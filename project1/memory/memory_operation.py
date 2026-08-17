"""定义摘要 Agent 生成的记忆操作及批次级冲突校验。"""

from typing import Literal, Self
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class MemoryOperation(BaseModel):
    """一条经过运行时校验的记忆变更指令。"""

    model_config = ConfigDict(extra="forbid")

    operation: Literal["ADD", "UPDATE", "DELETE", "NOOP"]
    target_id: str | None = None
    content: str | None = Field(
        default=None,
        # ``summary`` 是旧版摘要协议使用的兼容字段名。
        validation_alias=AliasChoices("content", "summary"),
    )
    reasoning: str | None = None

    @field_validator("target_id", "content", mode="before")
    @classmethod
    def normalize_empty_string(cls, value):
        """将空白字符串规范化为 ``None``，便于后续必填校验。"""
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @model_validator(mode="after")
    def validate_required_fields(self) -> Self:
        """根据操作类型校验正文和目标 ID 是否齐全。"""
        if self.operation in {"ADD", "UPDATE"} and self.content is None:
            raise ValueError(f"{self.operation} 操作必须提供 content")
        if self.operation in {"UPDATE", "DELETE"} and self.target_id is None:
            raise ValueError(f"{self.operation} 操作必须提供 target_id")
        return self


class MemoryOperationBatch(BaseModel):
    """一次摘要产生的完整变更计划，也是原子提交单位。"""

    model_config = ConfigDict(extra="forbid")

    operations: list[MemoryOperation] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def reject_conflicting_operations(self) -> Self:
        """拒绝同批次重复修改同一条目或重复添加相同内容。"""
        targeted_ids: set[str] = set()
        added_contents: set[str] = set()

        for operation in self.operations:
            if operation.target_id:
                if operation.target_id in targeted_ids:
                    raise ValueError(f"同一批次重复操作记忆: {operation.target_id}")
                targeted_ids.add(operation.target_id)

            if operation.operation == "ADD" and operation.content:
                if operation.content in added_contents:
                    raise ValueError("同一批次不能添加重复内容")
                added_contents.add(operation.content)

        return self
