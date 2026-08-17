"""提供用于演示工具注册、参数校验和调用流程的天气示例工具。"""

from typing import Dict, Any, List

from pydantic import BaseModel, ConfigDict, Field

from project1.tools.base import Tool, ToolParameter


class ExampleToolArguments(BaseModel):
    """示例天气工具接受的参数。"""

    model_config = ConfigDict(extra="forbid")

    city: str = Field(min_length=1, max_length=100)


class ExampleTool(Tool):
    """返回固定天气文本，用于演示工具集成而非真实天气查询。"""
    def __init__(self):
        super().__init__(
            name="example_tool",
            description="根据城市名称返回演示天气，用于验证工具调用链路。",
            arguments_model=ExampleToolArguments,
        )

    def run(self, parameters:Dict[str,Any]) -> str:
        """返回固定的演示天气结果。"""
        return "晴朗的"

    def get_parameters(self) -> List[ToolParameter]:
        """返回城市参数定义。"""
        return [
            ToolParameter(
                name="city",
                description="你想查询的城市",
                type="str",
                required=True
            )
        ]
