# 叫AI帮忙写的关键词查询。使用BM25评分标准
# 改过了，保证不排序且不管什么情况都有完整输出

import math

from project1.memory.memory_item import MemoryItem


def keyword_search_with_scores(
    items: list[str],
    keyword: str,
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    """Return matching strings and their BM25 relevance scores."""
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
    idf = math.log(
        1 + (document_count - matched_count + 0.5) / (matched_count + 0.5)
    )

    results: list[float] = []
    for original, normalized in zip(items, normalized_items):
        frequency = normalized.count(keyword)
        if frequency == 0:
            score = 0.0
        else:
            length_factor = 1 - b + b * len(normalized) / average_length
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
    """定制的根据memories的关键词搜索"""
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
