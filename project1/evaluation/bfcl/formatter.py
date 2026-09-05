"""Format AgentDecision objects as BFCL AST-evaluable Python call strings."""

from __future__ import annotations

import ast
import math
import re
from typing import Any

from project1.core.agent_protocol import AgentDecision, FinishDecision, ToolDecision


_DOTTED_IDENTIFIER = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$"
)


class BFCLFormatError(ValueError):
    """Raised when a local tool decision cannot be represented as BFCL output."""


def format_decision_for_bfcl(decision: AgentDecision) -> str:
    """Convert a local AgentDecision to a BFCL Python-list call expression."""
    if isinstance(decision, FinishDecision):
        return "[]"
    if not isinstance(decision, ToolDecision):
        raise BFCLFormatError(f"Unsupported decision type: {type(decision)!r}")

    calls = []
    for tool_call in decision.tool_calls:
        calls.append(format_tool_call(tool_call.tool_name, tool_call.parameters))
    result = "[" + ", ".join(calls) + "]"
    ast.parse(result, mode="eval")
    return result


def format_tool_call(tool_name: str, parameters: dict[str, Any]) -> str:
    """Format one tool call as ``function(arg=value)``."""
    if not _DOTTED_IDENTIFIER.fullmatch(tool_name):
        raise BFCLFormatError(f"Invalid Python function name: {tool_name}")

    arguments = ", ".join(
        f"{name}={to_python_literal(parameters[name])}"
        for name in sorted(parameters)
    )
    return f"{tool_name}({arguments})"


def to_python_literal(value: Any) -> str:
    """Return a deterministic Python literal for JSON-like BFCL arguments."""
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise BFCLFormatError(f"Non-finite float is not supported: {value!r}")
        return repr(value)
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(to_python_literal(item) for item in value) + "]"
    if isinstance(value, tuple):
        return "[" + ", ".join(to_python_literal(item) for item in value) + "]"
    if isinstance(value, dict):
        items = []
        for key in sorted(value, key=lambda item: str(item)):
            items.append(
                f"{to_python_literal(str(key))}: {to_python_literal(value[key])}"
            )
        return "{" + ", ".join(items) + "}"
    raise BFCLFormatError(f"Unsupported argument value type: {type(value)!r}")
