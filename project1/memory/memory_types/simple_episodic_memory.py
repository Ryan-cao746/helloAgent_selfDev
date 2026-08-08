# 简单的情景记忆，用Python数组存储，现在不做持久化
from typing import List

from project1.memory.memory_item import MemoryItem
from project1.memory.memory_types.base import BaseMemory
from project1.supportive_functions.keyword_search import keyword_search_with_scores_in_memory
from project1.supportive_functions.tfidf_search import try_tfidf_search_in_memory


class SimpleEpisodicMemory(BaseMemory):
    def __init__(self):
        super().__init__()  # 调用父类的初始化方法，直接初始化memories列表

    def add(self, memory_item:MemoryItem):
        self.memories[memory_item.id] = memory_item

    def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
        """TF-IDF向量化检索"""

        # TF-IDF向量化检索，返回每一项对应的评分
        vector_scores = try_tfidf_search_in_memory(query=query, memories=self.memories)  # 专门定制的根据记忆列表查询
        #keyword_scores = keyword_search_with_scores_in_memory(memories=self.memories, keyword=query) # 这里去掉了关键词检索的功能。因为如果我的query要输入完整input，那么就不能使用关键词了
        # 计算综合分数

        importance_weight = {id:0.8 + memory.importance * 0.4 for id, memory in self.memories.items()}
        final_score = {id: (id,vector_scores[id] * 0.7 * importance_weight[id]) for id in self.memories.keys()}
        final_score_list = list(final_score.values())
        final_score_list.sort(key=lambda x: x[1], reverse=True)  # 按分数降序


        return [self.memories[final_score_list[i][0]] for i in range(min(limit, final_score_list.__len__()))]  # 根据排序获取所求的记忆列表