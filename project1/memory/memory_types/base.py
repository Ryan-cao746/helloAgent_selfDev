from abc import ABC, abstractmethod
from typing import List, Dict

from datetime import datetime

from project1.config.memory_config import MemoryConfig
from project1.memory.memory_item import MemoryItem

class BaseMemory(ABC):
    def __init__(self, memory_config:MemoryConfig = None):
        self.memory_config = memory_config
        self.memories: Dict[str, MemoryItem] = dict()  # 主键搭配记忆体的形式

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
        for key, value in self.memories.items():
            if value.expires_at < datetime.now():
                del self.memories[key]
    def _remove_low_priority_memories(self):
        """按重要性排序再删除不重要的记忆"""
        memory_list:List[MemoryItem] = []
        for key, value in self.memories.items():
            memory_list.append(value)
        memory_list.sort(key=lambda x: x.importance, reverse=True)
        for i in range(self.memory_config.working_memory_capacity, len(memory_list)):
            del self.memories[memory_list[i].id]


    def get_all_memories(self) -> Dict[str, MemoryItem]:
        return self.memories