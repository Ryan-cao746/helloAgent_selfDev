from abc import ABC, abstractmethod
import re
from typing import TypedDict, List, Literal

from project1.memory.memory_manager import MemoryManager
from project1.tools.registry import ToolRegistry


class PhrasedResult(TypedDict):
    thought: str
    content:str
    state:Literal["Finish", "Action", "Pass"]

# 处理输出的基类
class BaseResponsePhraser(ABC):
    def __init__(self, tool_registry:ToolRegistry = None):
        self.tool_registry = tool_registry  # 一定要注入工具管理的依赖

    @abstractmethod
    def phrase_response(self, text:str) -> PhrasedResult:   # 规定子类的结果必须是这个参数类型
        pass

    def phrase_output(self,text: str):
        """提取thought和action"""
        # Thought要匹配到Action:或文本末尾
        thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|$)", text,
                                  re.DOTALL)  # 跳过 Thought: 后面可能存在的空白。非贪婪、条件地捕获内容直到Action:或文末。re.DOTALL指让正则表达式中的点号（.）匹配包括换行符（\n）在内的任意字符。

        # Action要匹配到文本末尾
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    def phrase_action(self,action_text: str):
        """从action里提取tool_calls"""
        match = re.match(r"(\w+)\[(.*)]", action_text, re.DOTALL)  # 方括号前和后的分别为两个捕获组
        if match:
            return match.group(1), match.group(2)
        return None, None