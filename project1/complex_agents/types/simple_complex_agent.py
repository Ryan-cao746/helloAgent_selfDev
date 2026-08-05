from project1.complex_agents.types.base import BaseComplexAgent
from project1.context.simple_context_manager import SimpleContextManager
from project1.core.llm_client import HelloAgentsLLM
from project1.memory.memory_manager import MemoryManager
from project1.supportive_functions.output_phrasing import phrase_output, phrase_action
from project1.tools.registry import ToolRegistry
from project1.core.message import Message

class SimpleComplexAgent(BaseComplexAgent):
    def __init__(
            self,
            llm_client:HelloAgentsLLM,
            tool_registry:ToolRegistry,
            max_steps: int = 5,
    ):
        super().__init__(
            name="simple_complex_agent",
            llm_client= llm_client,
            tool_registry=tool_registry,
        )
        # 值得注意的是，memory_manager和context_manager的生命周期在agent内部，所以说不用外部输入
        self.memory_manager=MemoryManager(enable_simple=True, enable_working=False) # 启动简单记忆，关闭工作记忆
        self.context_manager = SimpleContextManager(tool_registry=tool_registry, memory_manager=self.memory_manager) # 提示词模板用默认的
        self.max_steps = max_steps

    def run(self, input_text: str, **kwargs) -> str:
        current_step = 0
        while current_step < self.max_steps:
            current_step += 1
            print(f"-----第{current_step}步-----")

            # 提示词构建
            prompt = self.context_manager.build(input_text)

            # 调用llm
            response = self.llm_client.think([Message(content=prompt, role="user")], **kwargs)

            thought, action = phrase_output(response)
            if action and action.startswith("Finish"):
                final_answer = phrase_action(action)[1] # 元组取第二个，即方括号里的
                self.memory_manager.add(type="simple", content=input_text)
                self.memory_manager.add(type="simple", content=final_answer)
                return final_answer

            if action:
                tool_name, tool_input = phrase_action(action)
                if self.tool_registry is None:
                    return "似乎不存在工具注册表"
                result = self.tool_registry.execute_tool_call(tool_name, tool_input)
                self.memory_manager.add(type="simple", content=input_text)
                self.memory_manager.add(type="simple", content=result)
            else:
                print("似乎不存在工具调用")

        # 达到最大步数
        final_answer = "已达到最大迭代次数，无法完成任务。"
        self.memory_manager.add(type="simple", content=input_text)
        self.memory_manager.add(type="simple", content=final_answer)
        return final_answer