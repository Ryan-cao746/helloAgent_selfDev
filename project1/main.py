# 这是一个示例 Python 脚本。
from project1.factories.agent_factory import create_multi_turn_conversation
from project1.tools.built_in.example import ExampleTool
from project1.tools.doubao_search import DouBaoSearchTool
from project1.user_input_interface.cil_user_input import CilUserInput
from project1.tools.registry import ToolRegistry
from project1.config.config import Config

# 按 Shift+F10 执行或将其替换为您的代码。
# 按 双击 Shift 在所有地方搜索类、文件、工具窗口、操作和设置。

# 目前仅仅做了多轮对话的Agent
def main():
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

# 访问 https://www.jetbrains.com/help/pycharm/ 获取 PyCharm 帮助
