"""基于 TF-IDF 向量和余弦相似度的中文检索。

将「构建索引」与「查询」拆分为两个阶段，便于调用方在语料不变时复用索引，
避免每次查询都重新分词和拟合向量器。
"""
from typing import Any, Dict, List, Tuple

import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from project1.memory.memory_item import MemoryItem

_STOP_WORDS = ["的", "是", "了", "在", "和", "也", "之", "一个", "一种"]


def chinese_tokenize(text: str) -> str:
    """使用 jieba 进行中文分词，返回空格连接的字符串。"""
    return " ".join(jieba.lcut(text))


def build_tfidf_index(documents: List[str]) -> Tuple[TfidfVectorizer, Any]:
    """对文档列表分词并拟合 TF-IDF 索引，返回 (向量器, 文档矩阵)。"""
    tokenized_docs = [chinese_tokenize(doc) for doc in documents]
    vectorizer = TfidfVectorizer(
        token_pattern=r'(?u)\b\w+\b',
        stop_words=_STOP_WORDS,
        max_df=1.0,
        min_df=1,
    )
    tfidf_matrix = vectorizer.fit_transform(tokenized_docs)
    return vectorizer, tfidf_matrix


def query_tfidf(query: str, vectorizer: TfidfVectorizer, tfidf_matrix: Any) -> List[float]:
    """使用已有索引对查询向量化，返回查询与每条文档的余弦相似度。"""
    query_vector = vectorizer.transform([chinese_tokenize(query)])
    similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
    return [float(s) for s in similarities]


def try_tfidf_search(query: str, memories_str_list: List[str]) -> List[float]:
    """返回每条文本与查询的 TF-IDF 余弦相似度评分列表（一次性构建索引）。"""
    if not memories_str_list:
        return []
    vectorizer, tfidf_matrix = build_tfidf_index(memories_str_list)
    return query_tfidf(query, vectorizer, tfidf_matrix)


def try_tfidf_search_in_memory(query: str, memories: Dict[str, MemoryItem]) -> Dict[str, float]:
    """返回以记忆 ID 为键、查询相似度为值的评分字典。"""
    memory_list: List[MemoryItem] = list(memories.values())
    memories_str_list = [memory.content for memory in memory_list]
    res_list = try_tfidf_search(query, memories_str_list)
    res_dict: Dict[str, float] = {}
    for i in range(len(memory_list)):
        res_dict[memory_list[i].id] = res_list[i]
    return res_dict


if __name__ == '__main__':
    query = "神经网络算法有哪些"
    documents = [
        "机器学习是人工智能的核心技术之一",
        "深度学习是机器学习的一个重要分支，基于神经网络",
        "自然语言处理是人工智能的重要应用领域",
        "计算机视觉也是人工智能的重要研究方向",
        "支持向量机是一种经典的机器学习算法",
    ]
    res = try_tfidf_search(query, documents)
    print(res)
