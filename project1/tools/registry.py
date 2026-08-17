"""注册、发现并按安全策略执行工具。"""

from collections.abc import Callable
from time import perf_counter
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ValidationError

from project1.tools.base import (
    Tool,
    ToolCall,
    ToolExecutionPolicy,
    ToolParameter,
    ToolPolicy,
    ToolResult,
)
from project1.tools.security import limit_text, redact_sensitive_text


class FunctionTool(Tool):
    """将普通函数适配为与 ``Tool`` 一致的字典参数接口。"""

    def __init__(
            self,
            name: str,
            description: str,
            func: Callable[[Any], str],
            parameters: Optional[List[ToolParameter]] = None,
            policy: ToolPolicy | None = None,
            arguments_model: type[BaseModel] | None = None,
    ):
        super().__init__(
            name,
            description,
            policy=policy,
            arguments_model=arguments_model,
        )
        self.func = func
        self.uses_parameter_dict = (
            parameters is not None or arguments_model is not None
        )
        if parameters is not None:
            self.parameters = parameters
        elif arguments_model is not None:
            schema = arguments_model.model_json_schema()
            required = set(schema.get("required", []))
            self.parameters = [
                ToolParameter(
                    name=name,
                    type=str(field_schema.get("type", "any")),
                    description=str(field_schema.get("description", "")),
                    required=name in required,
                    default=field_schema.get("default"),
                )
                for name, field_schema in schema.get("properties", {}).items()
            ]
        else:
            self.parameters = [
                ToolParameter(
                    name="input",
                    type="str",
                    description="工具输入",
                    required=True,
                )
            ]

    def run(self, parameters: Dict[str, Any]) -> str:
        """按函数声明方式传入参数字典或单个 ``input`` 值。"""
        if self.uses_parameter_dict:
            return self.func(parameters)
        return self.func(parameters["input"])

    def get_parameters(self) -> List[ToolParameter]:
        """返回显式参数或由 Pydantic 模型推导出的参数定义。"""
        return self.parameters

class ToolRegistry:
    """管理工具，并统一执行权限检查、参数校验和结果脱敏。"""

    def __init__(
            self,
            execution_policy: ToolExecutionPolicy | None = None,
    ):
        self._tools: Dict[str, Tool] = {}
        self.execution_policy = execution_policy or ToolExecutionPolicy()

    def register_tool(self, tool: Tool):
        """按名称注册工具；同名工具会被新实例覆盖。"""
        if tool.name in self._tools:
            print(f"工具'{tool.name}'已存在，将被覆盖")
        self._tools[tool.name] = tool
        print(f"工具'{tool.name}'已被注册")

    def register_function(
            self,
            name: str,
            description: str,
            func: Callable[[Any], str],
            parameters: Optional[List[ToolParameter]] = None,
            policy: ToolPolicy | None = None,
            arguments_model: type[BaseModel] | None = None,
    ):
        """将函数注册为工具，同时兼容旧式单字符串回调。"""
        self.register_tool(FunctionTool(
            name,
            description,
            func,
            parameters,
            policy,
            arguments_model,
        ))

    def get_tool(self, name:str) -> Optional[Tool]:
        """按名称返回已注册工具；不存在时返回 ``None``。"""
        return self._tools.get(name)

    def get_tools_description(self) -> str:
        """返回当前执行策略允许暴露给模型的工具说明。"""
        descriptions = []
        for tool in self._tools.values():
            if tool.policy.access not in self.execution_policy.allowed_access:
                continue
            descriptions.append(tool.get_full_description())

        return "\n".join(descriptions) if descriptions else ""

    def execute_tool_call_structured(
            self,
            tool_call: ToolCall,
            confirmed: bool = False,
    ) -> ToolResult:
        """执行完整安全管线并返回可观测的结构化结果。"""
        started = perf_counter()
        tool = self.get_tool(tool_call.tool_name)
        if tool is None:
            return self._failure_result(
                tool_call.tool_name,
                status="failed",
                error_code="tool_not_found",
                error=f"未找到工具 {tool_call.tool_name}",
                started=started,
            )

        if tool.policy.access not in self.execution_policy.allowed_access:
            return self._failure_result(
                tool_call.tool_name,
                status="denied",
                error_code="policy_denied",
                error=f"安全策略不允许执行 {tool.policy.access} 类型工具",
                started=started,
            )

        needs_confirmation = (
            tool.policy.confirmation_required
            and tool.name not in self.execution_policy.preapproved_tools
        )   # 判断相关工具是否需要用户确认
        if needs_confirmation and not confirmed:
            return self._failure_result(
                tool_call.tool_name,
                status="confirmation_required",
                error_code="confirmation_required",
                error="该工具需要用户确认后才能执行",
                started=started,
            )

        try:
            validated_parameters = self._validate_tool_parameters(tool, tool_call.parameters)
        except Exception as error:
            return self._failure_result(
                tool_call.tool_name,
                status="failed",
                error_code="invalid_parameters",
                error=str(error),
                started=started,
            )

        try:
            result = tool.run(validated_parameters)
        except Exception as error:
            return self._failure_result(
                tool_call.tool_name,
                status="failed",
                error_code="execution_failed",
                error=str(error),
                started=started,
            )

        safe_output = redact_sensitive_text(str(result))
        bounded_output, truncated, original_length = limit_text(
            safe_output,
            tool.policy.max_output_chars,
        )
        return ToolResult(
            tool_name=tool_call.tool_name,
            status="success",
            output=bounded_output,
            duration_ms=(perf_counter() - started) * 1000,
            truncated=truncated,
            original_length=original_length,
        )

    @staticmethod
    def _validate_tool_parameters(tool: Tool, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if tool.arguments_model is not None:
            try:
                arguments = tool.arguments_model.model_validate(parameters)
            except ValidationError as error:
                details = error.errors(include_url=False, include_input=False)
                raise ValueError(f"工具参数校验失败: {details}") from error
            return arguments.model_dump(mode="python")

        declared = {parameter.name: parameter for parameter in tool.get_parameters()}
        unknown = set(parameters) - set(declared)
        if unknown:
            raise ValueError(f"未知工具参数: {', '.join(sorted(unknown))}")

        validated = dict(parameters)
        for name, parameter in declared.items():
            if name not in validated:
                if parameter.required:
                    raise ValueError(f"缺少必填工具参数: {name}")
                validated[name] = parameter.default
        return validated

    @staticmethod
    def _failure_result(
            tool_name: str,
            status: str,
            error_code: str,
            error: str,
            started: float,
    ) -> ToolResult:
        return ToolResult(
            tool_name=tool_name,
            status=status,
            error_code=error_code,
            error=redact_sensitive_text(error),
            duration_ms=(perf_counter() - started) * 1000,
        )

