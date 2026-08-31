"""MCP tool 到项目同步 ``Tool`` 接口的适配器。
这个适配器实际上是将MCP工具的相关描述导入到agent适配的tool中，而运行上还是通过后台线程和事件循环异步执行
"""

from __future__ import annotations

import json
from typing import Any

from project1.mcp.sync_bridge import SyncMCPClientBridge
from project1.tools.base import Tool, ToolParameter, ToolPolicy
from project1.tools.registry import ToolRegistry


class MCPWrappedTool(Tool):
    """将 MCP server 中的单个 tool 包装为可注册的同步 Tool。"""

    def __init__(
            self,
            name: str,
            description: str,
            input_schema: Any,
            bridge: SyncMCPClientBridge,
            mcp_tool_name: str,
            policy: ToolPolicy | None = None,
    ):
        super().__init__(
            name=name,
            description=description,
            policy=policy or ToolPolicy(),
        )
        self.input_schema = _normalize_schema(input_schema)
        self.bridge = bridge
        self.mcp_tool_name = mcp_tool_name
        self.parameters = _schema_to_parameters(self.input_schema)

    def run(self, parameters: dict[str, Any]) -> str:
        """通过同步桥调用异步 MCP tool。"""
        result = self.bridge.call_tool(self.mcp_tool_name, parameters)
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False, default=str)

    def get_parameters(self) -> list[ToolParameter]:
        """返回由 MCP input schema 转换出的参数定义。"""
        return self.parameters


def register_mcp_tools(
        registry: ToolRegistry,
        bridge: SyncMCPClientBridge,
        prefix: str | None = None,
        policy: ToolPolicy | None = None,
) -> list[str]:
    """列出 MCP tools，将它们包装成普通 Tool 并注册到 registry。"""
    bridge.start()
    registered_names: list[str] = []

    for tool_info in bridge.list_tools():
        mcp_tool_name = str(tool_info["name"])
        registered_name = (
            f"{prefix}_{mcp_tool_name}" if prefix else mcp_tool_name
        )
        registry.register_tool(
            MCPWrappedTool(
                name=registered_name,
                description=str(tool_info.get("description", "")),
                input_schema=tool_info.get("input_schema", {}),
                bridge=bridge,
                mcp_tool_name=mcp_tool_name,
                policy=policy,
            )
        )
        registered_names.append(registered_name)

    return registered_names


def _schema_to_parameters(input_schema: dict[str, Any]) -> list[ToolParameter]:
    """将MCP Schema转换为ToolParameters"""
    properties = input_schema.get("properties", {})
    if not isinstance(properties, dict):
        return []

    required = input_schema.get("required", [])
    required_names = set(required) if isinstance(required, list) else set()
    parameters: list[ToolParameter] = []

    for name, property_schema in properties.items():
        field_schema = (
            property_schema if isinstance(property_schema, dict) else {}
        )
        parameters.append(
            ToolParameter(
                name=str(name),
                type=_schema_type(field_schema),
                description=_schema_description(field_schema),
                required=name in required_names,
                default=field_schema.get("default"),
            )
        )

    return parameters


def _normalize_schema(input_schema: Any) -> dict[str, Any]:
    if isinstance(input_schema, dict):
        return input_schema
    if hasattr(input_schema, "model_dump"):
        dumped = input_schema.model_dump(mode="python")
        return dumped if isinstance(dumped, dict) else {}
    if hasattr(input_schema, "dict"):
        dumped = input_schema.dict()
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _schema_type(field_schema: dict[str, Any]) -> str:
    schema_type = field_schema.get("type")
    if isinstance(schema_type, str):
        return schema_type
    if isinstance(schema_type, list):
        return "|".join(str(item) for item in schema_type)

    for variant_key in ("anyOf", "oneOf"):
        variants = field_schema.get(variant_key)
        if isinstance(variants, list):
            variant_types = [
                _schema_type(variant)
                for variant in variants
                if isinstance(variant, dict)
            ]
            variant_types = [item for item in variant_types if item != "any"]
            if variant_types:
                return "|".join(variant_types)

    if "properties" in field_schema:
        return "object"
    if "items" in field_schema:
        return "array"
    return "any"


def _schema_description(field_schema: dict[str, Any]) -> str:
    description = field_schema.get("description", "")
    if not isinstance(description, str):
        description = str(description)

    enum_values = field_schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        enum_text = ", ".join(str(value) for value in enum_values)
        if description:
            return f"{description} 可选值: {enum_text}"
        return f"可选值: {enum_text}"

    return description
