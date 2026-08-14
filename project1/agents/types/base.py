from abc import ABC, abstractmethod

from project1.context.base import ContextManagerBase
from project1.core.llm_client import HelloAgentsLLM
from typing import Optional
from project1.config.config import Config
from project1.memory.memory_manager import MemoryManager
from project1.tools.registry import ToolRegistry


class BaseComplexAgent(ABC):

    # 接口写在这里了，必须赋值
    memory_manager: MemoryManager
    context_manager: ContextManagerBase

    def __init__(
            self,
            name:str,
            llm_client: HelloAgentsLLM,
            tool_registry: Optional[ToolRegistry] = None,   # 默认空注册表
    ):
        self.name = name
        self.llm_client = llm_client
        self.tool_registry = tool_registry if tool_registry is not None else ToolRegistry()
    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        """运行Agent"""
        pass
