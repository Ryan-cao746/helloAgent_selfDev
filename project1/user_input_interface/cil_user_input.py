"""实现命令行用户输入和高风险工具确认。"""

from project1.user_input_interface.base import UserInputInterface, InputParams
from project1.tools.base import ToolCall, ToolPolicy


class CilUserInput(UserInputInterface):
    """通过标准输入输出驱动多轮对话。"""

    def get_input(self) -> InputParams:
        """读取消息类型，并在对话类型下继续读取提示文本。"""

        prompt1 = """
        ---- 请输入消息类型 ----
        数字1：Talk
        数字2：Stop
        """
        print(prompt1)

        message_type = input("消息类型：")

        if message_type == "2":
            return InputParams(
                input_text="N/A",
                input_type="Stop"
            )
        elif message_type == "1":
            print("---- 请输入用户提示词 ----")
            res = input("你的提示词：")
            return InputParams(
                input_text=res,
                input_type="Talk"
            )
        else:
            print("错误输入")
            return InputParams(
                input_text="N/A",
                input_type="Error"
            )

    def confirm_tool_call(
            self,
            tool_call: ToolCall,
            policy: ToolPolicy,
    ) -> bool:
        """展示工具权限和名称，仅接受明确的 y/yes 确认。"""
        print(
            f"工具 {tool_call.tool_name} 请求 {policy.access} 权限，是否允许执行？"
        )
        answer = input("输入 y 确认，其他内容拒绝：").strip().lower()
        return answer in {"y", "yes"}
