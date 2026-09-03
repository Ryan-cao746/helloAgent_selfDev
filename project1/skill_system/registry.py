"""Discover and parse local agent skills.
发现和序列化。从本地文件仓库中搜索、加载、注册skills，根据元数据搜索查找，返回根据元数据生成的总结，节约上下文
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Skill(BaseModel):
    """A reusable workflow loaded from a local ``SKILL.md`` file.主要数据结构，具备参数校验等功能"""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    name: str = Field(min_length=1)
    description: str = ""   # 描述
    root_path: Path     # 存储路径
    instructions: str = ""  # md文件的主体内容
    references: list[str] = Field(default_factory=list)     # 该skill引用的其他文件路径
    scripts: list[str] = Field(default_factory=list)    # 该skill配套的脚本路径
    assets: list[str] = Field(default_factory=list)
    mcp_dependencies: list[str] = Field(default_factory=list)   # mcp依赖

    def metadata_summary(self) -> str:
        """根据mcp依赖和描述生成元数据总结"""
        dependency_text = ""
        if self.mcp_dependencies:
            dependency_text = (
                f" MCP dependencies: {', '.join(self.mcp_dependencies)}."
            )
        return f"- {self.name}: {self.description}{dependency_text}"


class SkillRegistry:
    """Scans configured skill roots and exposes metadata-first lookup."""

    def __init__(self, skill_roots: list[Path]):
        self.skill_roots = [root.expanduser().resolve() for root in skill_roots]    # 获取所有提供的skill_roots的绝对路径
        self._skills: dict[str, Skill] = {} # 初始化注册表
        self.errors: list[str] = []
        self.refresh()

    @classmethod
    def for_project(cls, repo_root: Path, project_root: Path) -> "SkillRegistry":
        """Create the default registry for this repository layout."""
        repo = repo_root.expanduser().resolve()     # 获取skills仓库的绝对路径
        project = project_root.expanduser().resolve()       # 获取项目目录的绝对路径
        return cls([
            repo / ".agents" / "skills",
            project / "skills",
        ])

    def refresh(self) -> None:
        """Rescan skill directories without loading unrelated files.
        加载、注册skills
        """
        skills: dict[str, Skill] = {}
        errors: list[str] = []

        for skill_file in self._find_skill_files():
            try:
                skill = self._load_skill_file(skill_file)
            except Exception as error:
                errors.append(f"{skill_file}: {error}")
                continue

            if skill.name in skills:
                errors.append(
                    f"{skill_file}: duplicate skill name '{skill.name}'"
                )
                continue
            skills[skill.name] = skill

        self._skills = skills
        self.errors = errors

    def list_skills(self) -> list[Skill]:
        """Return all discovered skills, sorted by name."""
        return [self._skills[name] for name in sorted(self._skills)]

    def get(self, name: str) -> Skill | None:
        """Return a skill by exact name."""
        return self._skills.get(name)

    def match(self, query: str, limit: int = 5) -> list[Skill]:
        """Return simple metadata matches for a user/model query.
        根据元数据检索skills
        """
        normalized_query = query.strip().lower()
        if not normalized_query:
            return self.list_skills()[:limit]

        scored: list[tuple[int, Skill]] = []
        query_terms = [
            term for term in normalized_query.replace("_", " ").split()
            if term
        ]
        for skill in self.list_skills():
            haystack = f"{skill.name} {skill.description}".lower()
            score = sum(1 for term in query_terms if term in haystack)
            if normalized_query in haystack:
                score += 3
            if score > 0:
                scored.append((score, skill))

        scored.sort(key=lambda item: (-item[0], item[1].name))
        return [skill for _, skill in scored[:limit]]

    def describe(self, query: str | None = None) -> str:
        """Render metadata summaries suitable for prompt injection.根据查询到的元数据生成总结"""
        skills = self.match(query or "", limit=20) if query else self.list_skills()
        if not skills:
            if self.errors:
                return (
                    "No valid skills discovered. Skill scan errors:\n"
                    + "\n".join(f"- {error}" for error in self.errors)
                )
            return "No skills discovered."

        lines = [skill.metadata_summary() for skill in skills]  # 根据元数据生成总结
        if self.errors:
            lines.append("Skill scan errors:")
            lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)

    def load_full(self, name: str) -> Skill:
        """Reload and return a skill with full instructions from disk."""
        metadata = self.get(name)
        if metadata is None:
            raise KeyError(f"Skill not found: {name}")
        return self._load_skill_file(metadata.root_path / "SKILL.md")

    def _find_skill_files(self) -> list[Path]:
        """根据初始化时提供的路径查询对应的skill，返回对应的文件"""
        files: list[Path] = []
        for root in self.skill_roots:
            if not root.exists():
                continue
            direct_skill = root / "SKILL.md"
            if direct_skill.exists():
                files.append(direct_skill)
            for child in sorted(root.iterdir(), key=lambda path: path.name):    # 遍历当前skill路径对应下的文件夹中的其他文件
                skill_file = child / "SKILL.md"
                if child.is_dir() and skill_file.exists():
                    files.append(skill_file)
        return files

    def _load_skill_file(self, skill_file: Path) -> Skill:
        """解析元数据，创建并返回skill对象"""
        text = skill_file.read_text(encoding="utf-8")
        metadata, body = _parse_frontmatter(text)
        name = str(metadata.get("name", "")).strip()
        description = str(metadata.get("description", "")).strip()

        if not name:
            raise ValueError("frontmatter field 'name' is required")
        if not description:
            raise ValueError("frontmatter field 'description' is required")

        root_path = skill_file.parent.resolve()
        return Skill(
            name=name,
            description=description,
            root_path=root_path,
            instructions=body.strip(),
            references=_collect_relative_files(root_path / "references"),
            scripts=_collect_relative_files(root_path / "scripts"),
            assets=_collect_relative_files(root_path / "assets"),
            mcp_dependencies=_string_list(metadata.get("mcp_dependencies")),
        )


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """从skills.md文件中分割出内容和元数据"""
    normalized = text.replace("\r\n", "\n")
    lines = normalized.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md must start with frontmatter")

    end_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":   # 从这里看出元数据和正文由---分割
            end_index = index
            break

    if end_index is None:
        raise ValueError("SKILL.md frontmatter is not closed")

    metadata = _parse_simple_yaml(lines[1:end_index])
    body = "\n".join(lines[end_index + 1:])
    return metadata, body


def _parse_simple_yaml(lines: list[str]) -> dict[str, Any]:
    """从yaml解析元数据"""
    metadata: dict[str, Any] = {}
    current_key: str | None = None

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("- ") and current_key:
            metadata.setdefault(current_key, []).append(stripped[2:].strip())
            continue

        if ":" not in stripped:
            raise ValueError(f"unsupported frontmatter line: {stripped}")

        key, value = stripped.split(":", 1)
        key = key.strip()
        parsed_value = _parse_scalar(value.strip())
        metadata[key] = parsed_value
        current_key = key if parsed_value == [] else None

    return metadata


def _parse_scalar(value: str) -> Any:
    if value == "":
        return []
    if (
        len(value) >= 2
        and value[0] in {"'", '"'}
        and value[-1] == value[0]
    ):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [
            item.strip().strip("'\"")
            for item in inner.split(",")
            if item.strip()
        ]
    return value


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value)]


def _collect_relative_files(directory: Path) -> list[str]:
    if not directory.exists() or not directory.is_dir():
        return []
    root = directory.parent.resolve()
    files = []
    for path in sorted(directory.rglob("*"), key=lambda item: str(item)):
        if path.is_file():
            files.append(path.resolve().relative_to(root).as_posix())
    return files
