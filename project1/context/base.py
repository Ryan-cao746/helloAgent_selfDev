"""定义从记忆、工具和提示词模板构建模型上下文的抽象接口。"""

from abc import ABC, abstractmethod

from project1.memory.memory_manager import MemoryManager
from project1.skill_system.runtime import SkillRuntime
from project1.tools.registry import ToolRegistry


class ContextManagerBase(ABC):
    """上下文构建器基类，依赖项由具体 Agent 在装配时注入。"""

    def __init__(
            self,
            memory_manager:MemoryManager= None,
            tool_registry:ToolRegistry = None,
            prompt_template: str = "",
            skill_runtime: SkillRuntime | None = None,  # 加了skills运行时
    ):
        self.memory_manager = memory_manager
        self.tool_registry = tool_registry
        self.prompt_template = prompt_template
        self.skill_runtime = skill_runtime

    @abstractmethod
    def build(self, **kwargs) -> str:
        """根据当前依赖和调用参数构建一段模型输入文本。"""
        pass
