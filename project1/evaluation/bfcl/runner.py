"""Batch runner for lightweight BFCL generation."""

from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Iterable

from project1.core.exceptions import LLMClientError
from project1.core.llm_client import HelloAgentsLLM
from project1.core.message import Message
from project1.evaluation.bfcl.formatter import (
    BFCLFormatError,
    format_decision_for_bfcl,
)
from project1.evaluation.bfcl.loader import load_bfcl_cases
from project1.evaluation.bfcl.prompt import render_bfcl_prompt
from project1.evaluation.bfcl.schemas import (
    BFCLCase,
    BFCLGenerationRecord,
    BFCLRunSummary,
)
from project1.tools.security import redact_sensitive_text


DEFAULT_OUTPUT_ROOT = ".bfcl_runs"


class BFCLRunner:
    """Generate BFCL result files without executing real project tools."""

    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client

    def run_cases(
        self,
        cases: Iterable[BFCLCase],
        *,
        dataset_name: str,
        category: str,
        model_name: str,
        output_root: str | Path = DEFAULT_OUTPUT_ROOT,
        temperature: float = 0,
        decision_retries: int = 1,
    ) -> BFCLRunSummary:
        """Run one independent model decision for each BFCL case."""
        output_root = Path(output_root)
        started_at = datetime.now(timezone.utc)
        started = perf_counter()
        result_file, trace_file, summary_file = build_output_paths(
            output_root=output_root,
            model_name=model_name,
            dataset_name=dataset_name,
        )
        for path in (result_file.parent, trace_file.parent, summary_file.parent):
            path.mkdir(parents=True, exist_ok=True)

        records = [
            self._run_single_case(
                case,
                temperature=temperature,
                decision_retries=decision_retries,
            )
            for case in cases
        ]

        _write_jsonl(
            result_file,
            [record.to_official_record() for record in records],
        )
        _write_jsonl(
            trace_file,
            [record.model_dump(mode="json", exclude_none=True) for record in records],
        )

        succeeded = sum(record.status == "success" for record in records)
        summary = BFCLRunSummary(
            model_name=model_name,
            dataset=dataset_name,
            category=category,
            total=len(records),
            succeeded=succeeded,
            failed=len(records) - succeeded,
            output_file=str(result_file),
            trace_file=str(trace_file),
            summary_file=str(summary_file),
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            duration_ms=(perf_counter() - started) * 1000,
        )
        summary_file.write_text(
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return summary

    def _run_single_case(
        self,
        case: BFCLCase,
        *,
        temperature: float,
        decision_retries: int,
    ) -> BFCLGenerationRecord:
        started = perf_counter()
        try:
            decision = self.llm_client.decide(
                [Message(content=render_bfcl_prompt(case), role="user")],
                temperature=temperature,
                max_retries=decision_retries,
            )
            result = format_decision_for_bfcl(decision)
            return BFCLGenerationRecord(
                id=case.id,
                result=result,
                status="success",
                latency_ms=(perf_counter() - started) * 1000,
                raw_decision=decision.model_dump(mode="json"),
            )
        except (LLMClientError, BFCLFormatError, Exception) as error:
            return BFCLGenerationRecord(
                id=case.id,
                result="[]",
                status="failed",
                latency_ms=(perf_counter() - started) * 1000,
                error=redact_sensitive_text(str(error)),
            )


def run_bfcl_file(
    dataset_path: str | Path,
    *,
    category: str,
    model_name: str,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    limit: int | None = None,
    temperature: float = 0,
    decision_retries: int = 1,
    llm_client: HelloAgentsLLM | None = None,
) -> BFCLRunSummary:
    """Convenience wrapper that loads cases and runs the default LLM client."""
    path = Path(dataset_path)
    cases = load_bfcl_cases(path, limit=limit)
    runner = BFCLRunner(llm_client or HelloAgentsLLM())
    return runner.run_cases(
        cases,
        dataset_name=path.stem,
        category=category,
        model_name=model_name,
        output_root=output_root,
        temperature=temperature,
        decision_retries=decision_retries,
    )


def build_output_paths(
    *,
    output_root: str | Path,
    model_name: str,
    dataset_name: str,
) -> tuple[Path, Path, Path]:
    """Return official result, trace, and summary output paths."""
    root = Path(output_root)
    safe_model_name = model_name.replace("/", "_")
    file_stem = dataset_name[:-7] if dataset_name.endswith("_result") else dataset_name
    return (
        root / "result" / safe_model_name / f"{file_stem}_result.json",
        root / "traces" / safe_model_name / f"{file_stem}_trace.jsonl",
        root / "summaries" / safe_model_name / f"{file_stem}_summary.json",
    )


def validate_result_file(results_path: str | Path) -> tuple[bool, list[str]]:
    """Validate the lightweight result JSONL shape and Python AST syntax."""
    path = Path(results_path)
    errors: list[str] = []
    if not path.exists():
        return False, [f"results file does not exist: {path}"]

    try:
        rows = _read_result_rows(path)
    except ValueError as error:
        return False, [str(error)]

    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append(f"line {index}: expected object")
            continue
        if not isinstance(row.get("id"), str) or not row["id"]:
            errors.append(f"line {index}: id must be a non-empty string")
        result = row.get("result")
        if not isinstance(result, str):
            errors.append(f"line {index}: result must be a string")
            continue
        try:
            parsed = ast.parse(result, mode="eval")
        except SyntaxError as error:
            errors.append(f"line {index}: result is not valid Python AST: {error}")
            continue
        if not isinstance(parsed.body, ast.List):
            errors.append(f"line {index}: result must be a Python list expression")

    return not errors, errors


def official_evaluate_command(
    *,
    model_name: str,
    category: str,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    partial_eval: bool = True,
) -> str:
    """Return a PowerShell command that points BFCL at this runner's output."""
    root = Path(output_root).resolve()
    escaped_root = str(root).replace("'", "''")
    escaped_model = model_name.replace("'", "''")
    escaped_category = category.replace("'", "''")
    command = (
        f"$env:BFCL_PROJECT_ROOT = '{escaped_root}'\n"
        f"bfcl evaluate --model '{escaped_model}' "
        f"--test-category '{escaped_category}'"
    )
    if partial_eval:
        command += " --partial-eval"
    return command


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_result_rows(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        loaded = json.loads(text)
        if not isinstance(loaded, list):
            raise ValueError("JSON result file must contain a list")
        return loaded

    rows = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON at {path}:{line_number}: {error.msg}"
                ) from error
    return rows
