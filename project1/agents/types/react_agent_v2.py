"""实现带工具安全预算、生命周期控制和运行轨迹的 ReAct Agent。"""

import json
from time import perf_counter
from typing import Callable

from project1.agents.types.base import BaseComplexAgent
from project1.context.base import ContextManagerBase
from project1.core.agent_protocol import (
    AgentRunResult,
    AgentStepRecord,
    FinishDecision,
    ToolDecision,
)
from project1.core.exceptions import LLMClientError
from project1.core.llm_client import HelloAgentsLLM
from project1.core.message import Message
from project1.core.run_lifecycle import (
    RunCancelled,
    RunController,
    RunErrorCode,
    RunStatus,
    RunTimedOut,
)
from project1.memory.memory_manager import MemoryManager
from project1.tools.base import ToolCall, ToolPolicy, ToolResult
from project1.tools.registry import ToolRegistry
from project1.tools.security import redact_sensitive_text


class ReactAgentV2(BaseComplexAgent):
    """在受控状态循环中执行模型决策、工具调用和最终回答。"""

    def __init__(
            self,
            llm_client:HelloAgentsLLM,
            tool_registry:ToolRegistry,
            memory_manager:MemoryManager,
            context_manager:ContextManagerBase,
            max_steps: int = 5,
            decision_retries: int = 1,
            max_tool_calls: int = 3,
            max_repeated_tool_calls: int = 2,
            max_total_tool_output_chars: int = 40_000,
            run_timeout_seconds: float | None = 120,
            confirmation_handler: Callable[
                [ToolCall, ToolPolicy], bool
            ] | None = None,    # 接受一个ToolCall,一个ToolPolicy两个参数的函数
    ):
        if max_steps < 1:
            raise ValueError("max_steps 必须大于 0")
        if decision_retries < 0:
            raise ValueError("decision_retries 不能小于 0")
        if max_tool_calls < 1:
            raise ValueError("max_tool_calls 必须大于 0")
        if max_repeated_tool_calls < 1:
            raise ValueError("max_repeated_tool_calls 必须大于 0")
        if max_total_tool_output_chars < 1:
            raise ValueError("max_total_tool_output_chars 必须大于 0")
        if run_timeout_seconds is not None and run_timeout_seconds <= 0:
            raise ValueError("run_timeout_seconds 必须大于 0")

        super().__init__(
            name="simple_complex_agent",
            llm_client= llm_client,
            tool_registry=tool_registry,
        )
        self.memory_manager=memory_manager
        self.context_manager = context_manager
        self.max_steps = max_steps
        self.decision_retries = decision_retries
        self.max_tool_calls = max_tool_calls
        self.max_repeated_tool_calls = max_repeated_tool_calls
        self.max_total_tool_output_chars = max_total_tool_output_chars
        self.run_timeout_seconds = run_timeout_seconds
        self.confirmation_handler = confirmation_handler
        self.episodic_memory_name = memory_manager.episodic_memory_name
        self.working_memory_name = memory_manager.working_memory_name
        self.last_run_result: AgentRunResult | None = None
        self.active_run_controller: RunController | None = None

    def run(self, input_text: str, **kwargs) -> str:
        """运行 Agent，并保留原有的字符串返回接口。"""
        return self.run_structured(input_text=input_text, **kwargs).output

    def cancel_current_run(self) -> bool:
        """请求协作式取消；当前没有运行时返回 ``False``。"""
        if self.active_run_controller is None:
            return False
        self.active_run_controller.cancel()
        return True

    def run_structured(self, input_text: str, **kwargs) -> AgentRunResult:
        """执行受校验的决策循环，并返回包含状态和轨迹的结构化结果。"""
        controller = kwargs.pop("controller", None)
        if controller is None:
            timeout_seconds = kwargs.pop(
                "timeout_seconds",
                self.run_timeout_seconds,
            )
            controller = RunController(timeout_seconds=timeout_seconds)
        elif not isinstance(controller, RunController):
            raise TypeError("controller 必须是 RunController")
        elif controller.current_state is not None:
            raise ValueError("RunController 不能被重复使用")

        self.active_run_controller = controller
        steps: list[AgentStepRecord] = []
        try:
            return self._run_controlled(
                input_text=input_text,
                controller=controller,
                steps=steps,
                **kwargs,
            )
        except (RunCancelled, KeyboardInterrupt):
            controller.cancel()
            return self._complete_run(
                input_text=input_text,
                controller=controller,
                status="cancelled",
                output="任务已取消。",
                step_count=len(steps),
                steps=steps,
                error_code="cancelled",
                error="run cancelled",
            )
        except RunTimedOut:
            return self._complete_run(
                input_text=input_text,
                controller=controller,
                status="timed_out",
                output="任务执行超时。",
                step_count=len(steps),
                steps=steps,
                error_code="timed_out",
                error="run timed out",
            )
        finally:
            self.active_run_controller = None

    def _run_controlled(
            self,
            input_text: str,
            controller: RunController,
            steps: list[AgentStepRecord],
            **kwargs,
    ) -> AgentRunResult:
        """使用了controller状态机的运行接口"""
        controller.transition("building_context")
        controller.checkpoint()
        context_started = perf_counter()
        try:
            prompt = self.context_manager.build(
                input_text=input_text,
                working_memory_name=self.working_memory_name,
                episodic_memory_name=self.episodic_memory_name,
                **kwargs,
            )
        except Exception as error:
            controller.context_duration_ms = (
                perf_counter() - context_started
            ) * 1000
            safe_error = redact_sensitive_text(str(error))
            return self._complete_run(
                input_text=input_text,
                controller=controller,
                status="failed",
                output="上下文构建失败。",
                step_count=0,
                steps=steps,
                error_code="context_build_failed",
                error=safe_error,
            )

        controller.context_duration_ms = (
            perf_counter() - context_started
        ) * 1000
        controller.checkpoint()
        controller.transition("deciding")   # llm决策环节
        messages = [Message(content=prompt, role="user")]
        temperature = kwargs.get("temperature", 0)
        tool_call_count = 0
        repeated_tool_calls: dict[str, int] = {}
        total_tool_output_chars = 0

        for step_number in range(1, self.max_steps + 1):
            controller.checkpoint()
            llm_started = perf_counter()

            def on_decision_retry(reason: str) -> None:
                """将协议重试同步记录到当前运行的状态轨迹。"""
                controller.transition("retrying", reason=reason)
                controller.checkpoint()
                controller.transition("deciding", reason="retrying model decision")

            try:
                decision = self.llm_client.decide(
                    messages,
                    temperature=temperature,
                    max_retries=self.decision_retries,
                    on_retry=on_decision_retry,
                )
            except LLMClientError as error:
                llm_duration_ms = (perf_counter() - llm_started) * 1000
                safe_error = redact_sensitive_text(str(error))
                steps.append(AgentStepRecord(
                    step_number=step_number,
                    llm_duration_ms=llm_duration_ms,
                    error=safe_error,
                ))
                return self._complete_run(
                    input_text=input_text,
                    controller=controller,
                    status="failed",
                    output="模型未能返回合法的执行决策。",
                    step_count=step_number,
                    steps=steps,
                    error_code="llm_failed",
                    error=safe_error,
                )

            llm_duration_ms = (perf_counter() - llm_started) * 1000
            controller.checkpoint()

            if isinstance(decision, FinishDecision):
                steps.append(AgentStepRecord(
                    step_number=step_number,
                    decision=decision,
                    llm_duration_ms=llm_duration_ms,
                ))
                return self._complete_run(
                    input_text=input_text,
                    controller=controller,
                    status="finished",
                    output=decision.final_answer,
                    step_count=step_number,
                    steps=steps,
                )

            if isinstance(decision, ToolDecision):
                if self.tool_registry is None:
                    steps.append(AgentStepRecord(
                        step_number=step_number,
                        decision=decision,
                        llm_duration_ms=llm_duration_ms,
                        error="tool_registry is None",
                    ))
                    return self._complete_run(
                        input_text=input_text,
                        controller=controller,
                        status="failed",
                        output="未配置工具注册表，无法执行工具调用。",
                        step_count=step_number,
                        steps=steps,
                        error_code="tool_registry_missing",
                        error="tool_registry is None",
                    )

                if tool_call_count >= self.max_tool_calls:
                    tool_result = ToolResult(
                        tool_name=decision.tool_call.tool_name,
                        status="denied",
                        error_code="call_budget_exceeded",
                        error="已达到本轮工具调用次数上限",
                        duration_ms=0,
                    )
                    steps.append(AgentStepRecord(
                        step_number=step_number,
                        decision=decision,
                        llm_duration_ms=llm_duration_ms,
                        tool_result=tool_result,
                    ))
                    return self._complete_run(
                        input_text=input_text,
                        controller=controller,
                        status="failed",
                        output="工具调用次数已达到安全上限。",
                        step_count=step_number,
                        steps=steps,
                        error_code="tool_call_budget_exceeded",
                        error="maximum tool calls reached",
                    )

                call_key = json.dumps(
                    decision.tool_call.model_dump(),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                repeated_count = repeated_tool_calls.get(call_key, 0)
                if repeated_count >= self.max_repeated_tool_calls:
                    tool_result = ToolResult(
                        tool_name=decision.tool_call.tool_name,
                        status="denied",
                        error_code="call_budget_exceeded",
                        error="相同工具和参数的重复调用次数已达到上限",
                        duration_ms=0,
                    )
                    steps.append(AgentStepRecord(
                        step_number=step_number,
                        decision=decision,
                        llm_duration_ms=llm_duration_ms,
                        tool_result=tool_result,
                    ))
                    return self._complete_run(
                        input_text=input_text,
                        controller=controller,
                        status="failed",
                        output="检测到重复工具调用，已停止本轮任务。",
                        step_count=step_number,
                        steps=steps,
                        error_code="repeated_tool_call_limit",
                        error="repeated tool call limit reached",
                    )

                if total_tool_output_chars >= self.max_total_tool_output_chars:
                    tool_result = ToolResult(
                        tool_name=decision.tool_call.tool_name,
                        status="denied",
                        error_code="output_budget_exceeded",
                        error="本轮工具输出总量已达到上限",
                        duration_ms=0,
                    )
                    steps.append(AgentStepRecord(
                        step_number=step_number,
                        decision=decision,
                        llm_duration_ms=llm_duration_ms,
                        tool_result=tool_result,
                    ))
                    return self._complete_run(
                        input_text=input_text,
                        controller=controller,
                        status="failed",
                        output="工具输出总量已达到安全上限。",
                        step_count=step_number,
                        steps=steps,
                        error_code="tool_output_budget_exceeded",
                        error="tool output budget reached",
                    )

                # 上述情况检查全部通过，进入工具调用环节
                tool_call_count += 1
                repeated_tool_calls[call_key] = repeated_count + 1

                controller.transition(
                    "executing_tool",
                    reason=decision.tool_call.tool_name,
                )
                controller.checkpoint()
                tool_result = self.tool_registry.execute_tool_call_structured(
                    decision.tool_call
                )
                controller.checkpoint()

                if tool_result.status == "confirmation_required":   # 如果需要用户确认
                    controller.transition(
                        "waiting_confirmation",
                        reason=decision.tool_call.tool_name,
                    )
                    tool = self.tool_registry.get_tool(
                        decision.tool_call.tool_name
                    )
                    if self.confirmation_handler is not None and tool is not None:
                        try:
                            confirmed = self.confirmation_handler(
                                decision.tool_call,
                                tool.policy,
                            )
                        except Exception as error:
                            confirmed = False
                            confirmation_error = (
                                "用户确认失败: "
                                f"{redact_sensitive_text(str(error))}"
                            )
                        else:
                            confirmation_error = "用户拒绝执行该工具"

                        controller.checkpoint()
                        if confirmed:
                            controller.transition(
                                "executing_tool",
                                reason="tool call confirmed",
                            )
                            tool_result = (
                                self.tool_registry.execute_tool_call_structured(
                                    decision.tool_call,
                                    confirmed=True,
                                )
                            )
                            controller.checkpoint()
                        else:
                            tool_result = ToolResult(
                                tool_name=decision.tool_call.tool_name,
                                status="denied",
                                error_code="confirmation_denied",
                                error=confirmation_error,
                                duration_ms=tool_result.duration_ms,
                            )

                if tool_result.status == "success" and tool_result.output is not None:
                    remaining_output_chars = (
                        self.max_total_tool_output_chars - total_tool_output_chars
                    )
                    if len(tool_result.output) > remaining_output_chars:
                        tool_result = tool_result.model_copy(update={
                            "output": tool_result.output[:remaining_output_chars],
                            "truncated": True,
                            "original_length": (
                                tool_result.original_length
                                if tool_result.original_length is not None
                                else len(tool_result.output)
                            ),
                        })
                    total_tool_output_chars += len(tool_result.output)

                controller.transition(
                    "deciding",
                    reason=f"tool result: {tool_result.status}",
                )
                steps.append(AgentStepRecord(
                    step_number=step_number,
                    decision=decision,
                    llm_duration_ms=llm_duration_ms,
                    tool_result=tool_result,
                ))
                messages.extend([
                    Message(content=decision.model_dump_json(), role="assistant"),
                    Message(
                        content=(
                            f"{tool_result.to_observation()}\n"
                            "请根据结果返回下一项合法 JSON 决策。"
                        ),
                        role="user",
                    ),
                ])

        return self._complete_run(
            input_text=input_text,
            controller=controller,
            status="failed",
            output="已达到最大迭代次数，无法完成任务。",
            step_count=self.max_steps,
            steps=steps,
            error_code="maximum_steps_reached",
            error="maximum steps reached",
        )

    def _complete_run(
            self,
            input_text: str,
            controller: RunController,
            status: RunStatus,
            output: str,
            step_count: int,
            steps: list[AgentStepRecord],
            error_code: RunErrorCode | None = None,
            error: str | None = None,
    ) -> AgentRunResult:
        controller.transition(status, reason=error_code or status)
        return self._finish_run(
            input_text=input_text,
            controller=controller,
            status=status,
            output=output,
            step_count=step_count,
            steps=steps,
            error_code=error_code,
            error=error,
        )

    def _finish_run(
            self,
            input_text: str,
            controller: RunController,
            status: RunStatus,
            output: str,
            step_count: int,
            steps: list[AgentStepRecord],
            error_code: RunErrorCode | None = None,
            error: str | None = None,
    ) -> AgentRunResult:
        if status == "finished":
            self.memory_manager.add(
                type=self.working_memory_name,
                content=input_text,
                role="user",
            )
            self.memory_manager.add(
                type=self.working_memory_name,
                content=output,
                role="assistant",
            )

        self.last_run_result = AgentRunResult(
            run_id=controller.run_id,
            status=status,
            output=output,
            step_count=step_count,
            steps=steps,
            error=redact_sensitive_text(error) if error else None,
            error_code=error_code,
            started_at=controller.started_at,
            duration_ms=controller.elapsed_ms(),
            context_duration_ms=controller.context_duration_ms,
            transitions=list(controller.transitions),
        )
        return self.last_run_result
