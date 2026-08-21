"""加载文件工具使用的目录配置，并负责定位项目目录下的配置文件。"""

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class FileConfig(BaseModel):
    """文件工具相关的目录配置。"""

    workspace_root: Path = Field(default=Path("."))

    def resolve_workspace_root(self, base_dir: Optional[Path] = None) -> Path:
        """将相对路径的 workspace_root 解析到给定基准目录之下。

        ``base_dir`` 默认取项目目录 ``project1/``。
        如果没有指定提供base_dir，则直接取project1/
        """
        # 提供对workspace_root的相对/绝对路径的两种解决方案
        base = (base_dir or get_project_root()).resolve()
        root = self.workspace_root.expanduser()
        if not root.is_absolute():
            root = base / root
        return root.resolve()


def get_project_root() -> Path:
    """返回项目目录 ``project1/``，即本模块向上两级。"""
    return Path(__file__).resolve().parents[1]


def get_config_path() -> Path:
    """返回项目目录下的配置文件路径 ``project1/config.json``。"""
    return get_project_root() / "config.json"


def load_file_config(config_path: Optional[Path] = None) -> FileConfig:
    """读取并校验文件工具配置；文件不存在时返回默认配置。"""
    path = config_path or get_config_path()
    if not path.exists():
        return FileConfig()
    raw = json.loads(path.read_text(encoding="utf-8"))
    file_section = raw.get("file", {}) if isinstance(raw, dict) else {}
    return FileConfig.model_validate(file_section)
