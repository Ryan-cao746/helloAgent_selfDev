"""测试结构化 ReAct 决策循环的运行轨迹、协议校验和记忆写入。"""

import unittest
from unittest.mock import Mock

from pydantic import ValidationError

from project1.agents.types.multi_asking_agent.multi_turn_conversation import (
    MultiTurnConversation,
)
from project1.agents.types.react_agent_v2 import ReactAgentV2
from project1.context.base import ContextManagerBase
from project1.core.agent_protocol import (
    AgentRunResult,
    FinishDecision,
    ToolDecision,
    parse_agent_decision,
)
from project1.core.exceptions import LLMClientError
from project1.core.llm_client import HelloAgentsLLM
from project1.core.message import Message
from project1.core.run_lifecycle import RunController
from project1.core.trace_formatter import format_run_trace
from project1.memory.memory_manager import MemoryManager
from project1.memory.memory_types.simple_working_memory import SimpleWorkingMemory
from project1.tools.base import (
    Tool,
    ToolCall,
    ToolExecutionPolicy,
    ToolParameter,
    ToolPolicy,
)
from project1.tools.registry import ToolRegistry
from project1.user_input_interface.base import InputParams


class FakeContextManager(ContextManagerBase):
    def build(self, **kwargs) -> str:
        return f"question: {kwargs['input_text']}"


class FailingContextManager(ContextManagerBase):
    def build(self, **kwargs) -> str:
        raise RuntimeError("context unavailable")


class FakeDecisionLLM:
    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.message_batches = []

    def decide(self, messages, **kwargs):
        self.message_batches.append(list(messages))
        decision = self.decisions.pop(0)
        if isinstance(decision, Exception):
            raise decision
        return decision


class RetryingDecisionLLM(FakeDecisionLLM):
    def decide(self, messages, **kwargs):
        kwargs["on_retry"]("测试协议重试")
        return super().decide(messages, **kwargs)


class WeatherTool(Tool):
    def __init__(self, policy=None):
        super().__init__("weather", "查询城市天气", policy=policy)
        self.received = None
        self.call_count = 0

    def run(self, parameters):
        self.call_count += 1
        self.received = parameters
        return f"{parameters['city']}：晴朗"

    def get_parameters(self):
        return [
            ToolParameter(
                name="city",
                type="str",
                description="城市名称",
                required=True,
            )
        ]


def create_agent(
        decisions,
        max_steps=5,
        tool_policy=None,
        execution_policy=None,
        **agent_options,
):
    llm = FakeDecisionLLM(decisions)
    memory_manager = MemoryManager(
        enable_working_memory=True,
        working_memory=SimpleWorkingMemory(),
    )
    registry = ToolRegistry(execution_policy=execution_policy)
    weather = WeatherTool(policy=tool_policy)
    registry.register_tool(weather)
    agent = ReactAgentV2(
        llm_client=llm,
        tool_registry=registry,
        memory_manager=memory_manager,
        context_manager=FakeContextManager(memory_manager, registry),
        max_steps=max_steps,
        **agent_options,
    )
    return agent, llm, weather, memory_manager


class StructuredReactAgentTest(unittest.TestCase):
    def test_finishes_with_one_validated_decision(self):
        agent, _, _, memory_manager = create_agent([
            FinishDecision(
                kind="finish",
                reasoning_summary="可以直接回答",
                final_answer="你好",
            )
        ])

        answer = agent.run("打个招呼")

        self.assertEqual("你好", answer)
        self.assertEqual("finished", agent.last_run_result.status)
        self.assertEqual(1, agent.last_run_result.step_count)
        self.assertEqual(
            ["building_context", "deciding", "finished"],
            [item.to_state for item in agent.last_run_result.transitions],
        )
        self.assertGreaterEqual(agent.last_run_result.duration_ms, 0)
        self.assertGreaterEqual(agent.last_run_result.context_duration_ms, 0)
        self.assertLessEqual(
            agent.last_run_result.started_at,
            agent.last_run_result.finished_at,
        )
        self.assertGreaterEqual(
            agent.last_run_result.steps[0].llm_duration_ms,
            0,
        )
        memories = memory_manager.get_all_by_type("working")
        self.assertEqual(["user", "assistant"], [item.role for item in memories])
        self.assertEqual(["打个招呼", "你好"], [item.content for item in memories])

    def test_executes_tool_and_feeds_observation_back_to_model(self):
        agent, llm, weather, memory_manager = create_agent([
            ToolDecision(
                kind="tool",
                reasoning_summary="需要天气数据",
                tool_calls=[ToolCall(
                    tool_name="weather",
                    parameters={"city": "北京"},
                )],
            ),
            FinishDecision(
                kind="finish",
                reasoning_summary="已经取得天气数据",
                final_answer="北京今天晴朗",
            ),
        ])

        answer = agent.run("北京天气怎么样？")

        self.assertEqual("北京今天晴朗", answer)
        self.assertEqual({"city": "北京"}, weather.received)
        self.assertIn("北京：晴朗", llm.message_batches[1][-1].content)
        self.assertIn(
            "<UNTRUSTED_TOOL_OUTPUT>",
            llm.message_batches[1][-1].content,
        )
        self.assertEqual(2, len(agent.last_run_result.steps))
        tool_results = agent.last_run_result.steps[0].tool_results
        self.assertEqual("success", tool_results[0].status)
        self.assertIn("北京：晴朗", tool_results[0].output)
        self.assertGreaterEqual(tool_results[0].duration_ms, 0)
        memories = memory_manager.get_all_by_type("working")
        self.assertEqual(1, sum(item.role == "user" for item in memories))
        self.assertEqual(0, sum(item.role == "tool" for item in memories))

    def test_executes_multiple_tool_calls_in_order(self):
        agent, llm, weather, _ = create_agent([
            ToolDecision(
                kind="tool",
                reasoning_summary="需要两个城市的天气",
                tool_calls=[
                    ToolCall(
                        tool_name="weather",
                        parameters={"city": "北京"},
                    ),
                    ToolCall(
                        tool_name="weather",
                        parameters={"city": "上海"},
                    ),
                ],
            ),
            FinishDecision(
                kind="finish",
                reasoning_summary="已取得两地天气",
                final_answer="北京和上海都是晴天",
            ),
        ])

        answer = agent.run("北京和上海天气怎么样？")

        self.assertEqual("北京和上海都是晴天", answer)
        self.assertEqual(2, weather.call_count)
        feedback = llm.message_batches[1][-1].content
        self.assertIn("北京：晴朗", feedback)
        self.assertIn("上海：晴朗", feedback)
        self.assertEqual(2, len(agent.last_run_result.steps))
        self.assertEqual(
            ["success", "success"],
            [r.status for r in agent.last_run_result.steps[0].tool_results],
        )

    def test_returns_failed_result_after_maximum_steps(self):
        tool_decision = ToolDecision(
            kind="tool",
            reasoning_summary="继续查询",
            tool_calls=[ToolCall(
                tool_name="weather",
                parameters={"city": "北京"},
            )],
        )
        agent, _, _, memory_manager = create_agent(
            [tool_decision, tool_decision.model_copy(deep=True)],
            max_steps=2,
        )

        answer = agent.run("不断查询")

        self.assertIn("最大迭代次数", answer)
        self.assertEqual("failed", agent.last_run_result.status)
        self.assertEqual("maximum steps reached", agent.last_run_result.error)
        self.assertEqual(
            "maximum_steps_reached",
            agent.last_run_result.error_code,
        )
        self.assertEqual(2, len(agent.last_run_result.steps))
        self.assertEqual([], memory_manager.get_all_by_type("working"))

    def test_records_llm_failure_as_a_step(self):
        agent, _, _, _ = create_agent([
            LLMClientError("invalid decision api_key=private-value")
        ])

        result = agent.run_structured("触发模型失败")

        self.assertEqual("failed", result.status)
        self.assertEqual(1, result.step_count)
        self.assertEqual(1, len(result.steps))
        self.assertIsNone(result.steps[0].decision)
        self.assertIn("invalid decision", result.steps[0].error)
        self.assertNotIn("private-value", result.steps[0].error)
        self.assertNotIn("private-value", result.error)
        self.assertEqual("llm_failed", result.error_code)

    def test_cancelled_run_does_not_write_memory(self):
        agent, _, _, memory_manager = create_agent([
            FinishDecision(kind="finish", final_answer="不会执行")
        ])
        controller = RunController()
        controller.cancel()

        result = agent.run_structured("取消任务", controller=controller)

        self.assertEqual("cancelled", result.status)
        self.assertEqual("cancelled", result.error_code)
        self.assertEqual(
            ["building_context", "cancelled"],
            [item.to_state for item in result.transitions],
        )
        self.assertEqual([], memory_manager.get_all_by_type("working"))

    def test_run_times_out_at_checkpoint(self):
        now = [0.0]
        controller = RunController(
            timeout_seconds=1,
            clock=lambda: now[0],
        )
        now[0] = 1.0
        agent, _, _, _ = create_agent([])

        result = agent.run_structured("超时任务", controller=controller)

        self.assertEqual("timed_out", result.status)
        self.assertEqual("timed_out", result.error_code)
        self.assertEqual(1000, result.duration_ms)

    def test_confirmed_write_tool_executes_once(self):
        agent, _, weather, _ = create_agent([
            ToolDecision(
                kind="tool",
                tool_calls=[ToolCall(
                    tool_name="weather",
                    parameters={"city": "北京"},
                )],
            ),
            FinishDecision(kind="finish", final_answer="完成"),
        ],
            tool_policy=ToolPolicy(access="write"),
            execution_policy=ToolExecutionPolicy(
                allowed_access={"read_only", "write"}
            ),
            confirmation_handler=lambda tool_call, policy: True,
        )

        result = agent.run_structured("执行写工具")

        states = [item.to_state for item in result.transitions]
        self.assertEqual("finished", result.status)
        self.assertEqual(1, weather.call_count)
        self.assertIn("waiting_confirmation", states)
        self.assertEqual("success", result.steps[0].tool_results[0].status)

    def test_denied_confirmation_allows_fallback_answer(self):
        agent, _, weather, _ = create_agent([
            ToolDecision(
                kind="tool",
                tool_calls=[ToolCall(
                    tool_name="weather",
                    parameters={"city": "北京"},
                )],
            ),
            FinishDecision(kind="finish", final_answer="已取消写入"),
        ],
            tool_policy=ToolPolicy(access="write"),
            execution_policy=ToolExecutionPolicy(
                allowed_access={"read_only", "write"}
            ),
            confirmation_handler=lambda tool_call, policy: False,
        )

        result = agent.run_structured("拒绝写工具")

        self.assertEqual("finished", result.status)
        self.assertEqual(0, weather.call_count)
        self.assertEqual("denied", result.steps[0].tool_results[0].status)
        self.assertEqual(
            "confirmation_denied",
            result.steps[0].tool_results[0].error_code,
        )

    def test_records_protocol_retry_phase(self):
        agent, _, _, _ = create_agent([])
        agent.llm_client = RetryingDecisionLLM([
            FinishDecision(kind="finish", final_answer="完成")
        ])

        result = agent.run_structured("触发重试")

        states = [item.to_state for item in result.transitions]
        self.assertEqual("finished", result.status)
        self.assertIn("retrying", states)
        self.assertGreaterEqual(result.steps[0].llm_duration_ms, 0)

    def test_stops_repeated_identical_tool_calls(self):
        tool_decision = ToolDecision(
            kind="tool",
            reasoning_summary="继续查询",
            tool_calls=[ToolCall(
                tool_name="weather",
                parameters={"city": "北京"},
            )],
        )
        agent, _, _, _ = create_agent(
            [tool_decision, tool_decision.model_copy(deep=True)],
            max_repeated_tool_calls=1,
        )

        result = agent.run_structured("重复查询")

        self.assertEqual("failed", result.status)
        self.assertEqual("repeated tool call limit reached", result.error)
        self.assertEqual("denied", result.steps[-1].tool_results[0].status)
        self.assertEqual(
            "call_budget_exceeded",
            result.steps[-1].tool_results[0].error_code,
        )

    def test_limits_total_tool_output(self):
        agent, llm, _, _ = create_agent([
            ToolDecision(
                kind="tool",
                reasoning_summary="查询天气",
                tool_calls=[ToolCall(
                    tool_name="weather",
                    parameters={"city": "北京"},
                )],
            ),
            FinishDecision(
                kind="finish",
                reasoning_summary="完成",
                final_answer="完成",
            ),
        ], max_total_tool_output_chars=2)

        result = agent.run_structured("限制输出")

        tool_result = result.steps[0].tool_results[0]
        self.assertEqual(2, len(tool_result.output))
        self.assertTrue(tool_result.truncated)
        self.assertIn("[工具输出已截断]", llm.message_batches[1][-1].content)

    def test_records_context_build_failure(self):
        agent, _, _, memory_manager = create_agent([])
        agent.context_manager = FailingContextManager(
            memory_manager=memory_manager,
            tool_registry=agent.tool_registry,
        )

        result = agent.run_structured("触发上下文失败")

        self.assertEqual("failed", result.status)
        self.assertEqual(0, result.step_count)
        self.assertEqual([], result.steps)
        self.assertEqual("context unavailable", result.error)
        self.assertGreaterEqual(result.context_duration_ms, 0)

    def test_formats_a_safe_trace_summary(self):
        agent, _, _, _ = create_agent([
            FinishDecision(
                kind="finish",
                reasoning_summary="可以直接回答",
                final_answer="不应出现在轨迹中",
            )
        ])

        agent.run("不应出现在轨迹中的问题")
        trace = format_run_trace(agent.last_run_result)

        self.assertIn("状态: finished", trace)
        self.assertIn("决策: 返回最终答案", trace)
        self.assertIn(
            "状态流: building_context -> deciding -> finished",
            trace,
        )
        self.assertNotIn("不应出现在轨迹中", trace)


class RunControllerTest(unittest.TestCase):
    def test_terminal_state_cannot_transition(self):
        controller = RunController()
        controller.transition("building_context")
        controller.transition("cancelled")

        with self.assertRaises(RuntimeError):
            controller.transition("deciding")


class OneTurnInput:
    def get_input(self):
        return InputParams(input_text="测试", input_type="Talk")


class ResultAgent:
    def __init__(self, result):
        self.last_run_result = result

    def run(self, input_text):
        return self.last_run_result.output


class RecordingSummaryAgent:
    def __init__(self):
        self.call_count = 0

    def run(self, input_text):
        self.call_count += 1
        return "ok"


class MultiTurnLifecycleTest(unittest.TestCase):
    def create_conversation(self, status):
        memory_manager = MemoryManager(
            enable_working_memory=True,
            working_memory=SimpleWorkingMemory(),
        )
        agent_result = AgentRunResult(
            status=status,
            output="answer",
        )
        conversation_agent = ResultAgent(agent_result)
        summary_agent = RecordingSummaryAgent()
        conversation = MultiTurnConversation(
            user_input_interface=OneTurnInput(),
            memory_manager=memory_manager,
            conversation_agent=conversation_agent,
            summary_agent=summary_agent,
            max_ask=1,
        )
        return conversation, summary_agent

    def test_failed_run_is_not_summarized(self):
        conversation, summary_agent = self.create_conversation("failed")

        conversation.run()

        self.assertEqual(0, summary_agent.call_count)

    def test_finished_run_is_summarized(self):
        conversation, summary_agent = self.create_conversation("finished")

        conversation.run()

        self.assertEqual(1, summary_agent.call_count)


class StructuredDecisionParsingTest(unittest.TestCase):
    def test_rejects_unknown_decision_fields(self):
        with self.assertRaises(ValidationError):
            parse_agent_decision(
                '{"kind":"finish","final_answer":"完成","extra":true}'
            )

    def test_llm_repairs_one_invalid_decision(self):
        client = HelloAgentsLLM.__new__(HelloAgentsLLM)
        client.think = Mock(side_effect=[
            "这不是 JSON",
            '{"kind":"finish","reasoning_summary":"完成","final_answer":"成功"}',
        ])

        decision = client.decide([
            Message(content="请完成任务", role="user")
        ])

        self.assertIsInstance(decision, FinishDecision)
        self.assertEqual("成功", decision.final_answer)
        self.assertEqual(2, client.think.call_count)
        repaired_messages = client.think.call_args_list[1].args[0]
        self.assertEqual("assistant", repaired_messages[-2].role)
        self.assertIn("校验错误", repaired_messages[-1].content)


if __name__ == "__main__":
    unittest.main()
