from abc import ABC, abstractmethod
from typing import Literal


class InputParams:
    """参数传递类"""
    def __init__(
            self,
            input_text: str,
            input_type: Literal["Talk", "Stop", "Error"] = "Talk"
    ):
        self.input_text = input_text
        self.input_type = input_type

class UserInputInterface(ABC):
    """输入界面接口，用于适配不同的输入传递策略"""

    @abstractmethod
    def get_input(self) -> InputParams:
        """获取适用于llm的用户提示输入"""
        pass