from typing import List

from project1.context.base import ContextManagerBase
from project1.context.prompt_template import REACT_PROMPT_TEMPLATE
from project1.memory.memory_item import MemoryItem
from project1.memory.memory_manager import MemoryManager
from project1.tools.registry import ToolRegistry

# 为装配了情景记忆系统的Agent设计的上下文构建器
class AdvancedContextManager(ContextManagerBase):
    def __init__(
            self,
            memory_manager: MemoryManager,
            tool_registry: ToolRegistry,
            prompt_template: str = REACT_PROMPT_TEMPLATE
    ):
        super().__init__(memory_manager, tool_registry, prompt_template)

    def build(self, input_text:str) -> str:

        if self.memory_manager:
            selected_memories:List[MemoryItem] = []
            selected_episodic_memory = self.memory_manager.search(type="simple_episodic", query=input_text) # 查询
            working_memory = self.memory_manager.get_all_by_type(type="simple_working")

            selected_memories.extend(selected_episodic_memory)
            selected_memories.extend(working_memory)
            selected_str_list = [memory.content for memory in selected_memories]
            memory_str = "\n".join(selected_str_list)
        else:
            memory_str = ""

        if self.tool_registry:
            tool_description = self.tool_registry.get_tools_description()  # 获取关于所有工具的详细描述
        else:
            tool_description = "None"

        return self.prompt_template.format(tool_description=tool_description, history_str=memory_str, input_text=input_text)