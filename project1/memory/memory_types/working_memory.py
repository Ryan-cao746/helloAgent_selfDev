# 工作记忆类型，负责短期记忆存储，存储当前会话中的临时信息，快速访问和自动清理
from typing import List

from project1.memory.memory_types.base import BaseMemory
from project1.config.memory_config import MemoryConfig
from project1.memory.memory_item import MemoryItem
from project1.supportive_functions.keyword_search import keyword_search_with_scores_in_memory
from project1.supportive_functions.tfidf_search import try_tfidf_search_in_memory


class WorkingMemory(BaseMemory):
    """
    工作记忆实现
    容量有限，默认50条，有ttl自动定时清理
    纯内存存储
    混合检索
    """
    def __init__(self, memory_config:MemoryConfig = None):
        super().__init__(memory_config)
        if memory_config is None:
            self.working_memory_capacity = 5
        else :
            self.working_memory_capacity = memory_config.working_memory_capacity

    def add(self, memory_item:MemoryItem) -> str:
        """添加工作记忆"""
        self._expire_old_memories() # 过期清理

        if len(self.memories) >= self.working_memory_capacity: # 超出容量清理
            self._remove_low_priority_memories()

        self.memories.append(memory_item) # 添加
        return memory_item.id

    def retrieve(self, query:str, limit:int=5, **kwargs) -> List[MemoryItem]:
        """混合检索，TF-IDF向量化和关键词匹配"""
        self._expire_old_memories() # 清理过期工作记忆

        # TF-IDF向量化检索，返回每一项对应的评分
        vector_scores = try_tfidf_search_in_memory(query=query, memories= self.memories) # 专门定制的根据记忆列表查询
        keyword_scores = keyword_search_with_scores_in_memory(memories=self.memories, keyword=query)
        # 计算综合分数
        base_relevance = [vector_scores[i]*0.7 + keyword_scores[i]*0.3 for i in range(len(self.memories))]
        importance_weight = [0.8+memory.importance*0.4 for memory in self.memories]
        final_score = [(i, base_relevance[i]*importance_weight[i]) for i in range(len(self.memories))]
        final_score.sort(key=lambda x: x[1], reverse=True) # 按分数降序
        return [self.memories[final_score[i][0]] for i in range(limit)] # 根据排序获取所求的记忆列表
