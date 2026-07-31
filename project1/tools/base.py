# 工具抽象基类
# 所有工具都使用一致的调用和值返回逻辑
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel

# 实现复杂工具参数验证和文档生成
class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool
    default: Any = None

class Tool(ABC):
    """工具基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, parameters:Dict[str,Any]) -> str:
        """执行工具"""
        pass

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        pass
