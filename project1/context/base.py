# 配置了上下文管理接口。实现这个接口的类具有构造上下文的方法。由于以后会经常修改这个模块，于是做了解耦
# 理论上上下文构造需要从Agent的各个其他模块收集相关信息，所以需要具备其他很多示例，这些以后在各个实现的__init__中写
from abc import ABC, abstractmethod

from project1.memory.memory_manager import MemoryManager
from project1.tools.registry import ToolRegistry


class ContextManagerBase(ABC):

    def __init__(
            self,
            memory_manager:MemoryManager= None,
            tool_registry:ToolRegistry = None,
            prompt_template: str = "",
    ):
        self.memory_manager = memory_manager  # 注入记忆管理的数据依赖。理论上这是引用，所以每个记忆管理类型的数据是变化的
        self.tool_registry = tool_registry # 注入工具注册表的依赖。因为上下文构建需要知道所有工具
        self.prompt_template = prompt_template  # 注入提示词模板

    @abstractmethod
    def build(self, **kwargs) -> str:
        """构建上下文，返回最朴素的字符串"""
        pass