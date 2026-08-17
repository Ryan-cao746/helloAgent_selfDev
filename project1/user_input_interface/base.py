"""定义会话输入和高风险工具确认所需的界面抽象。"""

from abc import ABC, abstractmethod
from typing import Literal

from project1.tools.base import ToolCall, ToolPolicy


class InputParams:
    """一次用户输入及其会话控制类型。"""
    def __init__(
            self,
            input_text: str,
            input_type: Literal["Talk", "Stop", "Error"] = "Talk"
    ):
        self.input_text = input_text
        self.input_type = input_type

class UserInputInterface(ABC):
    """适配命令行或其他前端的用户输入与工具确认接口。"""

    @abstractmethod
    def get_input(self) -> InputParams:
        """读取下一条用户输入或会话控制指令。"""
        pass

    def confirm_tool_call(
            self,
            tool_call: ToolCall,
            policy: ToolPolicy,
    ) -> bool:
        """确认高风险工具调用；默认拒绝，具体界面可覆盖。"""
        return False
