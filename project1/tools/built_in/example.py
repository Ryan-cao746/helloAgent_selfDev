from typing import Dict, Any, List

from project1.tools.base import Tool, ToolParameter


class ExampleTool(Tool):
    """测试工具调用和注册机制、agent相关配置的示例工具"""
    def __init__(self):
        super().__init__(
            name="example_tool",
            description="""
            测试工具调用和注册机制、agent相关配置的示例工具，目前的功能是获取某城市的天气。
            参数:
            city: str
            """
        )

    def run(self, parameters:Dict[str,Any]) -> str:
        return "晴朗的"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="city",
                description="你想查询的城市",
                type="str",
                required=True
            )
        ]