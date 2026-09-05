"""Prompt rendering for lightweight BFCL generation."""

from __future__ import annotations

import json
from typing import Any

from project1.evaluation.bfcl.schemas import BFCLCase, BFCLFunctionSpec


BFCL_DECISION_PROMPT = """你正在参加 Berkeley Function Calling Leaderboard 的单轮函数调用评估。

你只能根据下面给出的函数文档决定是否调用函数；不要假设有其他工具存在，也不要执行工具。
你每次只能返回一个合法 JSON 对象，不要使用 Markdown 代码块，不要输出 JSON 之外的文字。

需要调用函数时返回：
{{
  "kind": "tool",
  "reasoning_summary": "简短说明为什么需要这些函数",
  "tool_calls": [
    {{
      "tool_name": "函数名称",
      "parameters": {{"参数名称": "参数值"}}
    }}
  ]
}}

如果用户问题与所有函数都无关，或不应调用任何函数，返回：
{{
  "kind": "finish",
  "reasoning_summary": "简短说明为什么不调用函数",
  "final_answer": "NO_FUNCTION_CALL"
}}

当用户需要多个函数调用时，把所有调用按自然执行顺序放入 tool_calls 数组。
不要输出完整思考过程。

可用函数：
{function_descriptions}

用户消息：
{question}
"""


def render_bfcl_prompt(case: BFCLCase) -> str:
    """Render one BFCL case into the current AgentDecision JSON protocol."""
    return BFCL_DECISION_PROMPT.format(
        function_descriptions="\n\n".join(
            render_function_description(function) for function in case.functions
        ),
        question=case.conversation_text(),
    )


def render_function_description(function: BFCLFunctionSpec) -> str:
    """Render a BFCL function schema in the local tool-description style."""
    parameter_lines = []
    required = function.required_parameter_names
    for name, schema in function.parameter_properties.items():
        if not isinstance(schema, dict):
            schema = {"description": str(schema)}
        parameter_lines.append(_render_parameter(name, schema, name in required))

    parameters_text = "\n".join(parameter_lines) if parameter_lines else "        None"
    return f"""## 工具信息
name: {function.name}
description: {function.description}
access: read_only
requires_confirmation: False
## 参数信息
{parameters_text}"""


def _render_parameter(name: str, schema: dict[str, Any], required: bool) -> str:
    details = {
        "name": name,
        "type": schema.get("type", "any"),
        "description": schema.get("description", ""),
        "required": required,
    }
    if "default" in schema:
        details["default"] = schema["default"]
    if "enum" in schema:
        details["enum"] = schema["enum"]
    return json.dumps(details, ensure_ascii=False, sort_keys=True)
