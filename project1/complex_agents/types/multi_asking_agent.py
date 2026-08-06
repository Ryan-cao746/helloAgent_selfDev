# 旨在实现一个具备多轮对话能力的Agent
# 打算启用情景记忆和simple_memory(简易工作记忆)
from project1.complex_agents.types.base import BaseComplexAgent
from project1.config.config import Config
from project1.context.advanced_context_manager import AdvancedContextManager
from project1.context.base import ContextManagerBase
from project1.core.llm_client import HelloAgentsLLM
from project1.memory.memory_manager import MemoryManager
from project1.memory.memory_types.simple_episodic_memory import SimpleEpisodicMemory
from project1.memory.memory_types.simple_working_memory import SimpleWorkingMemory
from project1.tools.registry import ToolRegistry


class MultiAskingAgent(BaseComplexAgent):
    def __init__(
            self,
            name: str,
            llm_client: HelloAgentsLLM,
            max_ask:int = 5,
            tool_registry: ToolRegistry = None,
            system_prompt: str = None,
            config: Config = None,

    ):
        super().__init__(
            name=name,
            llm_client=llm_client,
            tool_registry=tool_registry,
            system_prompt=system_prompt,
            config=config
        )
        # 初始化记忆系统，启动简单工作记忆和简单情景记忆
        self.memory_manager=MemoryManager()
        self.memory_manager.add_new_memory_type(type="simple_working", base_memory=SimpleWorkingMemory())
        self.memory_manager.add_new_memory_type(type="simple_episodic", base_memory=SimpleEpisodicMemory())

        self.context_manager=AdvancedContextManager(self.memory_manager, self.tool_registry)
        self.max_ask=max_ask

    def run(self, input_text: str, **kwargs) -> str:
        """这个场景下run方法是单论对话内的情况。区别或许仅仅在于更复杂的记忆系统"""
        current_ask = 0;
        while current_ask < self.max_ask:
            current_ask += 1
            self.memory_manager.clear(type="simple_working")    # 每一轮对话清除工作记忆
