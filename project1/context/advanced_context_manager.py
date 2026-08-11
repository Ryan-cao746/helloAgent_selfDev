from typing import List

from project1.context.base import ContextManagerBase
from project1.context.prompt_templates.react_prompt_template import REACT_PROMPT_TEMPLATE
from project1.memory.memory_item import MemoryItem
from project1.memory.memory_manager import MemoryManager
from project1.tools.registry import ToolRegistry

# 为装配了情景记忆系统的Agent设计的上下文构建器
class AdvancedContextManager(ContextManagerBase):
    def __init__(
            self,
            memory_manager: MemoryManager,
            tool_registry: ToolRegistry = None,
            prompt_template: str = REACT_PROMPT_TEMPLATE
    ):
        super().__init__(memory_manager, tool_registry, prompt_template)

    def build(
            self,
            input_text:str,
            **kwargs,
    ) -> str:

        if self.memory_manager:
            selected_memories:List[MemoryItem] = []
            selected_semantic_memories:List[MemoryItem] = []

            working_memory_name = self.memory_manager.working_memory_name
            episodic_memory_name = self.memory_manager.episodic_memory_name
            semantic_memory_name = self.memory_manager.semantic_memory_name

            if self.memory_manager.has_memory_type(episodic_memory_name):
                selected_memories.extend(
                    self.memory_manager.search(type=episodic_memory_name, query=input_text)
                )
            if self.memory_manager.has_memory_type(working_memory_name):
                selected_memories.extend(
                    self.memory_manager.get_all_by_type(type=working_memory_name)
                )
            if self.memory_manager.has_memory_type(semantic_memory_name):
                selected_semantic_memories.extend(
                    self.memory_manager.search(type=semantic_memory_name, query=input_text)
                )

            selected_str_list = [memory.content for memory in selected_memories]
            selected_semantic_str_list = [memory.content for memory in selected_semantic_memories]

            memory_str = "\n".join(selected_str_list)
            semantic_str = "\n".join(selected_semantic_str_list)
        else:
            memory_str = ""
            semantic_str = ""

        if self.tool_registry:
            tool_description = self.tool_registry.get_tools_description()  # 获取关于所有工具的详细描述
        else:
            tool_description = "None"

        return self.prompt_template.format(tool_description=tool_description, history_str=memory_str, input_text=input_text, semantic_str=semantic_str)
