# 记忆条目
from datetime import datetime

from pydantic import BaseModel


class MemoryItem(BaseModel):
    """
    记忆条目
    重要的字段：创建时间戳和过期时间戳，ttl的值由config给出
    """

    id: str = None
    content: str
    importance: float
    created_at: datetime = None
    # 显式设置默认值为 None，明确告知 Pydantic 该字段是可选的
    expires_at: datetime | None = None

    def __init__(self,
                 id:str,
                 content:str,
                 importance:float,
                 created_at:datetime = None, # 创建的时间戳
                 expires_at:datetime = None  # 过期的时间戳
                 ):
        super().__init__(
            id = id,
            content = content,
            importance = importance,
            created_at = created_at,
            expires_at = expires_at
        )
