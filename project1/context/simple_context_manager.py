
from project1.context.base import ContextManagerBase
from project1.context.prompt_template import REACT_PROMPT_TEMPLATE
from project1.memory.memory_manager import MemoryManager
from project1.tools.registry import ToolRegistry

# 一个基本上下文构建方法，即模板+历史记录直接赛在一起
class SimpleContextManager(ContextManagerBase):
    def __init__(
            self,
            memory_manager:MemoryManager = None,
            tool_registry: ToolRegistry = None,
            prompt_template: str = REACT_PROMPT_TEMPLATE
            ):
        super().__init__(memory_manager, tool_registry, prompt_template)

    def build(self, input_text:str) -> str:

        if self.tool_registry:
            tool_description = self.tool_registry.get_tools_description()  # 获取关于所有工具的详细描述
        else:
            tool_description = "None"

        if self.memory_manager:
            memory_str_list = []
            for memory in self.memory_manager.memory_types.values(): # 将每个托管的记忆库全部加入提示词
                for record in memory.memories:
                    memory_str_list.append(record.content)
            memory_str = "\n".join(memory_str_list)
        else:
            memory_str = "None"

        return  self.prompt_template.format(tool_description=tool_description, history_str=memory_str, input_text=input_text)

