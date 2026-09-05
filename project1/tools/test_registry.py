"""测试工具注册、JSON/兼容参数解析和函数工具执行。"""

import unittest
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field

from project1.tools.base import (
    Tool,
    ToolCall,
    ToolExecutionPolicy,
    ToolParameter,
    ToolPolicy,
)
from project1.tools.registry import ToolRegistry


class RecordingTool(Tool):
    def __init__(self):
        super().__init__("weather", "查询城市天气")
        self.received: Dict[str, Any] = {}

    def run(self, parameters: Dict[str, Any]) -> str:
        self.received = parameters
        return "sunny"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="city",
                type="str",
                description="城市",
                required=True,
            ),
            ToolParameter(
                name="unit",
                type="str",
                description="温度单位",
                required=False,
                default="c",
            ),
        ]


class StrictArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    city: str = Field(min_length=1, max_length=20)
    count: int = Field(default=1, ge=1, le=3)


class PolicyTool(Tool):
    def __init__(self, policy: ToolPolicy, output: str = "done"):
        super().__init__(
            "policy_tool",
            "用于测试安全策略",
            policy=policy,
            arguments_model=StrictArguments,
        )
        self.output = output
        self.call_count = 0

    def run(self, parameters: Dict[str, Any]) -> str:
        self.call_count += 1
        return self.output

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="city",
                type="str",
                description="城市",
                required=True,
            ),
            ToolParameter(
                name="count",
                type="int",
                description="数量",
                required=False,
                default=1,
            ),
        ]


class FailingPolicyTool(PolicyTool):
    def run(self, parameters: Dict[str, Any]) -> str:
        self.call_count += 1
        raise RuntimeError("api_key=should-not-leak")
 

class ToolRegistryTest(unittest.TestCase):
    def setUp(self):
        self.registry = ToolRegistry()
        self.tool = RecordingTool()
        self.registry.register_tool(self.tool)

    def test_executes_structured_tool_call(self):
        result = self.registry.execute_tool_call_structured(
            ToolCall(tool_name="weather", parameters={"city": "北京"})
        )

        self.assertEqual("success", result.status)
        self.assertEqual("sunny", result.output)
        self.assertEqual({"city": "北京", "unit": "c"}, self.tool.received)

    def test_rejects_unknown_parameters(self):
        result = self.registry.execute_tool_call_structured(
            ToolCall(tool_name="weather", parameters={"city": "北京", "extra": True})
        )

        self.assertEqual("failed", result.status)
        self.assertIn("未知工具参数: extra", result.error)

    def test_returns_structured_execution_details(self):
        result = self.registry.execute_tool_call_structured(
            ToolCall(tool_name="weather", parameters={"city": "北京"})
        )

        self.assertEqual("success", result.status)
        self.assertEqual("sunny", result.output)
        self.assertIsNone(result.error)
        self.assertGreaterEqual(result.duration_ms, 0)

    def test_structured_result_keeps_tool_errors_separate(self):
        result = self.registry.execute_tool_call_structured(
            ToolCall(
                tool_name="weather",
                parameters={"city": "北京", "extra": True},
            )
        )

        self.assertEqual("failed", result.status)
        self.assertIsNone(result.output)
        self.assertIn("未知工具参数: extra", result.error)

    def test_registered_function_uses_the_same_execution_path(self):
        self.registry.register_function(
            name="echo",
            description="返回输入",
            func=lambda parameters: parameters["text"],
            parameters=[
                ToolParameter(
                    name="text",
                    type="str",
                    description="待返回文本",
                    required=True,
                )
            ],
        )

        result = self.registry.execute_tool_call_structured(
            ToolCall(tool_name="echo", parameters={"text": "hello"})
        )

        self.assertEqual("success", result.status)
        self.assertIn("hello", result.output)
        self.assertIn("返回输入", self.registry.get_tools_description())

    def test_registered_function_accepts_pydantic_arguments(self):
        self.registry.register_function(
            name="city_count",
            description="返回城市和数量",
            func=lambda parameters: (
                f"{parameters['city']}:{parameters['count']}"
            ),
            arguments_model=StrictArguments,
        )

        result = self.registry.execute_tool_call_structured(
            ToolCall(
                tool_name="city_count",
                parameters={"city": "北京", "count": 2},
            )
        )

        self.assertEqual("success", result.status)
        self.assertEqual("北京:2", result.output)
        self.assertIn("city", self.registry.get_tools_description())

    def test_denies_disallowed_tool_before_execution(self):
        tool = PolicyTool(ToolPolicy(access="write"))
        self.registry.register_tool(tool)

        result = self.registry.execute_tool_call_structured(
            ToolCall(tool_name=tool.name, parameters={"city": "北京"})
        )

        self.assertEqual("denied", result.status)
        self.assertEqual("policy_denied", result.error_code)
        self.assertEqual(0, tool.call_count)
        self.assertNotIn(tool.name, self.registry.get_tools_description())

    def test_requires_explicit_confirmation(self):
        registry = ToolRegistry(ToolExecutionPolicy(allowed_access={"write"}))
        tool = PolicyTool(ToolPolicy(
            access="write",
            requires_confirmation=True,
        ))
        registry.register_tool(tool)
        call = ToolCall(tool_name=tool.name, parameters={"city": "北京"})

        pending = registry.execute_tool_call_structured(call)
        confirmed = registry.execute_tool_call_structured(call, confirmed=True)

        self.assertEqual("confirmation_required", pending.status)
        self.assertGreaterEqual(pending.duration_ms, 0)
        self.assertEqual("success", confirmed.status)
        self.assertEqual(1, tool.call_count)

    def test_write_tools_require_confirmation_by_default(self):
        registry = ToolRegistry(ToolExecutionPolicy(allowed_access={"write"}))
        tool = PolicyTool(ToolPolicy(access="write"))
        registry.register_tool(tool)

        result = registry.execute_tool_call_structured(
            ToolCall(tool_name=tool.name, parameters={"city": "北京"})
        )

        self.assertEqual("confirmation_required", result.status)
        self.assertEqual(0, tool.call_count)

    def test_exact_tool_can_be_preapproved(self):
        registry = ToolRegistry(ToolExecutionPolicy(
            allowed_access={"write"},
            preapproved_tools={"policy_tool"},
        ))
        tool = PolicyTool(ToolPolicy(access="write"))
        registry.register_tool(tool)

        result = registry.execute_tool_call_structured(
            ToolCall(tool_name=tool.name, parameters={"city": "北京"})
        )

        self.assertEqual("success", result.status)
        self.assertEqual(1, tool.call_count)

    def test_validates_arguments_with_pydantic_model(self):
        tool = PolicyTool(ToolPolicy())
        self.registry.register_tool(tool)

        result = self.registry.execute_tool_call_structured(
            ToolCall(
                tool_name=tool.name,
                parameters={"city": "北京", "count": "2"},
            )
        )

        self.assertEqual("failed", result.status)
        self.assertEqual("invalid_parameters", result.error_code)
        self.assertEqual(0, tool.call_count)

    def test_redacts_and_truncates_tool_output(self):
        tool = PolicyTool(
            ToolPolicy(max_output_chars=24),
            output="api_key=secret-value " + "x" * 40,
        )
        self.registry.register_tool(tool)

        result = self.registry.execute_tool_call_structured(
            ToolCall(tool_name=tool.name, parameters={"city": "北京"})
        )
        observation = result.to_observation()

        self.assertEqual("success", result.status)
        self.assertTrue(result.truncated)
        self.assertEqual(24, len(result.output))
        self.assertNotIn("secret-value", result.output)
        self.assertIn("<UNTRUSTED_TOOL_OUTPUT>", observation)
        self.assertIn("[工具输出已截断]", observation)

    def test_redacts_tool_errors(self):
        tool = FailingPolicyTool(ToolPolicy())
        self.registry.register_tool(tool)

        result = self.registry.execute_tool_call_structured(
            ToolCall(tool_name=tool.name, parameters={"city": "北京"})
        )

        self.assertEqual("execution_failed", result.error_code)
        self.assertNotIn("should-not-leak", result.error)

    def test_redacts_authorization_headers(self):
        tool = PolicyTool(
            ToolPolicy(),
            output="Authorization: Bearer private-token",
        )
        self.registry.register_tool(tool)

        result = self.registry.execute_tool_call_structured(
            ToolCall(tool_name=tool.name, parameters={"city": "北京"})
        )

        self.assertEqual("Authorization: ***", result.output)


if __name__ == "__main__":
    unittest.main()
