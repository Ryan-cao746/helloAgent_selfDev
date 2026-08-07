
from project1.user_input_interface.base import UserInputInterface


class CilUserInput(UserInputInterface):
    def get_input_text(self) -> str:
        print("---- 请输入用户提示词 ----")
        return input("你的提示词：")