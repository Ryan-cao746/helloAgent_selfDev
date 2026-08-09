from project1.agents.types.base import BaseComplexAgent
from project1.context.base import ContextManagerBase
from project1.core.llm_client import HelloAgentsLLM
from project1.memory.memory_manager import MemoryManager
from project1.supportive_functions.output_phrasing import phrase_output, phrase_action
from project1.tools.registry import ToolRegistry
from project1.core.message import Message

class ReactAgentV2(BaseComplexAgent):
    def __init__(
            self,
            llm_client:HelloAgentsLLM,
            tool_registry:ToolRegistry,
            memory_manager:MemoryManager,
            context_manager:ContextManagerBase,
            max_steps: int = 5,
    ):
        super().__init__(
            name="simple_complex_agent",
            llm_client= llm_client,
            tool_registry=tool_registry,
        )
        #  需要外部注入，且在注入前启动两种记忆
        self.memory_manager=memory_manager
        self.context_manager = context_manager
        self.max_steps = max_steps
        self.episodic_memory_name = memory_manager.episodic_memory_name
        self.working_memory_name = memory_manager.working_memory_name

    def run(self, input_text: str, **kwargs) -> str:
        current_step = 0
        while current_step < self.max_steps:
            current_step += 1
            print(f"-----第{current_step}步-----")

            # 提示词构建
            prompt = self.context_manager.build(
                input_text=input_text,
                working_memory_name=self.working_memory_name,
                episodic_memory_name=self.episodic_memory_name,
                **kwargs,
            )

            # 调用llm
            response = self.llm_client.think([Message(content=prompt, role="user")], **kwargs)

            thought, action = phrase_output(response)
            if action and action.startswith("Finish"):
                final_answer = phrase_action(action)[1] # 元组取第二个，即方括号里的
                self.memory_manager.add(type=self.working_memory_name, content=input_text, role="user")
                self.memory_manager.add(type=self.working_memory_name, content=final_answer, role="assistant")
                return final_answer

            if action:
                tool_name, tool_input = phrase_action(action)
                if self.tool_registry is None:
                    return "似乎不存在工具注册表"
                result = self.tool_registry.execute_tool_call_from_text(tool_name, tool_input)
                self.memory_manager.add(type=self.working_memory_name, content=input_text, role="user")
                self.memory_manager.add(type=self.working_memory_name, content=result, role="tool")
            else:
                print("似乎不存在工具调用")

        # 达到最大步数
        final_answer = "已达到最大迭代次数，无法完成任务。"
        self.memory_manager.add(type=self.working_memory_name, content=input_text, role="user")
        self.memory_manager.add(type=self.working_memory_name, content=final_answer, role="assistant")
        return final_answer
