"""组装默认组件并启动命令行多轮对话。"""

from project1.factories.agent_factory import create_multi_turn_conversation
from project1.tools.built_in.example import ExampleTool
from project1.tools.doubao_search import DouBaoSearchTool
from project1.user_input_interface.cil_user_input import CilUserInput
from project1.tools.registry import ToolRegistry
from project1.config.config import Config

def main():
    """注册内置工具，创建默认 Agent 并启动交互循环。"""
    user_input_interface = CilUserInput()
    tool_registry = ToolRegistry()
    tool_registry.register_tool(ExampleTool())
    tool_registry.register_tool(DouBaoSearchTool())

    multi_asking_agent = create_multi_turn_conversation(
        user_input_interface=user_input_interface,
        config=Config(),
        tool_registry=tool_registry,
    )

    print(multi_asking_agent.run())


# 按装订区域中的绿色按钮以运行脚本。
if __name__ == '__main__':
    main()
