# 配置管理类，集中代码中硬编码的配置参数，并支持从环境变量中读取
from typing import Optional, Dict, Any
import os
from pydantic import BaseModel


class Config(BaseModel):
    """配置类"""

    # LLM配置
    default_model:str = "gpt-5.6"
    default_provider:str = "openai"
    temperature:float = 0.7
    max_tokens:Optional[int] = None #默认无限制

    # 系统配置
    debug:bool = False
    log_level:str = "INFO"

    # Agent配置
    max_steps:int = 5

    # 多轮对话配置
    max_ask:int = 5

    # 其他配置
    max_history_length:int = 100

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量创建配置"""
        return cls(
            debug = os.getenv("DEBUG", default="False").lower() == "true",
            log_level = os.getenv("LOG_LEVEL", default="INFO"),
            temperature = float(os.getenv("TEMPERATURE", default="0.7")),
            max_tokens = int(os.getenv("MAX_TOKENS", default="100")) if os.getenv("MAX_TOKENS") else None,
        )
        # cls 永远指向调用者所在的类，自动识别调用者

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump() #这玩意似乎比dict强大，且dict早不用了