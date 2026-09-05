"""Load and validate BFCL JSONL prompt entries."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from project1.evaluation.bfcl.schemas import BFCLCase


class BFCLDataError(ValueError):
    """Raised when a BFCL dataset file cannot be parsed or validated."""


def load_bfcl_cases(
    dataset_path: str | Path,
    limit: int | None = None,
) -> list[BFCLCase]:
    """Read BFCL JSONL cases from ``dataset_path``."""
    path = Path(dataset_path)
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive when provided")
    if not path.exists():
        raise BFCLDataError(f"BFCL dataset file does not exist: {path}")
    if not path.is_file():
        raise BFCLDataError(f"BFCL dataset path is not a file: {path}")

    cases: list[BFCLCase] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if limit is not None and len(cases) >= limit:
                break
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw_case = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise BFCLDataError(
                    f"Invalid JSON at {path}:{line_number}: {error.msg}"
                ) from error

            try:
                cases.append(BFCLCase.model_validate(raw_case))
            except ValidationError as error:
                raise BFCLDataError(
                    f"Invalid BFCL case at {path}:{line_number}: {error}"
                ) from error

    return cases
