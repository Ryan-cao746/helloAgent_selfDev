from typing import Dict, Any, List
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from project1.tools.base import Tool, ToolPolicy, ToolParameter
from project1.tools.built_in._paths import resolve_path


class ModifyFileArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1)
    content: str


class ModifyFile(Tool):
    def __init__(self, workspace_root: Path | None = None):
        super().__init__(
            name="modify_file",
            description="修改或者新建文件，会创建不存在的父目录",
            policy=ToolPolicy(
                access="write",
                requires_confirmation=True,  # 显式要求确认
                max_output_chars=1000
            ),
            arguments_model=ModifyFileArguments
        )
        self.workspace_root = (
            workspace_root or self._find_project_root()
        ).resolve()

    @staticmethod
    def _find_project_root() -> Path:
        """从当前文件向上查找包含项目入口文件的目录，作为相对路径的基准。"""
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "main.py").exists():
                return parent
        return Path.cwd()

    def _resolve_path(self, raw_path: str) -> Path:
        """展开 ~ 并将相对路径解析到工作目录之下，校验不越界。"""
        return resolve_path(self.workspace_root, raw_path)

    def run(self, parameters: Dict[str, Any]) -> str:
        try:
            path = self._resolve_path(parameters["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(parameters["content"], encoding="utf-8")
            return f"已写入 {len(parameters['content'])} 字符到 {path}"
        except Exception as e:
            return f"文件写入失败: {e}"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="str",
                description="目标文件的路径，支持相对路径（相对于工作目录）和 ~ 简写",
                required=True,
            ),
            ToolParameter(
                name="content",
                type="str",
                description="希望写入/覆盖的内容",
                required=True,
            )
        ]
