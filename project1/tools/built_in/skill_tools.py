"""Built-in tools for discovering and loading local skills.发现并加载本地skills的工具。这个是skill_system在Agent工具层上的具体实现，没什么好说的"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from project1.skill_system.runtime import SkillRuntime
from project1.tools.base import Tool, ToolParameter, ToolPolicy

# 参数校验相关数据模型
class ListSkillsArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str | None = Field(default=None, max_length=120)


class LoadSkillArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    include_references: bool = False
    reference_path: str | None = Field(default=None, max_length=500)


class RunSkillScriptArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    script_path: str = Field(min_length=1, max_length=500)
    argv: list[str] = Field(default_factory=list, max_length=50)
    stdin: str | None = Field(default=None, max_length=20_000)
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class ListSkills(Tool):
    """List available skills without loading their full instructions.通过元数据查询等相关方式列出skills，避免全部加载"""

    def __init__(self, skill_runtime: SkillRuntime):    # 注入runtime运行时
        super().__init__(
            name="list_skills",
            description=(
                "List local skills by metadata. Use this before loading a "
                "skill when the task looks like a reusable workflow."
            ),
            policy=ToolPolicy(
                access="read_only",
                requires_confirmation=False,
                max_output_chars=4000,
            ),
            arguments_model=ListSkillsArguments,
        )
        self.skill_runtime = skill_runtime

    def run(self, parameters: dict[str, Any]) -> str:
        return self.skill_runtime.describe_available_skills(
            parameters.get("query")
        )

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="str|null",
                description="Optional search text for matching skill metadata",
                required=False,
                default=None,
            )
        ]


class LoadSkill(Tool):
    """Load one skill's instructions and optional reference material.加载单个skills的主要内容以及引用的相关材料"""

    def __init__(self, skill_runtime: SkillRuntime):
        super().__init__(
            name="load_skill",
            description=(
                "Load a local skill by name. Returns full SKILL.md "
                "instructions plus declared material paths. Optionally reads "
                "one declared reference or all declared references."
            ),
            policy=ToolPolicy(
                access="read_only",
                requires_confirmation=False,
                max_output_chars=20_000,
            ),
            arguments_model=LoadSkillArguments,
        )
        self.skill_runtime = skill_runtime

    def run(self, parameters: dict[str, Any]) -> str:
        return self.skill_runtime.load_skill_context(
            name=parameters["name"],
            include_references=parameters.get("include_references", False),
            reference_path=parameters.get("reference_path"),
        )

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="name",
                type="str",
                description="Exact skill name from list_skills or prompt metadata",
                required=True,
            ),
            ToolParameter(
                name="include_references",
                type="bool",
                description="Whether to read all declared reference files",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="reference_path",
                type="str|null",
                description="One declared reference path to read",
                required=False,
                default=None,
            ),
        ]


class RunSkillScript(Tool):
    """Run a declared Python script from a loaded local skill.从加载的skills中运行一个Python脚本"""

    def __init__(self, skill_runtime: SkillRuntime):
        super().__init__(
            name="run_skill_script",
            description=(
                "Run a declared Python script from a local skill. The script "
                "must appear in that skill's scripts list from load_skill. "
                "Use only when the loaded skill instructions require script "
                "execution."
            ),
            policy=ToolPolicy(
                access="write",
                requires_confirmation=True,
                max_output_chars=20_000,
            ),
            arguments_model=RunSkillScriptArguments,
        )
        self.skill_runtime = skill_runtime

    def run(self, parameters: dict[str, Any]) -> str:
        return self.skill_runtime.run_skill_script(
            name=parameters["name"],
            script_path=parameters["script_path"],
            argv=parameters.get("argv", []),
            stdin=parameters.get("stdin"),
            timeout_seconds=parameters.get("timeout_seconds", 30),
        )

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="name",
                type="str",
                description="Exact skill name from list_skills or load_skill",
                required=True,
            ),
            ToolParameter(
                name="script_path",
                type="str",
                description=(
                    "Declared Python script path, for example "
                    "scripts/task.py"
                ),
                required=True,
            ),
            ToolParameter(
                name="argv",
                type="list[str]",
                description="Command-line arguments passed to the script",
                required=False,
                default=[],
            ),
            ToolParameter(
                name="stdin",
                type="str|null",
                description="Optional text sent to the script's stdin",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="timeout_seconds",
                type="int",
                description="Execution timeout, from 1 to 300 seconds",
                required=False,
                default=30,
            ),
        ]
