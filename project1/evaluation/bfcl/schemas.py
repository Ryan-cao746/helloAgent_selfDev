"""Pydantic schemas used by the lightweight BFCL evaluation runner."""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BFCLFunctionSpec(BaseModel):
    """OpenAI-style function documentation from a BFCL prompt entry."""

    model_config = ConfigDict(extra="allow")

    name: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)

    @property
    def required_parameter_names(self) -> set[str]:
        """Return required parameter names from common BFCL schema shapes."""
        required = self.parameters.get("required", [])
        if isinstance(required, list):
            return {str(item) for item in required}
        return set()

    @property
    def parameter_properties(self) -> dict[str, Any]:
        """Return parameter property definitions, tolerating loose schemas."""
        properties = self.parameters.get("properties", {})
        if isinstance(properties, dict):
            return properties
        return {}


class BFCLCase(BaseModel):
    """One BFCL JSONL prompt entry."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    question: Any
    functions: list[BFCLFunctionSpec] = Field(alias="function", min_length=1)

    def conversation_text(self) -> str:
        """Flatten BFCL's nested question format into readable dialogue text."""
        messages: list[str] = []

        def collect(value: Any) -> None:
            if isinstance(value, dict):
                role = str(value.get("role", "user"))
                content = value.get("content")
                if content is not None:
                    messages.append(f"{role}: {content}")
                return
            if isinstance(value, list):
                for item in value:
                    collect(item)
                return
            if isinstance(value, str):
                messages.append(f"user: {value}")

        collect(self.question)
        return "\n".join(messages)


class BFCLGenerationRecord(BaseModel):
    """Debug record for one generated BFCL result."""

    id: str
    result: str
    status: Literal["success", "failed"]
    latency_ms: float = Field(ge=0)
    error: str | None = None
    raw_decision: dict[str, Any] | None = None

    def to_official_record(self) -> dict[str, str]:
        """Return the minimal shape consumed by the official BFCL evaluator."""
        return {
            "id": self.id,
            "result": self.result,
        }


class BFCLRunSummary(BaseModel):
    """Aggregate metadata for a BFCL generation run."""

    model_name: str
    dataset: str
    category: str
    total: int
    succeeded: int
    failed: int
    output_file: str
    trace_file: str
    summary_file: str
    started_at: datetime
    finished_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    duration_ms: float = Field(ge=0)
