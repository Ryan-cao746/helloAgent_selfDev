from typing import Literal, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

from project1.tools.base import Tool, ToolPolicy, ToolParameter


class FileBrowserArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_type: Literal["ls", "pwd", "cat"]
    path: str = Field(default=".")
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)


class FileBrowser(Tool):
    def __init__(self):
        super().__init__(
            name="file_browser",
            description="文件浏览工具，用于查看目录结构、获取项目根目录以及按行读取文件内容",
            policy=ToolPolicy(
                access="read_only",
                requires_confirmation=False,  # 只读
                max_output_chars=4000
            ),
            arguments_model=FileBrowserArguments,
        )
        self.project_root = self._find_project_root()

    @staticmethod
    def _find_project_root() -> Path:
        """从当前文件向上查找包含项目入口文件的目录，作为相对路径的基准。"""
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "main.py").exists():
                return parent
        return Path.cwd()

    def _resolve_path(self, raw_path: str) -> Path:
        """展开 ~ 并将相对路径解析到项目根目录之下。"""
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    def run(self, parameters: Dict[str, Any]) -> str:
        try:
            operation = parameters["operation_type"]
            if operation == "pwd":
                return str(self.project_root)

            path = self._resolve_path(parameters["path"])
            if operation == "ls":
                return self._list_directory(path)
            if operation == "cat":
                return self._read_file(
                    path,
                    parameters.get("start_line"),
                    parameters.get("end_line"),
                )
            return "错误的操作类型"
        except Exception as e:
            return f"目录读取错误: {e}"

    def _list_directory(self, path: Path) -> str:
        if not path.exists():
            return f"路径不存在: {path}"
        if not path.is_dir():
            return f"路径不是目录: {path}"

        entries = []
        for item in sorted(path.iterdir(), key=lambda p: p.name.lower()):
            marker = "/" if item.is_dir() else ""
            entries.append(item.name + marker)
        if not entries:
            return f"目录为空: {path}"
        return "\n".join(entries)

    def _read_file(
            self,
            path: Path,
            start_line: int | None,
            end_line: int | None,
    ) -> str:
        if not path.exists():
            return f"文件不存在: {path}"
        if path.is_dir():
            return f"目标是目录而不是文件: {path}"
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"无法以 UTF-8 读取（可能是二进制文件）: {path}"

        lines = content.splitlines()
        total = len(lines)
        start = start_line or 1
        end = end_line or total

        if start > total:
            return f"起始行 {start} 超出文件总行数 {total}"
        if end < start:
            return f"结束行 {end} 不能小于起始行 {start}"
        end = min(end, total)

        numbered = [
            f"{number}: {line}"
            for number, line in enumerate(lines[start - 1:end], start=start)
        ]
        header = f"{path} （共 {total} 行，显示第 {start}-{end} 行）"
        return header + "\n" + "\n".join(numbered)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="operation_type",
                type="Literal['ls', 'pwd', 'cat']",
                description="操作类型：ls 列出目标目录下的文件和目录；pwd 获取项目根目录；cat 读取指定文件的内容",
                required=True,
            ),
            ToolParameter(
                name="path",
                type="str",
                description="目标路径，支持相对路径（相对于项目根目录）和 ~ 简写；pwd 操作可省略",
                required=False,
                default=".",
            ),
            ToolParameter(
                name="start_line",
                type="int",
                description="读取文件的起始行（从 1 开始），仅 cat 操作使用",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="end_line",
                type="int",
                description="读取文件的结束行（包含），仅 cat 操作使用",
                required=False,
                default=None,
            ),
        ]
