"""构建同时包含工作、情景和语义记忆的 Agent 上下文。"""

from typing import List

from project1.context.base import ContextManagerBase
from project1.context.prompt_templates.react_prompt_template import REACT_PROMPT_TEMPLATE
from project1.memory.memory_item import MemoryItem
from project1.memory.memory_manager import MemoryManager
from project1.skill_system.runtime import SkillRuntime
from project1.tools.registry import ToolRegistry

class AdvancedContextManager(ContextManagerBase):
    """为启用三类记忆的 Agent 选择相关内容并填充提示词模板。"""
    def __init__(
            self,
            memory_manager: MemoryManager,
            tool_registry: ToolRegistry = None,
            prompt_template: str = REACT_PROMPT_TEMPLATE,
            skill_runtime: SkillRuntime | None = None,  # 增加了注入skills运行时的依赖，使提示词具备列出skills列表的能力
    ):
        super().__init__(memory_manager, tool_registry, prompt_template, skill_runtime)

    def build(
            self,
            input_text:str,
            **kwargs,
    ) -> str:
        """检索与输入相关的记忆，并生成本轮完整模型上下文。"""

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
            tool_description = self.tool_registry.get_tools_description()
        else:
            tool_description = "None"

        if self.skill_runtime:  # 向提示词内添加skills的简要描述内容
            skills_description = self.skill_runtime.describe_available_skills(input_text)
        else:
            skills_description = "No skills runtime configured."

        return self.prompt_template.format(
            tool_description=tool_description,
            skills_description=skills_description,
            history_str=memory_str,
            input_text=input_text,
            semantic_str=semantic_str,
        )
