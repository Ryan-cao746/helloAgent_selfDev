from datetime import datetime
from typing import Dict, List, Literal

from project1.config.memory_config import MemoryConfig
from project1.memory.memory_item import MemoryItem
from project1.memory.memory_types.base import BaseMemory
from project1.memory.memory_types.simple_working_memory import SimpleWorkingMemory
from project1.memory.memory_types.working_memory import WorkingMemory


class MemoryManager:
    """记忆管理器，统一的记忆操作接口"""

    def __init__(
            self,
            config:MemoryConfig = None,
            user_id:str = "default_user",
            enable_working_memory:bool = False,
            enable_episodic_memory:bool = False,
            working_memory:BaseMemory = None,
            episodic_memory:BaseMemory = None,
    ):
        self.config = config
        self.user_id = user_id

        self.memory_types: Dict[str, BaseMemory] = {}

        if enable_working_memory:
            if working_memory is None:
                print("未配置相应的工作记忆类型")
                return
            self.memory_types["working"] = working_memory
        if enable_episodic_memory:
            if episodic_memory is None:
                print("未配置相应的情景记忆类型")
                return
            self.memory_types["episodic"] = episodic_memory

    def add(self, type:str, content:str, role:Literal["user", "assistant", "tool"]):
        """添加记忆的统一方法"""
        memory = MemoryItem(
            id = f"{type}-{datetime.now()}",
            content = content,
            importance= 1,   # 没有做重要性筛选
            created_at = datetime.now(),
            role=role
        )

        if not type in self.memory_types:
            print(f"不存在记忆种类{type}")
            return
        self.memory_types[type].add(memory) # 这个add中，每个记忆类型都有各自的逻辑，已经写进去了过期清理等操作

    def clear(self, type:str):
        """清除某个特定记忆类型的方法"""
        if not type in self.memory_types:
            print(f"不存在记忆种类{type}")
            return
        self.memory_types[type].memories.clear() # 清除对应类型的记忆

    def search(self, type:str, query:str) -> List[MemoryItem]:
        """根据查询字符串检索某个特定类别的记忆"""
        return self.memory_types[type].retrieve(query)

    def add_new_memory_type(self, type:str, base_memory:BaseMemory):
        """添加新的记忆类型。这样我就不需要两个enable参量了"""
        self.memory_types[type] = base_memory

    def get_all_by_type(self, type:str) -> List[MemoryItem]:
        res_dict = self.memory_types[type].get_all_memories()
        return [res for res in res_dict.values()]

    def update_memory_content(self, type:str, id:str, new_content:str):
        self.memory_types[type].memories[id].content = new_content

    def delete_memory_by_type(self, type:str, id:str):
        del self.memory_types[type].memories[id]

    def print_all_memory_by_type(self, type:str):
        for memory in self.memory_types[type].memories.values():
            print(f"记忆类型:{type}")
            print(f"id:{memory.id}, role:{memory.role}, content:{memory.content}")


