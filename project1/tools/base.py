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

    def to_str(self) -> str:
        return f"""
        name: {self.name}
        description: {self.description}
        required: {self.required}
        default: {self.default}       
        """

class Tool(ABC):
    """工具基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description # description至关重要，用于提供工具参数等信息

    @abstractmethod
    def run(self, parameters:Dict[str,Any]) -> str:
        """执行工具"""
        pass

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数"""
        pass

    def get_full_description(self) -> str: # 这玩意把工具描述和参数结合在一起
        params_text = []
        for param in self.get_parameters():
            param_text = param.to_str() # 单个参数转换为字符串
            params_text.append(param_text) # 全部加入

        params_description = "\n".join(params_text)
        return f"""
        
        ## 工具信息
        name: {self.name}
        description: {params_description}
        
        ## 参数信息
        {params_description}
        
        """
