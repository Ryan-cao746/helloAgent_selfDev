
from project1.user_input_interface.base import UserInputInterface, InputParams


class CilUserInput(UserInputInterface):
    def get_input(self) -> InputParams:

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