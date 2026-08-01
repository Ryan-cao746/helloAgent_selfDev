# 工具注册表类，作工具管理之用，提供注册、发现、执行等多种功能
from project1.tools.base import Tool
from typing import Dict, Any, List, Callable

class ToolRegistry:
    """HelloAgents工具注册表"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._functions: Dict[str, Dict[str, Any]] = {}

    def register_tool(self, tool: Tool):
        """注册Tool对象"""
        if tool.name in self._tools:
            print(f"工具'{tool.name}'已存在，将被覆盖")
        self._tools[tool.name] = tool
        print(f"工具'{tool.name}'已被注册")

    def register_function(self, name:str, description:str, func:Callable[[str], str]):
        """注册函数，作为简便方法"""
        # 注意，这里因为Callable[[参数类型列表], 返回值类型]，即func接受一个str作为参数，返回str
        if name in self._functions:
            print(f"工具'{name}'已存在，将被覆盖")
        self._functions[name] = {
            "description": description,
            "func": func
        }
        print(f"工具'{name}'已被注册")

    def get_tool(self, name:str) -> Tool:
        return self._tools[name]

    # 工具发现与管理机制
    def get_tools_description(self) -> str:
        """获得所有工具的描述字符串，合并为统一的描述字符串"""
        descriptions = []
        # 获取Tool对象描述
        for tool in self._tools.values(): #遍历字典的值序列
            descriptions.append(tool.get_full_description()) # 用我写的新函数，获取完整描述
        # 获取function对象描述
        for name, info in self._functions.items():
            descriptions.append(f"- {name}: {info['description']}") #name取键，info取值，再取info的description字段

        return "\n".join(descriptions) if descriptions else "" # 这个join的意思是用换行符连接descriptions数组中的所有记录

    #def to_openai_schema(self) -> Dict[str, Any]:
        """
            转换为openai function calling schema的格式
            ⽤于 FunctionCallAgent，使⼯具能够被 OpenAI 原⽣ function calling 使⽤
            Returns:
            符合 OpenAI function calling 标准的 schema
        """
        parameters = self.get_parameters

    def execute_tool_call(self, tool_name: str, parameters: str) -> str:
        """执行工具调用"""
        try:
            # 这里改了，全用自动参数解析
            param_dict = self._parse_tool_parameters(parameters)
            tool = self.get_tool(tool_name)
            if not tool:
                return f"未找到工具 {tool_name}"
            result = tool.run(param_dict)
            return f"工具{tool_name} 执行结果:\n {result}"
        except Exception as e:
            return f"工具执行失败:{str(e)}"

    def _parse_tool_parameters(self, parameters:str) -> dict:
        """智能解析工具参数"""
        param_dict = {} # 返回的是一个参数字典。这是很有趣的方法

        if '=' in parameters:
            # 匹配格式:key=value这种情况
            if ',' not in parameters:
                # 多参数情况，例如action=search,query=Python
                pairs = parameters.split(',') # 根据逗号划分捕获组
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1) # 根据等号划分键和值，最多划分一次
                        param_dict[key.strip()] = value.strip()
            else:
                # 单参数
                key, value = parameters.split('=', 1)  # 根据等号划分键和值，最多划分一次
                param_dict[key.strip()] = value.strip()
        else:
            print("参数格式不正确")

        return param_dict


