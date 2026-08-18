import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, ConfigDict, Field

from project1.supportive_functions.tfidf_search import build_tfidf_index, query_tfidf
from project1.tools.base import Tool, ToolPolicy, ToolParameter


class ExtractSkillsArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=120)


class ExtractSkills(Tool):
    def __init__(self):
        super().__init__(
            name="extract_skills",
            description="搜索并提取本地skills文件内容。优先调用此工具，而非直接进行网络搜索",
            policy=ToolPolicy(
                access="read_only",
                requires_confirmation=False,
                max_output_chars=1000
            ),
            arguments_model=ExtractSkillsArguments,
        )
        self.project_root = self.get_project_root()
        self.skill_dict_root = self.get_skills_root()
        self._index: Tuple[Any, ...] | None = None

    def run(self, parameters: Dict[str, Any]) -> str:
        query = parameters["query"].strip()
        if not query:
            return "查询内容为空，无法检索 skills。"

        paragraph_files, paragraphs, contents_by_file, vectorizer, matrix = self._get_index()
        if not paragraphs:
            return "skills 目录中没有可检索的 md 文件。"

        scores = query_tfidf(query, vectorizer, matrix)

        best_file: Path | None = None
        best_score = -1.0
        for file_path, score in zip(paragraph_files, scores):   # 打擂台，选最匹配的文件
            if math.isfinite(score) and score > best_score:
                best_score = score
                best_file = file_path

        if best_file is None:
            return "未在 skills 目录中找到匹配内容。"

        return contents_by_file[best_file]

    def _get_index(self) -> Tuple[Any, ...]:
        """按文件修改时间缓存索引，仅在 skills 目录变化时重建。

        返回 (signature, paragraph_files, paragraphs, contents_by_file, vectorizer, matrix)。
        """
        files = sorted(self.skill_dict_root.rglob("*.md"))
        signature = tuple((f, f.stat().st_mtime_ns) for f in files)

        if self._index is not None and self._index[0] == signature:
            return self._index[1:]

        paragraph_files: List[Path] = []
        paragraphs: List[str] = []
        contents_by_file: Dict[Path, str] = {}

        for md_file in files:
            content = md_file.read_text(encoding="utf-8")
            contents_by_file[md_file] = content
            for paragraph in content.split("\n\n"):
                paragraph = paragraph.strip()
                if paragraph:
                    paragraph_files.append(md_file)
                    paragraphs.append(paragraph)

        if not paragraphs:
            self._index = (signature, paragraph_files, paragraphs, contents_by_file, None, None)
            return self._index[1:]

        vectorizer, matrix = build_tfidf_index(paragraphs)
        self._index = (signature, paragraph_files, paragraphs, contents_by_file, vectorizer, matrix)
        return self._index[1:]

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="str",
                description="需要从skills目录中查找的内容，长度为 1~120 个字符；过长内容会被接口截断。",
                required=True
            )
        ]

    @staticmethod
    def get_project_root() -> Path:
        """从当前文件向上查找包含项目入口文件的目录。"""
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "main.py").exists():
                return parent
        raise FileNotFoundError("未找到包含 main.py 的项目目录")

    def get_skills_root(self) -> Path:
        """根据根目录查找skills文件目录。"""
        if (self.project_root / "skills").exists():
            return self.project_root / "skills"
        raise FileNotFoundError("项目目录中不存在 程序记忆skills 目录")
