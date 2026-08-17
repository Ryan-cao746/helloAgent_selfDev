"""协调用户输入、单轮 Agent、记忆整理和内存式运行轨迹。"""

from collections import deque

from project1.agents.types.base import BaseComplexAgent
from project1.core.agent_protocol import AgentRunResult
from project1.core.trace_formatter import format_run_trace
from project1.memory.memory_manager import MemoryManager
from project1.user_input_interface.base import UserInputInterface


class MultiTurnConversation:
    """在限定轮数内执行交互会话，并仅为成功运行整理长期记忆。"""

    def __init__(
            self,
            user_input_interface: UserInputInterface,
            memory_manager: MemoryManager,
            conversation_agent: BaseComplexAgent,
            summary_agent: BaseComplexAgent,
            max_ask:int = 5,
            debug_mode: bool = False,
    ):
        self.user_input_interface=user_input_interface
        self.debug_mode=debug_mode
        self.memory_manager=memory_manager
        self.conversation_agent=conversation_agent
        self.summary_agent=summary_agent
        self.working_memory_name = self.memory_manager.working_memory_name
        self.episodic_memory_name = self.memory_manager.episodic_memory_name
        self.max_ask=max_ask
        self.trace_history: deque[AgentRunResult] = deque(maxlen=20)


    def run(self, **kwargs) -> str:
        """持续读取用户输入，直到主动停止或达到最大对话轮数。"""
        current_ask = 0
        while current_ask < self.max_ask:
            current_ask += 1

            # 工作记忆只保留当前会话轮次，长期信息由摘要 Agent 写入情景记忆。
            self.memory_manager.clear(type=self.working_memory_name)

            user_input = self.user_input_interface.get_input()

            if user_input.input_type == "Stop":
                print("用户要求停止")
                return "用户停止"
            if user_input.input_type == "Error":
                print("用户输入类型错误，跳过该轮对话")
                continue

            input_text = user_input.input_text

            try:
                answer = self.conversation_agent.run(input_text=input_text)
            except Exception as e:
                # 单轮失败降级处理，后续轮次仍可继续。
                print(f"本轮对话Agent执行失败: {e}")
                continue

            print(f"answer: {answer}")

            run_result = getattr(self.conversation_agent, "last_run_result", None)
            if isinstance(run_result, AgentRunResult):
                self.trace_history.append(run_result)

            if (
                    isinstance(run_result, AgentRunResult)
                    and run_result.status == "finished"
            ):
                try:
                    self.summary_agent.run(input_text="default")
                except Exception as e:
                    # 记忆整理失败不影响已经生成的用户回答。
                    print(f"本轮记忆整理失败: {e}")

            if self.debug_mode:
                print("====== 调试信息 ======")
                if isinstance(run_result, AgentRunResult):
                    print(format_run_trace(run_result))
                self.memory_manager.print_all_memory_by_type(self.working_memory_name)
                self.memory_manager.print_all_memory_by_type(self.episodic_memory_name)

        print("已经执行完全部限制内对话数目")
        return "已经执行完全部限制内对话数目"
