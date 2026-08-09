from project1.response_phrasing.base import BaseResponsePhraser, PhrasedResult
from project1.tools.registry import ToolRegistry


class ResponsePhraserV1(BaseResponsePhraser):

    def __init__(self, tool_registry:ToolRegistry):
        super().__init__(tool_registry)

    def phrase_response(self, text:str) -> PhrasedResult:

        result = PhrasedResult(
            thought="",
            content="",
            state="Finish",
        )
        thought, action = self.phrase_output(text)
        result.thought = thought

        if action and action.startswith("Finish"):
            content = self.phrase_action(action)[1]  # 元组取第二个，即方括号里的
            state = "Finish"
        elif action:
            tool_name, tool_input = self.phrase_action(action)
            if self.tool_registry is None:
                state = "Finish"    # 直接退出循环，相当于报错
                content = "似乎不存在工具注册表"
            else:
                content = self.tool_registry.execute_tool_call_from_text(tool_name, tool_input)
                state = "Action"
        else:
            state = "Pass"  # 没有工具调用指令，Pass，不退出循环
            content = "似乎不存在工具调用"

        result.state = state
        result.content = content
        result.thought = thought
        return result
