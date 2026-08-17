"""定义需要模型客户端、工具和上下文依赖的复合 Agent 抽象接口。"""

from abc import ABC, abstractmethod

from project1.context.base import ContextManagerBase
from project1.core.llm_client import HelloAgentsLLM
from typing import Optional
from project1.config.config import Config
from project1.memory.memory_manager import MemoryManager
from project1.tools.registry import ToolRegistry


class BaseComplexAgent(ABC):
    """复合 Agent 基类，统一保存名称、模型客户端和工具注册表。"""

    # 具体 Agent 在初始化时必须提供这两个运行依赖。
    memory_manager: MemoryManager
    context_manager: ContextManagerBase

    def __init__(
            self,
            name:str,
            llm_client: HelloAgentsLLM,
            tool_registry: Optional[ToolRegistry] = None,
    ):
        self.name = name
        self.llm_client = llm_client
        self.tool_registry = tool_registry if tool_registry is not None else ToolRegistry()
    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        """处理一次用户输入并返回面向调用方的文本结果。"""
        pass
