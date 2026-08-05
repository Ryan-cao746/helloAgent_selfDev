from datetime import datetime
from typing import Dict

from project1.config.memory_config import MemoryConfig
from project1.memory.memory_item import MemoryItem
from project1.memory.memory_types.base import BaseMemory
from project1.memory.memory_types.simple_memory import SimpleMemory
from project1.memory.memory_types.working_memory import WorkingMemory


class MemoryManager:
    """记忆管理器，统一的记忆操作接口"""

    def __init__(
            self,
            config:MemoryConfig = None,
            user_id:str = "default_user",
            enable_working: bool = True,
            enable_simple: bool = False,
    ):
        self.config = config
        self.user_id = user_id

        self.memory_types: Dict[str, BaseMemory] = {}

        if enable_working:
            self.memory_types["working"] = WorkingMemory(self.config)
        if enable_simple:
            self.memory_types["simple"] = SimpleMemory() # 这玩意不要config

    def add(self, type:str, content:str):
        """添加记忆的统一方法"""
        memory = MemoryItem(
            id = f"{type}-{datetime.now()}",
            content = content,
            importance= 1,   # 没有做重要性筛选
            created_at = datetime.now(),
        )

        if not type in self.memory_types:
            print(f"不存在记忆种类{type}")
            return
        self.memory_types[type].add(memory) # 这个add中，每个记忆类型都有各自的逻辑，已经写进去了过期清理等操作
