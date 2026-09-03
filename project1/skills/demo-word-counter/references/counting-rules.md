# Counting Rules

- `characters` counts Python Unicode code points in the input text.
- `bytes_utf8` counts bytes after UTF-8 encoding.
- `lines` follows `str.splitlines()`, so a trailing newline does not create an extra empty line.
- `non_empty_lines` counts lines with non-whitespace content.
- `words` counts contiguous non-whitespace tokens.
