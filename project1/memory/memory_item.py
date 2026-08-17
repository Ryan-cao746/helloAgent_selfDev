"""定义各类记忆实现共享的单条记忆数据结构。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class MemoryItem(BaseModel):
    """带来源角色、重要性和可选过期时间的记忆条目。"""

    id: str
    role:Literal["user", "assistant", "tool", "system"] = "user"
    content: str
    importance: float = 1.0
    created_at: datetime = None
    expires_at: datetime | None = None

    def __init__(self,
                 id:str,
                 content:str,
                 importance:float = 1.0,
                 role:Literal["user", "assistant", "tool", "system"] = "user",
                 created_at:datetime = None,
                 expires_at:datetime = None
                 ):
        super().__init__(
            id = id,
            content = content,
            importance = importance,
            created_at = created_at,
            expires_at = expires_at,
            role = role,
        )


