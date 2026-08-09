# 旨在实现一个具备多轮对话能力的Agent
# 打算启用情景记忆和simple_memory(简易工作记忆)
from project1.agents.types.base import BaseComplexAgent
from project1.memory.memory_manager import MemoryManager
from project1.user_input_interface.base import UserInputInterface


class MultiTurnConversation:
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


    def run(self, **kwargs) -> str:     # 这个run直接从用户获取输入
        """这个场景下run方法是单论对话内的情况。区别或许仅仅在于更复杂的记忆系统"""
        current_ask = 0
        while current_ask < self.max_ask:
            current_ask += 1

            self.memory_manager.clear(type=self.working_memory_name)    # 每一轮对话清除工作记忆

            user_input = self.user_input_interface.get_input() # 获取用户输入

            if user_input.input_type == "Stop":
                print("用户要求停止")
                return "用户停止"
            if user_input.input_type == "Error":
                print("用户输入类型错误，跳过该轮对话")
                continue

            input_text = user_input.input_text

            answer = self.conversation_agent.run(input_text=input_text)

            print(f"answer: {answer}")

            self.summary_agent.run(input_text="default")    # 整理记忆系统

            if self.debug_mode:
                print("====== 调试信息 ======")
                self.memory_manager.print_all_memory_by_type(self.working_memory_name)
                self.memory_manager.print_all_memory_by_type(self.episodic_memory_name)

        print("已经执行完全部限制内对话数目")
        return "已经执行完全部限制内对话数目"
