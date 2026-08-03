# 工作记忆类型，负责短期记忆存储，存储当前会话中的临时信息，快速访问和自动清理
from typing import List

from project1.memory.base import BaseMemory
from project1.memory.memory_config import MemoryConfig
from project1.memory.memory_item import MemoryItem


class WorkingMemory(BaseMemory):
    """
    工作记忆实现
    容量有限，默认50条，有ttl自动定时清理
    纯内存存储
    混合检索
    """
    def __init__(self, memory_config:MemoryConfig):
        super().__init__(memory_config)

    def add(self, memory_item:MemoryItem) -> str:
        """添加工作记忆"""
        self._expire_old_memories() # 过期清理

        if len(self.memories) >= self.memory_config.working_memory_capacity: # 超出容量清理
            self._remove_low_priority_memories()

        self.memories.append(memory_item) # 添加
        return memory_item.id

    def retrieve(self, query:str, limit:int=5, **kwargs) -> List[MemoryItem]:
        """"""