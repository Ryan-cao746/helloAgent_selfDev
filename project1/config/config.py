"""集中管理 Agent、工具预算和运行时选项，并支持环境变量覆盖。"""

from typing import Optional, Dict, Any
import os
from pydantic import BaseModel, Field


class Config(BaseModel):
    """应用级配置；字段默认值适用于本地小规模运行。"""

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
    max_tool_calls:int = Field(default=3, ge=1)
    max_repeated_tool_calls:int = Field(default=2, ge=1)
    max_total_tool_output_chars:int = Field(default=40_000, ge=1)
    run_timeout_seconds:Optional[float] = Field(default=120, gt=0)

    # 多轮对话配置
    max_ask:int = 5

    # 其他配置
    max_history_length:int = 100

    @classmethod
    def from_env(cls) -> "Config":
        """读取受支持的环境变量并创建配置实例。"""
        return cls(
            debug = os.getenv("DEBUG", default="False").lower() == "true",
            log_level = os.getenv("LOG_LEVEL", default="INFO"),
            temperature = float(os.getenv("TEMPERATURE", default="0.7")),
            max_tokens = int(os.getenv("MAX_TOKENS", default="100")) if os.getenv("MAX_TOKENS") else None,
            max_tool_calls = int(os.getenv("MAX_TOOL_CALLS", default="3")),
            max_repeated_tool_calls = int(
                os.getenv("MAX_REPEATED_TOOL_CALLS", default="2")
            ),
            max_total_tool_output_chars = int(
                os.getenv("MAX_TOTAL_TOOL_OUTPUT_CHARS", default="40000")
            ),
            run_timeout_seconds = float(
                os.getenv("RUN_TIMEOUT_SECONDS", default="120")
            ),
        )
    def to_dict(self) -> Dict[str, Any]:
        """返回包含当前配置值的普通字典。"""
        return self.model_dump()
