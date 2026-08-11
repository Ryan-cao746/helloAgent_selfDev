from project1.config.memory_config import MemoryConfig
from project1.memory.memory_item import MemoryItem
from project1.memory.memory_types.base import BaseMemory
from typing import List
from uuid import uuid4
from project1.supportive_functions.tfidf_search import try_tfidf_search_in_memory
from datetime import datetime

class SimpleSemanticMemory(BaseMemory):
    def __init__(self, memory_config:MemoryConfig, debug_mode:bool = False):     # 这个需要传入记忆配置，因为需要知道文档路径
        super().__init__(memory_config=memory_config)
        self.debug_mode = debug_mode
        self.extract_from_library() # 初始化时加载数据。这有一个好处，就是可以直接继承BaseMemory的接口，拓展性更好

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

    def extract_from_library(self):
        if self.memory_config is None:
            raise ValueError("未注入语义记忆的配置类")

        folder = self.memory_config.library_root    # 加载文件
        for md_file in folder.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            if self.debug_mode:
                print(f"=== {md_file.name} ===")
                print(content)
            self.extract_memory_item(content)   # 读取到字典中

    def extract_memory_item(self, text:str):
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]   # 划分段落

        for paragraph in paragraphs:
            memory = MemoryItem(
                id=f"semantic-{uuid4()}",  # uuid4()生成数据库主键
                content=paragraph,
                importance=1,  # 没有做重要性筛选
                created_at=datetime.now(),
                role="system"
            )
            self.memories[memory.id] = memory

if __name__ == "__main__":
    memory_config = MemoryConfig()
    mem = SimpleSemanticMemory(memory_config=memory_config)
    for key, value in mem.memories.items():
        print(f"{key}: {value.content}")

