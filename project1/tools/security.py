"""提供工具输入输出使用的敏感信息脱敏和文本长度限制。"""

import re


_AUTHORIZATION_PATTERN = re.compile(
    r"(?i)([\"']?authorization[\"']?\s*[:=]\s*)([\"']?)"
    r"(?:Bearer\s+)?[^\"'\s,;&}]+([\"']?)"
)
_BEARER_PATTERN = re.compile(
    r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]+"
)
_SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)([\"']?(?:api[_-]?key|password|secret|"
    r"access[_-]?token|refresh[_-]?token|token)[\"']?\s*[:=]\s*)"
    r"([\"']?)([^\"'\s,;&}]+)([\"']?)"
)


def redact_sensitive_text(text: str) -> str:
    """在存储或展示前遮盖常见密钥、令牌和授权头内容。"""
    redacted = _AUTHORIZATION_PATTERN.sub(r"\1\2***\2", text)
    redacted = _BEARER_PATTERN.sub(r"\1***", redacted)

    def replace_sensitive_value(match: re.Match[str]) -> str:
        quote = match.group(2)
        closing_quote = quote if quote else ""
        return f"{match.group(1)}{quote}***{closing_quote}"

    return _SENSITIVE_VALUE_PATTERN.sub(replace_sensitive_value, redacted)


def limit_text(text: str, max_chars: int) -> tuple[str, bool, int]:
    """限制文本长度，并返回截断标记和原始字符数。"""
    original_length = len(text)
    if original_length <= max_chars:
        return text, False, original_length
    return text[:max_chars], True, original_length
