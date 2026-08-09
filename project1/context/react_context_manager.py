from typing import List

from project1.context.base import ContextManagerBase
from project1.context.prompt_templates.react_prompt_template import REACT_PROMPT_TEMPLATE
from project1.memory.memory_item import MemoryItem
from project1.memory.memory_manager import MemoryManager
from project1.tools.registry import ToolRegistry

# 一个基本上下文构建方法，即模板+历史记录直接赛在一起
class ReActContextManager(ContextManagerBase):
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

        if self.tool_registry:
            tool_description = self.tool_registry.get_tools_description()  # 获取关于所有工具的详细描述
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

        return  self.prompt_template.format(tool_description=tool_description, history_str=memory_str, input_text=input_text)

