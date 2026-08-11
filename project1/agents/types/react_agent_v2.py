from typing import Literal

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
from project1.memory.memory_manager import MemoryManager
from project1.tools.registry import ToolRegistry


class ReactAgentV2(BaseComplexAgent):
    def __init__(
            self,
            llm_client:HelloAgentsLLM,
            tool_registry:ToolRegistry,
            memory_manager:MemoryManager,
            context_manager:ContextManagerBase,
            max_steps: int = 5,
            decision_retries: int = 1,
    ):
        if max_steps < 1:
            raise ValueError("max_steps 必须大于 0")
        if decision_retries < 0:
            raise ValueError("decision_retries 不能小于 0")

        super().__init__(
            name="simple_complex_agent",
            llm_client= llm_client,
            tool_registry=tool_registry,
        )
        #  需要外部注入，且在注入前启动两种记忆
        self.memory_manager=memory_manager
        self.context_manager = context_manager
        self.max_steps = max_steps
        self.decision_retries = decision_retries
        self.episodic_memory_name = memory_manager.episodic_memory_name
        self.working_memory_name = memory_manager.working_memory_name
        self.last_run_result: AgentRunResult | None = None

    def run(self, input_text: str, **kwargs) -> str:
        """Run the agent while preserving the original string-returning API.
            适配于原本字符串化的API
        """
        return self.run_structured(input_text=input_text, **kwargs).output

    def run_structured(self, input_text: str, **kwargs) -> AgentRunResult:
        """Run a validated model -> tool -> observation state loop."""
        prompt = self.context_manager.build(
            input_text=input_text,
            working_memory_name=self.working_memory_name,
            episodic_memory_name=self.episodic_memory_name,
            **kwargs,
        )
        messages = [Message(content=prompt, role="user")]
        steps: list[AgentStepRecord] = []   # 存储每一步骤模型响应的记录，以便于回退
        temperature = kwargs.get("temperature", 0)

        for step_number in range(1, self.max_steps + 1):
            try:
                decision = self.llm_client.decide(
                    messages,
                    temperature=temperature,
                    max_retries=self.decision_retries,
                )
            except LLMClientError as error:
                return self._finish_run(
                    input_text=input_text,
                    status="failed",
                    output="模型未能返回合法的执行决策。",
                    step_count=step_number,
                    steps=steps,
                    error=str(error),
                )

            # 条件分支状态机
            if isinstance(decision, FinishDecision):
                steps.append(AgentStepRecord(
                    step_number=step_number,
                    decision=decision,
                ))
                return self._finish_run(
                    input_text=input_text,
                    status="finished",
                    output=decision.final_answer,
                    step_count=step_number,
                    steps=steps,
                )

            if isinstance(decision, ToolDecision):
                if self.tool_registry is None:
                    return self._finish_run(
                        input_text=input_text,
                        status="failed",
                        output="似乎不存在工具注册表",
                        step_count=step_number,
                        steps=steps,
                        error="tool_registry is None",
                    )

                tool_result = self.tool_registry.execute_tool_call(decision.tool_call)
                steps.append(AgentStepRecord(
                    step_number=step_number,
                    decision=decision,
                    tool_result=tool_result,
                ))
                messages.extend([
                    Message(content=decision.model_dump_json(), role="assistant"),
                    Message(
                        content=(
                            f"工具 {decision.tool_call.tool_name} 的执行结果如下：\n"
                            f"{tool_result}\n"
                            "请根据结果返回下一项合法 JSON 决策。"
                        ),
                        role="user",
                    ),
                ])

        return self._finish_run(
            input_text=input_text,
            status="failed",
            output="已达到最大迭代次数，无法完成任务。",
            step_count=self.max_steps,
            steps=steps,
            error="maximum steps reached",
        )

    def _finish_run(
            self,
            input_text: str,
            status: Literal["finished", "failed"],
            output: str,
            step_count: int,
            steps: list[AgentStepRecord],
            error: str | None = None,
    ) -> AgentRunResult:
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
            status=status,
            output=output,
            step_count=step_count,
            steps=steps,
            error=error,
        )
        return self.last_run_result
