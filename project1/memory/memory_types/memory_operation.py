from typing import Literal, Self

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class MemoryOperation(BaseModel):
    """一条经过运行时校验的记忆变更指令。"""

    model_config = ConfigDict(extra="forbid")   # 禁止数据类接受未定义的字段

    operation: Literal["ADD", "UPDATE", "DELETE", "NOOP"]
    target_id: str | None = None
    content: str | None = Field(
        default=None,
        validation_alias=AliasChoices("content", "summary"),    # 于处理数据来源多样、字段命名不统一的场景，让数据模型更加灵活和健壮
    )
    reasoning: str | None = None

    #为单个字段添加校验逻辑。
    @field_validator("target_id", "content", mode="before") # 转换前。在 Pydantic 做任何内置转换和校验之前。格式处理、数据清洗
    @classmethod
    def normalize_empty_string(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    # 用于需要多个字段联动校验的场景
    @model_validator(mode="after")  #在 Pydantic 完成了内置类型转换和基本约束校验（如 Field(gt=0)）之后执行。
    def validate_required_fields(self) -> Self:
        """校验相关字段"""
        if self.operation in {"ADD", "UPDATE"} and self.content is None:
            raise ValueError(f"{self.operation} 操作必须提供 content")
        if self.operation in {"UPDATE", "DELETE"} and self.target_id is None:
            raise ValueError(f"{self.operation} 操作必须提供 target_id")
        return self


class MemoryOperationBatch(BaseModel):
    """一次摘要产生的完整变更计划，也是原子提交单位。"""

    model_config = ConfigDict(extra="forbid")   # 禁止数据类接受未定义的字段

    operations: list[MemoryOperation] = Field(default_factory=list, max_length=100)

    # 自定义特定阶段的校验逻辑
    @model_validator(mode="after")  # 在 Pydantic 完成了内置类型转换和基本约束校验后处理
    def reject_conflicting_operations(self) -> Self:
        """校验，排除存在冲突指令的情况"""
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
