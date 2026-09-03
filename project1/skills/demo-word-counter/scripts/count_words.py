from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Count lines, words, characters, and UTF-8 bytes."
    )
    parser.add_argument("--text", help="Text to count.")
    parser.add_argument("--file", help="Path to a text file relative to the skill root.")
    return parser.parse_args()


def read_input(args: argparse.Namespace) -> str:
    if args.text is not None and args.file is not None:
        raise ValueError("Use only one of --text or --file.")
    if args.text is not None:
        return args.text
    if args.file is not None:
        path = Path(args.file)
        if path.is_absolute():
            raise ValueError("Absolute file paths are not allowed.")
        resolved = path.resolve()
        root = Path.cwd().resolve()
        try:
            resolved.relative_to(root)
        except ValueError as error:
            raise ValueError(f"File path escapes skill root: {args.file}") from error
        return resolved.read_text(encoding="utf-8")
    return sys.stdin.read()


def count_text(text: str) -> dict[str, int]:
    lines = text.splitlines()
    words = re.findall(r"\S+", text)
    return {
        "lines": len(lines),
        "non_empty_lines": sum(1 for line in lines if line.strip()),
        "words": len(words),
        "characters": len(text),
        "bytes_utf8": len(text.encode("utf-8")),
    }


def main() -> int:
    try:
        text = read_input(parse_args())
        print(json.dumps(count_text(text), ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as error:
        print(f"count_words failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
