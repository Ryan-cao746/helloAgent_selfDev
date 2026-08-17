"""验证多轮会话装配与运行的冒烟脚本。"""

from project1.config.config import Config
from project1.factories.agent_factory import create_multi_turn_conversation
from project1.tools.built_in.example import ExampleTool
from project1.tools.registry import ToolRegistry
from project1.user_input_interface.cil_user_input import CilUserInput

if __name__ == "__main__":

    user_input_interface = CilUserInput()
    tool_registry = ToolRegistry()
    tool_registry.register_tool(ExampleTool())

    multi_asking_agent = create_multi_turn_conversation(
        user_input_interface=user_input_interface,
        config=Config(),
        tool_registry=tool_registry,
    )

    print(multi_asking_agent.run())