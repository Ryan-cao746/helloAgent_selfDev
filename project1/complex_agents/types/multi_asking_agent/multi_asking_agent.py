# 旨在实现一个具备多轮对话能力的Agent
# 打算启用情景记忆和simple_memory(简易工作记忆)
from project1.complex_agents.types.base import BaseComplexAgent
from project1.complex_agents.types.multi_asking_agent.summary_agent import SummaryAgent
from project1.complex_agents.types.react_agent_v2 import ReactAgentV2
from project1.config.config import Config
from project1.context.advanced_context_manager import AdvancedContextManager
from project1.context.base import ContextManagerBase
from project1.core.llm_client import HelloAgentsLLM
from project1.memory.memory_manager import MemoryManager
from project1.memory.memory_types.simple_episodic_memory import SimpleEpisodicMemory
from project1.memory.memory_types.simple_working_memory import SimpleWorkingMemory
from project1.tools.registry import ToolRegistry
from project1.user_input_interface.base import UserInputInterface


class MultiAskingAgent(BaseComplexAgent):
    def __init__(
            self,
            name: str,
            llm_client: HelloAgentsLLM,
            user_input_interface: UserInputInterface,
            max_ask:int = 5,
            max_step:int = 5,
            tool_registry: ToolRegistry = None,
            system_prompt: str = None,
            config: Config = None,
            debug_mode: bool = False,
    ):
        super().__init__(
            name=name,
            llm_client=llm_client,
            tool_registry=tool_registry,
            system_prompt=system_prompt,
            config=config
        )
        self.user_input_interface=user_input_interface
        self.debug_mode=debug_mode

        # 初始化记忆系统，启动简单工作记忆和简单情景记忆
        self.memory_manager=MemoryManager(
            enable_working_memory=True,
            enable_episodic_memory=True,
            working_memory=SimpleWorkingMemory(),
            episodic_memory=SimpleEpisodicMemory(),
        )

        self.context_manager=AdvancedContextManager(self.memory_manager, self.tool_registry)
        self.max_ask=max_ask
        self.max_step=max_step

        # 配置子Agent
        self.built_in_react_agent = ReactAgentV2(
            llm_client=self.llm_client,
            tool_registry=self.tool_registry,
            memory_manager=self.memory_manager,
            context_manager=self.context_manager,
            max_steps=self.max_step,
        )   # 内置的ReAct，直接复用现成的。传入记忆依赖，操作整个Agent的记忆系统
        self.summary_agent = SummaryAgent(
            llm_client=self.llm_client,
            memory_manager=self.memory_manager,
            debug_mode=self.debug_mode,
        )   # 用于总结的Agent，注入记忆系统依赖从而整理全局

    def run(self, **kwargs) -> str:     # 这个run直接从用户获取输入
        """这个场景下run方法是单论对话内的情况。区别或许仅仅在于更复杂的记忆系统"""
        current_ask = 0
        while current_ask < self.max_ask:
            current_ask += 1

            self.memory_manager.clear(type="working")    # 每一轮对话清除工作记忆

            user_input = self.user_input_interface.get_input() # 获取用户输入

            if user_input.input_type == "Stop":
                print("用户要求停止")
                return "用户停止"
            if user_input.input_type == "Error":
                print("用户输入类型错误，跳过该轮对话")
                continue

            input_text = user_input.input_text

            answer = self.built_in_react_agent.run(input_text=input_text)

            print(f"answer: {answer}")

            self.summary_agent.run(input_text="default")    # 整理记忆系统

            if self.debug_mode:
                print("====== 调试信息 ======")
                self.memory_manager.print_all_memory_by_type("working")
                self.memory_manager.print_all_memory_by_type("episodic")

        print("已经执行完全部限制内对话数目")
        return "已经执行完全部限制内对话数目"



            