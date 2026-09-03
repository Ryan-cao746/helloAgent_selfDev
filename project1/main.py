"""组装默认组件并启动命令行多轮对话。"""
from pathlib import Path
from typing import cast, FrozenSet, Literal
from project1.factories.agent_factory import create_multi_turn_conversation
from project1.mcp_integration.mcp_server import MCPServer
from project1.mcp_integration.mcp_test import create_example_server
from project1.mcp_integration.sync_bridge import SyncMCPClientBridge
from project1.skill_system import SkillRegistry, SkillRuntime
from project1.tools.base import ToolExecutionPolicy, ToolAccess
from project1.tools.built_in.example import ExampleTool
from project1.tools.built_in.extract_skills import ExtractSkills
from project1.tools.built_in.file_browser import FileBrowser
from project1.tools.built_in.mcp_wrapper_tool import register_mcp_tools
from project1.tools.built_in.modify_file import ModifyFile
from project1.tools.built_in.skill_tools import ListSkills, LoadSkill, RunSkillScript
from project1.tools.doubao_search import DouBaoSearchTool
from project1.user_input_interface.cil_user_input import CilUserInput
from project1.tools.registry import ToolRegistry
from project1.config.config import Config
from project1.config.file_config import load_file_config

def main():
    """注册内置工具，创建默认 Agent 并启动交互循环。"""
    # 工具权限
    permissions = cast(
        FrozenSet[Literal["read_only", "network", "write", "destructive"]],
        frozenset(["read_only", "write", "network"])
    ) # 类型检查强制通过校验

    # mcp服务器
    server = create_example_server()
    # mcp同步桥
    bridge = SyncMCPClientBridge(server.mcp)

    # 文件存储配置，包括本地文件读写和skills文件位置、skills运行时等
    file_config = load_file_config()
    workspace_root = file_config.resolve_workspace_root()
    project_root = Path(__file__).resolve().parent
    repo_root = project_root.parent
    skill_registry = SkillRegistry.for_project(
        repo_root=repo_root,
        project_root=project_root,
    )
    skill_runtime = SkillRuntime(skill_registry)

    user_input_interface = CilUserInput()
    tool_registry = ToolRegistry(
        execution_policy=ToolExecutionPolicy(
            allowed_access=permissions
            )
        )

    # 工具注册
    tool_registry.register_tool(ExampleTool())
    tool_registry.register_tool(DouBaoSearchTool())
    tool_registry.register_tool(ExtractSkills())
    tool_registry.register_tool(ListSkills(skill_runtime))
    tool_registry.register_tool(LoadSkill(skill_runtime))
    tool_registry.register_tool(RunSkillScript(skill_runtime))
    tool_registry.register_tool(FileBrowser(workspace_root=workspace_root))
    tool_registry.register_tool(ModifyFile(workspace_root=workspace_root))
    # 注册全部mcp工具
    register_mcp_tools(tool_registry, bridge, prefix="demo")

    # 组装
    multi_asking_agent = create_multi_turn_conversation(
        user_input_interface=user_input_interface,
        config=Config(debug=False, max_tool_calls=6),
        tool_registry=tool_registry,
        skill_runtime=skill_runtime,
    )

    print(multi_asking_agent.run())


# 按装订区域中的绿色按钮以运行脚本。
if __name__ == '__main__':
    main()
