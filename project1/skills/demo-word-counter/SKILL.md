---
name: demo-word-counter
description: Count text lines, words, and characters using a declared Python script when a user asks for a deterministic text summary.
---

# Demo Word Counter

Use this skill when the user wants a deterministic count of text size, such as lines, words, non-empty lines, or characters.

## Workflow

1. If the user gives text directly, call `run_skill_script` with `script_path` set to `scripts/count_words.py` and pass the text through `stdin`.
2. If the user asks to count a file inside this skill, call `run_skill_script` with `argv` like `["--file", "assets/sample.txt"]`.
3. If the user asks for counting rules, read `references/counting-rules.md` with `load_skill`.

## Script

Run only the declared helper:

- `scripts/count_words.py`

The script prints JSON with line, non-empty line, word, character, and byte counts.
