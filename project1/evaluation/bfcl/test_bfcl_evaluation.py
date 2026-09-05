"""Tests for the lightweight BFCL evaluation adapter."""

import json
import tempfile
import unittest
from pathlib import Path

from project1.core.agent_protocol import FinishDecision, ToolDecision
from project1.core.exceptions import LLMClientError
from project1.core.message import Message
from project1.evaluation.bfcl.formatter import (
    BFCLFormatError,
    format_decision_for_bfcl,
)
from project1.evaluation.bfcl.loader import BFCLDataError, load_bfcl_cases
from project1.evaluation.bfcl.prompt import render_bfcl_prompt
from project1.evaluation.bfcl.runner import (
    BFCLRunner,
    official_evaluate_command,
    validate_result_file,
)
from project1.tools.base import ToolCall


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def sample_case(case_id: str = "simple_python_0") -> dict:
    return {
        "id": case_id,
        "question": [[{
            "role": "user",
            "content": "Find the area of a triangle with base 10 and height 5.",
        }]],
        "function": [{
            "name": "calculate_triangle_area",
            "description": "Calculate triangle area.",
            "parameters": {
                "type": "dict",
                "properties": {
                    "base": {
                        "type": "integer",
                        "description": "Triangle base.",
                    },
                    "height": {
                        "type": "integer",
                        "description": "Triangle height.",
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit name.",
                        "default": "units",
                    },
                },
                "required": ["base", "height"],
            },
        }],
    }


class BFCLLoaderTest(unittest.TestCase):
    def test_loads_valid_jsonl(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "BFCL_v4_simple_python.json"
            write_jsonl(dataset, [sample_case()])

            cases = load_bfcl_cases(dataset)

            self.assertEqual(1, len(cases))
            self.assertEqual("simple_python_0", cases[0].id)
            self.assertEqual("calculate_triangle_area", cases[0].functions[0].name)

    def test_rejects_missing_required_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "broken.json"
            write_jsonl(dataset, [{"id": "missing_function", "question": "hi"}])

            with self.assertRaises(BFCLDataError):
                load_bfcl_cases(dataset)

    def test_loads_empty_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "empty.json"
            dataset.write_text("", encoding="utf-8")

            self.assertEqual([], load_bfcl_cases(dataset))

    def test_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "broken.json"
            dataset.write_text("{bad json}\n", encoding="utf-8")

            with self.assertRaises(BFCLDataError):
                load_bfcl_cases(dataset)


class BFCLPromptTest(unittest.TestCase):
    def test_renders_function_schema_into_local_protocol_prompt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "BFCL_v4_simple_python.json"
            write_jsonl(dataset, [sample_case()])
            case = load_bfcl_cases(dataset)[0]

            prompt = render_bfcl_prompt(case)

            self.assertIn("calculate_triangle_area", prompt)
            self.assertIn('"name": "base"', prompt)
            self.assertIn('"required": true', prompt)
            self.assertIn('"kind": "tool"', prompt)
            self.assertIn("Find the area", prompt)


class BFCLFormatterTest(unittest.TestCase):
    def test_formats_single_call(self):
        decision = ToolDecision(
            kind="tool",
            tool_calls=[ToolCall(
                tool_name="calculate_triangle_area",
                parameters={"height": 5, "base": 10},
            )],
        )

        self.assertEqual(
            "[calculate_triangle_area(base=10, height=5)]",
            format_decision_for_bfcl(decision),
        )

    def test_formats_multiple_calls_and_nested_parameters(self):
        decision = ToolDecision(
            kind="tool",
            tool_calls=[
                ToolCall(
                    tool_name="search_city",
                    parameters={
                        "filters": {"country": "CN", "active": True},
                        "names": ["北京", "上海"],
                    },
                ),
                ToolCall(
                    tool_name="rank",
                    parameters={"limit": None},
                ),
            ],
        )

        self.assertEqual(
            "[search_city(filters={'active': True, 'country': 'CN'}, "
            "names=['北京', '上海']), rank(limit=None)]",
            format_decision_for_bfcl(decision),
        )

    def test_finish_decision_formats_as_empty_call_list(self):
        decision = FinishDecision(kind="finish", final_answer="NO_FUNCTION_CALL")

        self.assertEqual("[]", format_decision_for_bfcl(decision))

    def test_rejects_invalid_function_name(self):
        decision = ToolDecision(
            kind="tool",
            tool_calls=[ToolCall(
                tool_name="bad-name",
                parameters={},
            )],
        )

        with self.assertRaises(BFCLFormatError):
            format_decision_for_bfcl(decision)


class FakeLLM:
    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.messages: list[list[Message]] = []

    def decide(self, messages, **kwargs):
        self.messages.append(list(messages))
        decision = self.decisions.pop(0)
        if isinstance(decision, Exception):
            raise decision
        return decision


class BFCLRunnerTest(unittest.TestCase):
    def test_runner_writes_result_trace_and_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "BFCL_v4_simple_python.json"
            write_jsonl(dataset, [sample_case()])
            cases = load_bfcl_cases(dataset)
            llm = FakeLLM([
                ToolDecision(
                    kind="tool",
                    tool_calls=[ToolCall(
                        tool_name="calculate_triangle_area",
                        parameters={"base": 10, "height": 5},
                    )],
                )
            ])
            runner = BFCLRunner(llm)

            summary = runner.run_cases(
                cases,
                dataset_name=dataset.stem,
                category="simple_python",
                model_name="helloagent_prompt",
                output_root=root / ".bfcl_runs",
            )

            self.assertEqual(1, summary.total)
            self.assertEqual(1, summary.succeeded)
            result_path = Path(summary.output_file)
            valid, errors = validate_result_file(result_path)
            self.assertTrue(valid, errors)
            result_rows = [
                json.loads(line)
                for line in result_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual("simple_python_0", result_rows[0]["id"])
            self.assertEqual(
                "[calculate_triangle_area(base=10, height=5)]",
                result_rows[0]["result"],
            )
            self.assertTrue(Path(summary.trace_file).exists())

    def test_runner_continues_after_failed_case_and_honors_limit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "BFCL_v4_simple_python.json"
            write_jsonl(dataset, [
                sample_case("simple_python_0"),
                sample_case("simple_python_1"),
                sample_case("simple_python_2"),
            ])
            cases = load_bfcl_cases(dataset, limit=2)
            llm = FakeLLM([
                LLMClientError("bad response api_key=secret-value"),
                FinishDecision(kind="finish", final_answer="NO_FUNCTION_CALL"),
            ])
            runner = BFCLRunner(llm)

            summary = runner.run_cases(
                cases,
                dataset_name=dataset.stem,
                category="simple_python",
                model_name="helloagent_prompt",
                output_root=root / ".bfcl_runs",
            )

            self.assertEqual(2, summary.total)
            self.assertEqual(1, summary.succeeded)
            trace_rows = [
                json.loads(line)
                for line in Path(summary.trace_file).read_text(
                    encoding="utf-8"
                ).splitlines()
            ]
            self.assertEqual("failed", trace_rows[0]["status"])
            self.assertNotIn("secret-value", trace_rows[0]["error"])
            self.assertEqual("success", trace_rows[1]["status"])

    def test_validate_rejects_non_list_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result_path = Path(temp_dir) / "result.json"
            write_jsonl(result_path, [{"id": "x", "result": "foo()"}])

            valid, errors = validate_result_file(result_path)

            self.assertFalse(valid)
            self.assertIn("Python list expression", errors[0])

    def test_official_command_points_to_output_root(self):
        command = official_evaluate_command(
            model_name="helloagent_prompt",
            category="simple_python",
            output_root=".bfcl_runs",
        )

        self.assertIn("BFCL_PROJECT_ROOT", command)
        self.assertIn("--partial-eval", command)
        self.assertIn("simple_python", command)


if __name__ == "__main__":
    unittest.main()
