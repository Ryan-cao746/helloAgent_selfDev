"""构建由工具说明、近期记忆和用户输入组成的基础 ReAct 上下文。"""

from typing import List

from project1.context.base import ContextManagerBase
from project1.context.prompt_templates.react_prompt_template import REACT_PROMPT_TEMPLATE
from project1.memory.memory_item import MemoryItem
from project1.memory.memory_manager import MemoryManager
from project1.tools.registry import ToolRegistry

class ReActContextManager(ContextManagerBase):
    """将工作记忆和检索到的情景记忆填入 ReAct 提示词模板。"""
    def __init__(
            self,
            memory_manager:MemoryManager = None,
            tool_registry: ToolRegistry = None,
            prompt_template: str = REACT_PROMPT_TEMPLATE
            ):
        super().__init__(memory_manager, tool_registry, prompt_template)

    def build(
            self,
            input_text:str,
            working_memory_name:str = None,
            episodic_memory_name:str = None,
            **kwargs,
    ) -> str:
        """根据用户输入选择历史记录并返回格式化提示词。"""

        if self.tool_registry:
            tool_description = self.tool_registry.get_tools_description()
        else:
            tool_description = "None"

        if self.memory_manager:
            memory_list:List[MemoryItem] = []
            working_memory_name = working_memory_name or self.memory_manager.working_memory_name
            episodic_memory_name = episodic_memory_name or self.memory_manager.episodic_memory_name

            if self.memory_manager.has_memory_type(working_memory_name):
                memory_list.extend(self.memory_manager.get_all_by_type(working_memory_name))
            if self.memory_manager.has_memory_type(episodic_memory_name):
                memory_list.extend(self.memory_manager.search(type=episodic_memory_name, query=input_text))

            memory_str_list = [memory.content for memory in memory_list]

            memory_str = "\n".join(memory_str_list)
        else:
            memory_str = "None"

        return self.prompt_template.format(
            tool_description=tool_description,
            history_str=memory_str,
            input_text=input_text,
            semantic_str="",
        )
