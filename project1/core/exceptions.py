"""项目核心层使用的异常类型。"""

class LLMClientError(RuntimeError):
    """模型服务请求失败或响应无法按协议处理。"""
