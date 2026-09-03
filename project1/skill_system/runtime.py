"""Runtime helpers for loading skill instructions and materials.运行时基础层。维护registry，加载skills以及相关材料文件"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

from project1.skill_system.registry import Skill, SkillRegistry


class SkillRuntime:
    """Provides metadata summaries and progressive skill loading."""

    def __init__(
            self,
            registry: SkillRegistry,
            max_reference_chars: int = 12_000,
            python_executable: Path | None = None,
    ):
        self.registry = registry
        self.max_reference_chars = max_reference_chars
        self.python_executable = (
            python_executable or _find_project_python(registry.skill_roots)
        )
        self.activated_skills: dict[str, Skill] = {}

    def describe_available_skills(self, query: str | None = None) -> str:
        """根据查询到的元数据生成总结。Return metadata only; full skill text is loaded on demand."""
        return self.registry.describe(query)

    def load_skill_context(
            self,
            name: str,
            include_references: bool = False,
            reference_path: str | None = None,
    ) -> str:
        """根据名称加载对应skill Load one skill and optionally one or all reference files."""
        skill = self.registry.load_full(name)
        self.activated_skills[skill.name] = skill

        sections = [
            f"# Skill: {skill.name}",
            f"Description: {skill.description}",
        ]
        if skill.mcp_dependencies:
            sections.append(
                "MCP dependencies: " + ", ".join(skill.mcp_dependencies)
            )
        sections.append("## Instructions\n" + (skill.instructions or "None"))
        sections.append(self._render_material_inventory(skill))

        if reference_path:
            sections.append(self._render_reference(skill, reference_path))
        elif include_references:
            for path in skill.references:
                sections.append(self._render_reference(skill, path))

        return "\n\n".join(section for section in sections if section)

    def run_skill_script(
            self,
            name: str,
            script_path: str,   # 脚本路径
            argv: list[str] | None = None,
            stdin: str | None = None,
            timeout_seconds: int = 30,
    ) -> str:
        """显式执行某个 Skill 声明的 Python 脚本。"""
        skill = self.registry.load_full(name) # 根据名称加载
        self.activated_skills[skill.name] = skill

        # 脚本路径和参数处理
        normalized_script_path = _normalize_relative_path(script_path)
        self._validate_script_path(skill, normalized_script_path)
        resolved_script_path = _resolve_inside(
            skill.root_path,
            normalized_script_path,
        )
        arguments = [str(item) for item in (argv or [])]
        started = perf_counter()

        try:
            completed = subprocess.run(
                [
                    str(self.python_executable),    # 解释器路径
                    str(resolved_script_path),      # 脚本路径
                    *arguments,     # 参数
                ],  # 不是直接跑 bash 命令，而是显式指定用哪个 Python 去执行哪个 .py 文件
                input=stdin,    # 把 stdin 变量的内容，通过管道塞进你子进程的 sys.stdin 里。你的 script.py 里如果有 input() 函数，读到的就是这个值。
                text=True,  # 让传输的数据变成字符串（而不是二进制字节）
                capture_output=True,    # 把脚本打印到屏幕的所有内容（print() 和报错堆栈）全部捕获进内存，不会显示在终端屏幕上。
                cwd=skill.root_path,    # 切换工作目录到root_path
                shell=False,    # 明确告诉 Python 不要经过系统的 bash 解释器，直接用列表传参。防止黑客注入
                timeout=timeout_seconds,
            )   # 创建一个子进程，执行指定的命令行参数
        except subprocess.TimeoutExpired as error:
            duration_ms = (perf_counter() - started) * 1000
            return _format_script_result(
                script_path=normalized_script_path,
                exit_code=None,
                stdout=_completed_output(error.stdout),
                stderr=_completed_output(error.stderr),
                duration_ms=duration_ms,
                timed_out=True,
            )

        duration_ms = (perf_counter() - started) * 1000
        return _format_script_result(
            script_path=normalized_script_path,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_ms=duration_ms,
            timed_out=False,
        )   # 返回结构化执行结果

    @staticmethod
    def _validate_script_path(skill: Skill, script_path: str) -> None:
        if script_path not in skill.scripts:
            raise ValueError(
                f"Script '{script_path}' is not declared by {skill.name}"
            )
        path = Path(script_path)
        if path.suffix != ".py" or not script_path.startswith("scripts/"):
            raise ValueError(
                f"Script '{script_path}' is not an allowed Python skill script"
            )

    def _render_material_inventory(self, skill: Skill) -> str:
        """获取相关辅助文件的目录清单"""
        lines = ["## Materials"]
        lines.append(_format_list("references", skill.references))
        lines.append(_format_list("scripts", skill.scripts))
        lines.append(_format_list("assets", skill.assets))
        return "\n".join(lines)

    def _render_reference(self, skill: Skill, reference_path: str) -> str:
        """提取该skill引用文件对应的内容"""
        if reference_path not in skill.references:
            raise ValueError(
                f"Reference '{reference_path}' is not declared by {skill.name}"
            )

        path = _resolve_inside(skill.root_path, reference_path)     # 解析为绝对路径
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"## Reference: {reference_path}\nUnable to read as UTF-8."

        # 超过对应字数截短
        truncated = len(content) > self.max_reference_chars
        if truncated:
            content = content[:self.max_reference_chars]
        note = "\n[reference truncated]" if truncated else ""
        return f"## Reference: {reference_path}\n{content}{note}"


def _format_list(label: str, values: list[str]) -> str:
    if not values:
        return f"{label}: none"
    return label + ":\n" + "\n".join(f"- {value}" for value in values)


def _resolve_inside(root: Path, relative_path: str) -> Path:
    """解析相对路径为绝对路径"""
    base = root.resolve()
    resolved = (base / relative_path).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        raise ValueError(f"Path escapes skill root: {relative_path}") from None
    return resolved


def _normalize_relative_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if Path(normalized).is_absolute():
        raise ValueError(f"Absolute script paths are not allowed: {path}")
    return normalized


def _find_project_python(skill_roots: list[Path]) -> Path:
    """寻找Python解释器exe路径，默认使用整个项目指定的解释器路径"""
    for root in skill_roots:
        for parent in [root, *root.parents]:
            windows_python = parent / ".venv" / "Scripts" / "python.exe"
            if windows_python.exists():
                return windows_python
            posix_python = parent / ".venv" / "bin" / "python"
            if posix_python.exists():
                return posix_python
    return Path(sys.executable) # 将当前 Python 解释器的可执行文件路径，转换成一个 pathlib.Path 对象。


def _completed_output(output: Any) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return str(output)


def _format_script_result(
        script_path: str,
        exit_code: int | None,
        stdout: str,
        stderr: str,
        duration_ms: float,
        timed_out: bool,
) -> str:
    exit_code_text = "timeout" if timed_out else str(exit_code)
    return (
        f"script: {script_path}\n"
        f"exit_code: {exit_code_text}\n"
        f"timed_out: {timed_out}\n"
        f"duration_ms: {duration_ms:.2f}\n"
        "stdout:\n"
        f"{stdout or ''}\n"
        "stderr:\n"
        f"{stderr or ''}"
    )
