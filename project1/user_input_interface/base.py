from abc import ABC, abstractmethod

class UserInputInterface(ABC):
    """输入界面接口，用于适配不同的输入传递策略"""

    @abstractmethod
    def get_input_text(self) -> str:
        """获取适用于llm的用户提示输入"""
        pass