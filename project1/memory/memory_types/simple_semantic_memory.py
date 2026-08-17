"""从本地 Markdown 资料构建并检索只读语义记忆。"""

from project1.config.memory_config import MemoryConfig
from project1.memory.memory_item import MemoryItem
from project1.memory.memory_types.base import BaseMemory
from typing import List
from uuid import uuid4
from project1.supportive_functions.tfidf_search import try_tfidf_search_in_memory
from datetime import datetime

class SimpleSemanticMemory(BaseMemory):
    """按段落加载本地资料，并使用 TF-IDF 进行相关性检索。"""

    def __init__(self, memory_config:MemoryConfig, debug_mode:bool = False):
        super().__init__(memory_config=memory_config)
        self.debug_mode = debug_mode
        self.extract_from_library()

    def add(self, memory_item:MemoryItem):
        """按 ID 保存或覆盖一条语义记忆。"""
        self.memories[memory_item.id] = memory_item

    def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
        """返回与查询文本 TF-IDF 相似度最高的语义记忆。"""

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
        """读取资料目录中的全部 Markdown 文件并按段落导入。"""
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
        """将非空段落转换为独立的语义记忆条目。"""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]   # 划分段落

        for paragraph in paragraphs:
            memory = MemoryItem(
                id=f"semantic-{uuid4()}",
                content=paragraph,
                importance=1,
                created_at=datetime.now(),
                role="system"
            )
            self.memories[memory.id] = memory

if __name__ == "__main__":
    memory_config = MemoryConfig()
    mem = SimpleSemanticMemory(memory_config=memory_config)
    for key, value in mem.memories.items():
        print(f"{key}: {value.content}")
