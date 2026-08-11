from typing import Literal, TypeAlias
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from project1.tools.base import ToolCall


class ToolDecision(BaseModel):
    """A validated request from the model to execute one tool.
    序列化的工具执行请求
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["tool"]
    reasoning_summary: str = ""
    tool_call: ToolCall


class FinishDecision(BaseModel):
    """A validated request from the model to finish the current run.
    序列化的轮次结束请求
    """

    model_config = ConfigDict(extra="forbid")   # 严格参数校验，禁止出现额外的参数值

    kind: Literal["finish"]
    reasoning_summary: str = ""
    final_answer: str = Field(min_length=1)

    @field_validator("final_answer")
    @classmethod
    def strip_final_answer(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("final_answer 不能为空")
        return value


AgentDecision: TypeAlias = ToolDecision | FinishDecision

_DECISION_ADAPTER = TypeAdapter(AgentDecision)


def parse_agent_decision(text: str) -> AgentDecision:
    """Parse one strict JSON decision returned by the model."""
    return _DECISION_ADAPTER.validate_json(text.strip())


class AgentStepRecord(BaseModel):
    """One model decision and its optional tool observation.
    模型响应的步骤记录，用于回退
    """


    step_number: int = Field(ge=1)
    decision: AgentDecision
    tool_result: str | None = None


class AgentRunResult(BaseModel):
    """Structured result retained by the agent after every run.
    每次运行的结构化结果
    """

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    status: Literal["finished", "failed"]
    output: str
    step_count: int = Field(default=0, ge=0)
    error: str | None = None
    steps: list[AgentStepRecord] = Field(default_factory=list)
