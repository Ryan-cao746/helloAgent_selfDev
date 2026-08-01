# Agent基类接口，其他的Agent都基于这个基类构造，实现相关调用协议统一化
from abc import ABC, abstractmethod #Python中的抽象类
from typing import Optional, List

from project1.core.config import Config
from project1.core.llm_client import HelloAgentsLLM
from project1.core.message import Message

# Agent这个抽象基类默认不包含tool_registry。所以说次级方法在继承时需要在超类的init方法外面加上这个字段
class Agent(ABC):

    def __init__(
            self,
            name:str,
            llm_client: HelloAgentsLLM,
            system_prompt: Optional[str] = None,
            config: Optional[Config] = None
    ):
        self.name = name
        self.llm_client = llm_client
        self.system_prompt = system_prompt
        self.config = config
        self.history: List[Message] = [] # 至关重要的历史记录部分

    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str: #不关心具体实现，接口方法，所有子类必须实现之
        """运行Agent"""
        pass

    def add_message(self, message: Message):
        """添加到历史消息记录"""
        self.history.append(message)

    def clear_history(self):
        """清空历史记录"""
        self.history.clear()

    def get_history(self) -> List[Message]:
        """获取历史记录"""
        return self.history.copy() # 用copy是防止发生引用的问题

    def __str__(self) -> str:
        return str(self.get_history())
