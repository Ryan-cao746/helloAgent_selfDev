"""定义模型决策协议以及 Agent 运行轨迹的数据结构。"""

from datetime import datetime, timezone
from typing import Literal, TypeAlias
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from project1.tools.base import ToolCall, ToolResult
from project1.core.run_lifecycle import (
    RunErrorCode,
    RunStatus,
    RunTransition,
)


class ToolDecision(BaseModel):
    """模型返回的工具调用决策；额外字段会被拒绝。"""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["tool"]
    reasoning_summary: str = ""
    tool_calls: list[ToolCall] = Field(min_length=1)


class FinishDecision(BaseModel):
    """模型返回的结束决策，包含面向用户的非空最终回答。"""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["finish"]
    reasoning_summary: str = ""
    final_answer: str = Field(min_length=1)

    @field_validator("final_answer")
    @classmethod
    def strip_final_answer(cls, value: str) -> str:
        """去除回答首尾空白，并拒绝清理后的空字符串。"""
        value = value.strip()
        if not value:
            raise ValueError("final_answer 不能为空")
        return value


AgentDecision: TypeAlias = ToolDecision | FinishDecision

_DECISION_ADAPTER = TypeAdapter(AgentDecision)


def parse_agent_decision(text: str) -> AgentDecision:
    """将模型返回的 JSON 文本解析为受严格校验的决策对象。"""
    return _DECISION_ADAPTER.validate_json(text.strip())


class AgentStepRecord(BaseModel):
    """记录一步模型决策、耗时以及可选的工具结果或错误。"""

    step_number: int = Field(ge=1)
    decision: AgentDecision | None = None
    llm_duration_ms: float = Field(default=0, ge=0)
    tool_results: list[ToolResult] = Field(default_factory=list)
    error: str | None = None


class AgentRunResult(BaseModel):
    """单次运行的完整结果，供调用方、轨迹展示和故障定位使用。"""

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    status: RunStatus
    output: str
    step_count: int = Field(default=0, ge=0)
    error: str | None = None
    error_code: RunErrorCode | None = None
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    finished_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    duration_ms: float = Field(default=0, ge=0)
    context_duration_ms: float = Field(default=0, ge=0)
    steps: list[AgentStepRecord] = Field(default_factory=list)
    transitions: list[RunTransition] = Field(default_factory=list)
