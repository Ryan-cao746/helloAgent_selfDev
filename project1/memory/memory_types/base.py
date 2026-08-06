from abc import ABC, abstractmethod
from typing import List

from datetime import datetime

from project1.config.memory_config import MemoryConfig
from project1.memory.memory_item import MemoryItem

class BaseMemory(ABC):
    def __init__(self, memory_config:MemoryConfig = None):
        self.memory_config = memory_config
        self.memories: List[MemoryItem] = []

    @abstractmethod
    def add(self, memory_item:MemoryItem) -> str:
        """添加记忆"""
        pass

    @abstractmethod
    def retrieve(self, query:str, limit:int=5, **kwargs) -> List[MemoryItem]:
        """记忆检索"""
        pass

    def _expire_old_memories(self):
        """清除过期的记忆"""
        # 如果当前时间大于应该予以清除的时间，则删除该记录
        for memory_item in self.memories:
            if memory_item.expires_at > datetime.now():
                self.memories.remove(memory_item)

    def _remove_low_priority_memories(self):
        """按重要性排序再删除不重要的记忆"""
        self.memories.sort(key=lambda memory_item: memory_item.importance, reverse=True)
        current_idx = 0
        for memory_item in self.memories:
            if current_idx >= self.memory_config.working_memory_capacity:
                self.memories.remove(memory_item)

    def get_all_memories(self) -> List[MemoryItem]:
        return self.memories