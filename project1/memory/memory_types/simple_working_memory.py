# 简单记忆类型，用于论证架构合理性。没有什么功能
from typing import List

from project1.memory.memory_item import MemoryItem
from project1.memory.memory_types.base import BaseMemory


class SimpleWorkingMemory(BaseMemory):
    def __init__(self):
        """调用父类方法，仅仅初始化记忆存储列表，不用config"""
        super().__init__()

    def add(self, memory_item:MemoryItem):
        """朴素实现"""
        self.memories[memory_item.id] = memory_item

    def retrieve(self, query:str, limit:int=5, **kwargs) -> List[MemoryItem]:
        """无任何具体查询逻辑"""
        return []