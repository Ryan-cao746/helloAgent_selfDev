# TF-IDF向量化检索
# 我让这些函数返回的是所有项的相似度评分，没有排序等东西，因为要计算综合评分，所以不能忽略某一项
from typing import List, Dict

import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from project1.memory.memory_item import MemoryItem

def try_tfidf_search(query:str, memories_str_list:List[str]) -> List[float]:
    #memories_str_list = [memory.content for memory in memories] # 获取str形式的列表

    if memories_str_list.__len__() == 0:
        return []

    tokenized_docs = [chinese_tokenize(doc) for doc in memories_str_list]  # 逐个分词
    print("分词后的文档：")
    for i, doc in enumerate(tokenized_docs, 1):
        print(f"  文档{i}: {doc}")
    print()

    # ============ 3. 加载停用词（可选但推荐） ============
    # 常见中文停用词：的、是、了、在、和...
    # 这里简单列几个，实际项目应加载完整停用词表
    stop_words = ["的", "是", "了", "在", "和", "也", "之", "一个", "一种"]

    # ============ 4. TF-IDF 向量化 ============
    vectorizer = TfidfVectorizer(
        token_pattern=r'(?u)\b\w+\b',  # 匹配单个词（中文单字也算）
        stop_words=stop_words,  # 停用词过滤
        max_df=1.0,  # 过滤掉出现在超过 N% 文档中的词
        min_df=1,  # 过滤掉出现在少于 N 篇文档中的词
        # ngram_range=(1, 2),            # 可选：加入二元词组
        # sublinear_tf=True,             # 可选：对数压缩词频
    )

    tfidf_matrix = vectorizer.fit_transform(tokenized_docs)  # 向量化

    print(f"矩阵形状: {tfidf_matrix.shape}")
    print(f"词典大小: {len(vectorizer.vocabulary_)}")
    print(f"词典内容: {sorted(vectorizer.vocabulary_.keys())}\n")

    # ============ 5. 查看 IDF 值 ============
    feature_names = vectorizer.get_feature_names_out()
    print("各词的 IDF 值:")
    for word, idf_val in sorted(
            zip(feature_names, vectorizer.idf_),
            key=lambda x: x[1],
            reverse=True
    ):
        print(f"  {word}: {idf_val:.4f}")
    print()

    results = search(query, vectorizer, tfidf_matrix, top_k=3)

    return [float(result) for result in results]  # 结果的第二元是相似度。但是返回的类型是np.float64，可以转换一下

# Memory类型形式的查询
def try_tfidf_search_in_memory(query:str, memories:Dict[str, MemoryItem]) -> Dict[str, float]:

    memory_list:List[MemoryItem] = list(memories.values())

    memories_str_list = [memory.content for memory in memory_list] # 获取str形式的列表

    res_list = try_tfidf_search(query, memories_str_list)
    res_dict:Dict[str, float] = {}

    for i in range(memory_list.__len__()):
        res_dict[memory_list[i].id] = res_list[i]

    return res_dict

def chinese_tokenize(text:str) -> str:
    """使用jieba进行中文分词。"""
    # 英文天然用空格分隔单词，TfidfVectorizer 默认的正则表达式能直接切分。但中文没有空格，不分词的话整句话会被当成一个词，词典里全是句子，完全无法匹配。
    # jieba.lcut 返回列表，用空格连接成字符串
    # 因为 TfidfVectorizer 默认按空格/标点切分
    return " ".join(jieba.lcut(text))


# ============ 6. 检索函数 ============
def search(query, vectorizer, tfidf_matrix, top_k=3):
    """
    中文检索函数
    注意: 查询也必须走同样的分词 + transform 流程
    """
    # 查询分词
    query_tokenized = chinese_tokenize(query)
    print(f"查询分词结果: {query_tokenized}")

    # 查询向量化（必须用 transform，不能 fit_transform！）
    query_vector = vectorizer.transform([query_tokenized])

    # 计算余弦相似度
    similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()  # 计算余弦相似度

    # 排序取 Top-K
    #top_indices = np.argsort(similarities)[::-1][:top_k]

    return similarities

# 测试检索
if __name__ == '__main__':
    query = "神经网络算法有哪些"

    # ============ 1. 原始中文语料（未分词） ============
    documents = [
        "机器学习是人工智能的核心技术之一",
        "深度学习是机器学习的一个重要分支，基于神经网络",
        "自然语言处理是人工智能的重要应用领域",
        "计算机视觉也是人工智能的重要研究方向",
        "支持向量机是一种经典的机器学习算法",
    ]

    res = try_tfidf_search(query, documents)
    print(res)
