from typing import Dict, Any
from collections.abc import Callable

from project1.tools.example import weather_asking


class ToolExecutor:
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    def register_tool(self, name:str, description:str, func:Callable):
        """
        向工具箱中注册一个新工具
        """
        if name in self.tools:
            print(f"警告：工具'{name}'已存在，将被覆盖")
        self.tools[name] = {"description":description, "func":func}
        print(f"工具'{name}'已注册")

    def get_tool(self, name:str):
        """
        根据名称获取一个工具的执行函数
        """
        return self.tools.get(name, {}).get("func")

    def get_available_tools(self) -> str:
        """
        获取所有工具的格式化描述字符串
        """
        return "\n".join([f"-{name}:{info['description']}" for name, info in self.tools.items()])

if __name__ == "__main__":
    # 1.初始化执行器
    tool_executor = ToolExecutor()

    # 2.注册
    example_description = "一个天气查询工具。"
    tool_executor.register_tool("weather_asking", example_description, weather_asking)

    # 3.打印可用的工具
    print("\n--- 可用的工具 ---")
    print(tool_executor.get_available_tools())

    # 4.智能体的Action调用
    print("\n--- 执行Action:查找北京的天气 ---")
    tool_name = "weather_asking"
    tool_input = "北京的天气如何？"
    tool_func = tool_executor.get_tool(tool_name)

    if tool_func:
        observation = tool_func(tool_input)
        print("--- 观察(Observation) ---")
        print(observation)
    else:
        print(f"错误，未找到名为 '{tool_name}' 的工具")
