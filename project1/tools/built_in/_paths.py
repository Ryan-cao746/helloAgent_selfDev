"""提供文件工具共用的工作目录解析与越界校验。"""

from pathlib import Path


class PathEscapeError(ValueError):
    """目标路径解析后超出允许的工作目录时抛出。"""


def resolve_path(workspace_root: Path, raw_path: str) -> Path:
    """将目标路径解析到 ``workspace_root`` 之内，校验不越界。
    返回绝对路径
    相对路径以 ``workspace_root`` 为基准解析；绝对路径也必须位于
    ``workspace_root`` 之内，否则抛出 ``PathEscapeError``。
    """
    workspace = workspace_root.expanduser().resolve()
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = workspace / path
    resolved = path.resolve()

    try:
        resolved.relative_to(workspace)
    except ValueError:
        raise PathEscapeError(
            f"路径越界：{resolved} 不在工作目录 {workspace} 内"
        ) from None

    return resolved
