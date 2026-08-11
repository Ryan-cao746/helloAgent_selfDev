# 记忆条目
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class MemoryItem(BaseModel):
    """
    记忆条目
    重要的字段：创建时间戳和过期时间戳，ttl的值由config给出
    """

    id: str     # 现在id是必填字段
    role:Literal["user", "assistant", "tool", "system"] = "user"
    content: str
    importance: float = 1.0
    created_at: datetime = None
    # 显式设置默认值为 None，明确告知 Pydantic 该字段是可选的
    expires_at: datetime | None = None

    def __init__(self,
                 id:str,
                 content:str,
                 importance:float = 1.0,
                 role:Literal["user", "assistant", "tool", "system"] = "user",
                 created_at:datetime = None, # 创建的时间戳
                 expires_at:datetime = None  # 过期的时间戳
                 ):
        super().__init__(
            id = id,
            content = content,
            importance = importance,
            created_at = created_at,
            expires_at = expires_at,
            role = role,
        )


