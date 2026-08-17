"""定义 Agent 与模型之间传递的统一消息格式。"""

from datetime import datetime
from typing import Dict, Optional, Any, Literal

from pydantic import BaseModel

MessageRole = Literal["user", "assistant", "system", "tool"]

class Message(BaseModel):
    """封装消息角色、正文以及可选的时间和元数据。"""

    content: str
    role: MessageRole
    timestamp: datetime = None
    metadata: Optional[Dict[str, Any]] = None

    def __init__(self, content:str, role:MessageRole, **kwargs):
        super().__init__(
            content = content,
            role = role,
            timestamp=kwargs.get("timestamp", datetime.now()),
            metadata = kwargs.get("metadata", {})
        )

    def to_dict(self) -> Dict[str, Any]:
        """返回模型接口所需的 role/content 字典。"""
        return {
            "role": self.role,
            "content": self.content,
        }

    def __str__(self) -> str:
        """返回适合日志阅读的单行消息文本。"""
        return f"[{self.role}] {self.content}"
