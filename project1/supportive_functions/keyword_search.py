"""基于 BM25 评分的关键词检索，返回每条记忆与关键词的相关性评分。

不进行排序和截断，完整返回每项的评分，方便调用方据此计算综合得分。
"""

import math

from project1.memory.memory_item import MemoryItem


def keyword_search_with_scores(
    items: list[str],
    keyword: str,
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    """返回每条文本与关键词的 BM25 相关性评分（不排序、不截断）。

    ``k1`` 控制词频饱和程度，``b`` 控制文档长度归一化强度。
    """
    keyword = keyword.strip().casefold()
    if not items or not keyword:
        print("查询失败，需要相关参数不为空")
        return []

    normalized_items = [item.casefold() for item in items]
    document_count = len(items)
    matched_count = sum(keyword in item for item in normalized_items)
    if matched_count == 0:
        var = [0.0 for i in range(document_count)]
        return var

    average_length = sum(len(item) for item in normalized_items) / document_count
    # 逆文档频率：关键词越罕见，权重越高。
    idf = math.log(
        1 + (document_count - matched_count + 0.5) / (matched_count + 0.5)
    )

    results: list[float] = []
    for original, normalized in zip(items, normalized_items):
        frequency = normalized.count(keyword)
        if frequency == 0:
            score = 0.0
        else:
            # 文档长度归一化，避免长文档因词频天然更高而占优。
            length_factor = 1 - b + b * len(normalized) / average_length
            # BM25 词频饱和公式。
            score = idf * (frequency * (k1 + 1)) / (frequency + k1 * length_factor)
        results.append(round(score, 4))

    return results

def keyword_search_with_scores_in_memory(
        memories: list[MemoryItem],
        keyword: str,
        *,
        k1: float = 1.5,
        b: float = 0.75
) -> list[float]:
    """提取记忆正文后，返回每条记忆与关键词的相关性评分。"""
    memories_str_list = [memory.content for memory in memories]  # 获取str形式的列表
    return keyword_search_with_scores(memories_str_list, keyword, k1=k1, b=b)

if __name__ == "__main__":
    contents = [
        "Python 入门",
        "使用 Python 可以进行数据分析",
        "Python 简单易学，Python 也适合自动化开发",
        "Java 常用于企业级应用开发",
    ]

    for score in keyword_search_with_scores(contents, "python"):
        print(f"{score:.4f}")
