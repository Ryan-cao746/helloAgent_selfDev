# 定义了统一的消息格式，便于智能体和模型之间信息传递的标准化，还有用于历史记录的功能
from datetime import datetime
from typing import Dict, Optional, Any, Literal

from pydantic import BaseModel #A base class for creating Pydantic models.

MessageRole = Literal["user", "assistant", "system", "tool"] # 定义了消息，只能取几个类型之一个
# 这直接对应 OpenAI API 的规范，保证了类型安全

class Message(BaseModel): #基于BaseModel，封装了各种类型检查机制
    """消息类"""

    content: str
    role: MessageRole
    timestamp: datetime = None
    metadata: Optional[Dict[str, Any]] = None # 这个变量值要么是指定的类型，要么是None # Metadata（元数据）是关于智能体（Agent）自身的结构化描述信息
    #这个时间戳和元数据为未来日志等功能留出空间

    def __init__(self, content:str, role:MessageRole, **kwargs): #**kwargs 允许你将不定数量的键值对，作为一个字典传入函数。** 会将多余的关键字参数打包成一个字典。
        # 调用父类提供的初始化方法
        super().__init__(
            content = content,
            role = role,
            timestamp=kwargs.get("timestamp", datetime.now()),
            metadata = kwargs.get("metadata", {})
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式(OpenAI API格式)"""
        return {
            "role": self.role,
            "content": self.content,
        }

    def __str__(self) -> str:
        """转换成字典"""
        return f"[{self.role}] {self.content}"