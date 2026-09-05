"""测试 MCP tools 的同步注册适配层。"""

import unittest

try:
    from project1.mcp_integration.mcp_server import MCPServer
    from project1.mcp_integration.sync_bridge import SyncMCPClientBridge
    from project1.tools.base import ToolCall, ToolPolicy
    from project1.tools.built_in.mcp_wrapper_tool import register_mcp_tools
    from project1.tools.registry import ToolRegistry

    MCP_IMPORT_ERROR = None
except ImportError as error:
    MCP_IMPORT_ERROR = error


def calculator(expression: str) -> str:
    allowed_chars = set("0123456789+-*/() .")
    if not all(char in allowed_chars for char in expression):
        return "Error: Invalid characters in expression"
    return f"Result: {eval(expression)}"


def greet(name: str) -> str:
    return f"Hello, {name}!"


def status_resource() -> str:
    return "server status: ok"


def draft_prompt(topic: str) -> str:
    return f"Draft about {topic}"


@unittest.skipIf(MCP_IMPORT_ERROR is not None, f"MCP 不可用: {MCP_IMPORT_ERROR}")
class SyncMCPToolsTest(unittest.TestCase):
    def setUp(self):
        self.server = MCPServer(
            name="example_server",
            description="测试 MCP server",
        )
        self.server.add_tool(
            calculator,
            name="calculator",
            description="Calculate a math expression",
        )
        self.server.add_tool(
            greet,
            name="greet",
            description="Generate a friendly greeting",
        )
        self.server.add_resource(
            status_resource,
            uri="status://server",
            name="status",
            description="Server status",
        )
        self.server.add_prompt(
            draft_prompt,
            name="draft",
            description="Draft a topic",
        )
        self.bridge = SyncMCPClientBridge(self.server.mcp)
        self.registry = ToolRegistry()

    def tearDown(self):
        self.bridge.close()

    def test_registers_mcp_tools_into_registry(self):
        registered = register_mcp_tools(self.registry, self.bridge)

        self.assertEqual(["calculator", "greet"], registered)
        description = self.registry.get_tools_description()
        self.assertIn("calculator", description)
        self.assertIn("Calculate a math expression", description)
        self.assertIn("expression", description)
        self.assertIn("greet", description)
        self.assertIn("name", description)

    def test_executes_wrapped_mcp_tool_through_registry(self):
        register_mcp_tools(self.registry, self.bridge)

        result = self.registry.execute_tool_call_structured(
            ToolCall(
                tool_name="calculator",
                parameters={"expression": "2 + 3 * 4"},
            )
        )

        self.assertEqual("success", result.status)
        self.assertEqual("Result: 14", result.output)

    def test_registry_validates_missing_and_unknown_parameters(self):
        register_mcp_tools(self.registry, self.bridge)

        missing = self.registry.execute_tool_call_structured(
            ToolCall(tool_name="greet", parameters={})
        )
        unknown = self.registry.execute_tool_call_structured(
            ToolCall(tool_name="greet", parameters={"name": "Ada", "x": 1})
        )

        self.assertEqual("invalid_parameters", missing.error_code)
        self.assertIn("缺少必填工具参数: name", missing.error)
        self.assertEqual("invalid_parameters", unknown.error_code)
        self.assertIn("未知工具参数: x", unknown.error)

    def test_prefix_avoids_name_collisions(self):
        registered = register_mcp_tools(
            self.registry,
            self.bridge,
            prefix="demo",
        )

        self.assertEqual(["demo_calculator", "demo_greet"], registered)
        result = self.registry.execute_tool_call_structured(
            ToolCall(
                tool_name="demo_greet",
                parameters={"name": "Ada"},
            )
        )

        self.assertEqual("success", result.status)
        self.assertEqual("Hello, Ada!", result.output)

    def test_custom_policy_is_applied_to_wrapped_tools(self):
        register_mcp_tools(
            self.registry,
            self.bridge,
            policy=ToolPolicy(access="write"),
        )

        result = self.registry.execute_tool_call_structured(
            ToolCall(
                tool_name="greet",
                parameters={"name": "Ada"},
            )
        )

        self.assertEqual("denied", result.status)
        self.assertEqual("policy_denied", result.error_code)

    def test_close_stops_bridge(self):
        register_mcp_tools(self.registry, self.bridge)

        self.bridge.close()

        with self.assertRaises(RuntimeError):
            self.bridge.list_tools()

    def test_bridge_exposes_resources_and_prompts(self):
        resources = self.bridge.list_resources()
        resource = self.bridge.read_resource("status://server")
        prompts = self.bridge.list_prompts()
        prompt = self.bridge.get_prompt("draft", {"topic": "skills"})

        self.assertEqual("status://server", str(resources[0]["uri"]))
        self.assertEqual("server status: ok", resource)
        self.assertEqual("draft", prompts[0]["name"])
        self.assertEqual("user", str(prompt[0]["role"]))
        self.assertIn("Draft about skills", prompt[0]["content"])


if __name__ == "__main__":
    unittest.main()
