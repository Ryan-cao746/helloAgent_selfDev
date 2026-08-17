"""提供仅保存当前轮次内容的轻量工作记忆。"""

from typing import List

from project1.memory.memory_item import MemoryItem
from project1.memory.memory_types.base import BaseMemory


class SimpleWorkingMemory(BaseMemory):
    """不做检索和持久化的工作记忆实现。"""

    def __init__(self):
        """初始化不受容量配置约束的内存存储。"""
        super().__init__()

    def add(self, memory_item:MemoryItem):
        """按 ID 保存或覆盖一条工作记忆。"""
        self.memories[memory_item.id] = memory_item

    def retrieve(self, query:str, limit:int=5, **kwargs) -> List[MemoryItem]:
        """工作记忆不做相关性检索，调用方应直接读取全部条目。"""
        return []
