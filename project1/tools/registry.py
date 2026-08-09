# 工具注册表类，作工具管理之用，提供注册、发现、执行等多种功能
import csv
import json
from collections.abc import Callable, Mapping
from typing import Any, Dict, List, Optional, Union

from project1.tools.base import Tool, ToolCall, ToolParameter


class FunctionTool(Tool):
    """Adapt a function to the same dictionary-based contract as Tool."""

    def __init__(
            self,
            name: str,
            description: str,
            func: Callable[[Any], str],
            parameters: Optional[List[ToolParameter]] = None,
    ):
        super().__init__(name, description)
        self.func = func
        self.uses_parameter_dict = parameters is not None
        self.parameters = parameters or [
            ToolParameter(
                name="input",
                type="str",
                description="工具输入",
                required=True,
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        if self.uses_parameter_dict:
            return self.func(parameters)
        return self.func(parameters["input"])

    def get_parameters(self) -> List[ToolParameter]:
        return self.parameters

class ToolRegistry:
    """HelloAgents工具注册表"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register_tool(self, tool: Tool):
        """注册Tool对象"""
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
    ):
        """将函数适配为 Tool；旧式单字符串回调仍然受支持。"""
        self.register_tool(FunctionTool(name, description, func, parameters))

    def get_tool(self, name:str) -> Optional[Tool]:
        return self._tools.get(name)

    # 工具发现与管理机制
    def get_tools_description(self) -> str:
        """获得所有工具的描述字符串，合并为统一的描述字符串"""
        descriptions = []
        # 获取Tool对象描述
        for tool in self._tools.values(): #遍历字典的值序列
            descriptions.append(tool.get_full_description()) # 用我写的新函数，获取完整描述

        return "\n".join(descriptions) if descriptions else "" # 这个join的意思是用换行符连接descriptions数组中的所有记录

    def create_tool_call(
            self,
            tool_name: str,
            parameters: Union[str, Mapping[str, Any]],
    ) -> ToolCall:
        """把模型输出转换成统一的 ToolCall。"""
        tool_name = tool_name.strip()
        tool = self.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"未找到工具 {tool_name}")

        parsed_parameters = self._parse_tool_parameters(parameters, tool)
        validated_parameters = self._validate_tool_parameters(tool, parsed_parameters)
        return ToolCall(tool_name=tool_name, parameters=validated_parameters)

    def execute_tool_call(self, tool_call: ToolCall) -> str:
        """执行已经结构化的工具调用。"""
        try:
            tool = self.get_tool(tool_call.tool_name)
            if tool is None:
                raise ValueError(f"未找到工具 {tool_call.tool_name}")

            validated_parameters = self._validate_tool_parameters(tool, tool_call.parameters)
            result = tool.run(validated_parameters)
            return f"工具{tool_call.tool_name} 执行结果:\n {result}"
        except Exception as e:
            return f"工具执行失败:{str(e)}"

    def execute_tool_call_from_text(
            self,
            tool_name: str,
            parameters: Union[str, Mapping[str, Any]],
    ) -> str:
        """解析 ReAct 文本动作，然后通过结构化入口执行。"""
        try:
            tool_call = self.create_tool_call(tool_name, parameters)
        except Exception as e:
            return f"工具执行失败:{str(e)}"
        return self.execute_tool_call(tool_call)

    def _parse_tool_parameters(
            self,
            parameters: Union[str, Mapping[str, Any]],
            tool: Optional[Tool] = None,
    ) -> Dict[str, Any]:
        """优先解析 JSON 对象，同时兼容旧的 key=value 格式。"""
        if isinstance(parameters, Mapping):
            return dict(parameters)
        if not isinstance(parameters, str):
            raise TypeError("工具参数必须是 JSON 对象、字典或 key=value 字符串")

        parameters = parameters.strip()
        if not parameters:
            return {}

        try:
            parsed = json.loads(parameters)
        except json.JSONDecodeError:
            parsed = None

        if parsed is not None:
            if not isinstance(parsed, dict):
                raise ValueError("JSON 工具参数必须是对象")
            return parsed

        pairs = next(csv.reader([parameters], skipinitialspace=True))
        if all("=" in pair for pair in pairs):
            return {
                key.strip(): self._parse_legacy_value(value.strip())
                for key, value in (pair.split("=", 1) for pair in pairs)
            }

        declared_parameters = tool.get_parameters() if tool else []
        if len(declared_parameters) == 1:
            return {declared_parameters[0].name: parameters}
        raise ValueError("工具参数格式错误，请使用 JSON 对象")

    @staticmethod
    def _parse_legacy_value(value: str) -> Any:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    @staticmethod
    def _validate_tool_parameters(tool: Tool, parameters: Dict[str, Any]) -> Dict[str, Any]:
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


