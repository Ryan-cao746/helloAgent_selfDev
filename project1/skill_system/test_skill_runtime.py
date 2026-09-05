"""Tests for local skill discovery and progressive loading."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from project1.context.advanced_context_manager import AdvancedContextManager
from project1.memory.memory_manager import MemoryManager
from project1.skill_system import SkillRegistry, SkillRuntime
from project1.tools.base import ToolCall, ToolExecutionPolicy
from project1.tools.built_in.skill_tools import (
    ListSkills,
    LoadSkill,
    RunSkillScript,
)
from project1.tools.registry import ToolRegistry


class SkillRuntimeTest(unittest.TestCase):
    def test_scans_standard_and_project_skill_roots(self):
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            project_root = repo_root / "project1"
            self._write_skill(
                repo_root / ".agents" / "skills" / "repo_skill",
                "repo_skill",
                "Repository skill",
                "Use the repository workflow.",
            )
            self._write_skill(
                project_root / "skills" / "project_skill",
                "project_skill",
                "Project skill",
                "Use the project workflow.",
            )

            registry = SkillRegistry.for_project(repo_root, project_root)

            self.assertEqual(
                ["project_skill", "repo_skill"],
                [skill.name for skill in registry.list_skills()],
            )
            self.assertEqual([], registry.errors)

    def test_load_skill_returns_instructions_and_material_inventory(self):
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            project_root = repo_root / "project1"
            skill_root = repo_root / ".agents" / "skills" / "writer"
            self._write_skill(
                skill_root,
                "writer",
                "Draft reusable docs",
                "Follow the house style.",
                mcp_dependencies=["demo_search"],
            )
            reference = skill_root / "references" / "style.md"
            reference.parent.mkdir(parents=True)
            reference.write_text("Use short sentences.", encoding="utf-8")
            script = skill_root / "scripts" / "lint.py"
            script.parent.mkdir()
            script.write_text("print('ok')", encoding="utf-8")
            asset = skill_root / "assets" / "logo.txt"
            asset.parent.mkdir()
            asset.write_text("asset", encoding="utf-8")

            runtime = SkillRuntime(
                SkillRegistry.for_project(repo_root, project_root)
            )
            context = runtime.load_skill_context(
                "writer",
                reference_path="references/style.md",
            )

            self.assertIn("# Skill: writer", context)
            self.assertIn("Follow the house style.", context)
            self.assertIn("MCP dependencies: demo_search", context)
            self.assertIn("references/style.md", context)
            self.assertIn("scripts/lint.py", context)
            self.assertIn("assets/logo.txt", context)
            self.assertIn("Use short sentences.", context)

    def test_bad_skills_are_reported_without_stopping_scan(self):
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            project_root = repo_root / "project1"
            self._write_skill(
                repo_root / ".agents" / "skills" / "valid",
                "valid",
                "Valid skill",
                "Instructions.",
            )
            bad_root = project_root / "skills" / "bad"
            bad_root.mkdir(parents=True)
            (bad_root / "SKILL.md").write_text(
                "# Missing frontmatter",
                encoding="utf-8",
            )

            registry = SkillRegistry.for_project(repo_root, project_root)

            self.assertEqual(["valid"], [skill.name for skill in registry.list_skills()])
            self.assertEqual(1, len(registry.errors))
            self.assertIn("must start with frontmatter", registry.errors[0])

    def test_duplicate_skill_names_are_reported(self):
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            project_root = repo_root / "project1"
            self._write_skill(
                repo_root / ".agents" / "skills" / "one",
                "shared",
                "First",
                "One.",
            )
            self._write_skill(
                project_root / "skills" / "two",
                "shared",
                "Second",
                "Two.",
            )

            registry = SkillRegistry.for_project(repo_root, project_root)

            self.assertEqual(["shared"], [skill.name for skill in registry.list_skills()])
            self.assertEqual(1, len(registry.errors))
            self.assertIn("duplicate skill name 'shared'", registry.errors[0])

    def test_skill_tools_expose_metadata_then_full_context(self):
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            project_root = repo_root / "project1"
            self._write_skill(
                repo_root / ".agents" / "skills" / "reviewer",
                "reviewer",
                "Review code changes",
                "Find behavior regressions first.",
            )
            runtime = SkillRuntime(
                SkillRegistry.for_project(repo_root, project_root)
            )
            registry = ToolRegistry()
            registry.register_tool(ListSkills(runtime))
            registry.register_tool(LoadSkill(runtime))

            listed = registry.execute_tool_call_structured(
                ToolCall(tool_name="list_skills", parameters={})
            )
            loaded = registry.execute_tool_call_structured(
                ToolCall(
                    tool_name="load_skill",
                    parameters={"name": "reviewer"},
                )
            )

            self.assertEqual("success", listed.status)
            self.assertIn("Review code changes", listed.output)
            self.assertNotIn("Find behavior regressions first.", listed.output)
            self.assertEqual("success", loaded.status)
            self.assertIn("Find behavior regressions first.", loaded.output)

    def test_context_injects_skill_metadata_only(self):
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            project_root = repo_root / "project1"
            self._write_skill(
                repo_root / ".agents" / "skills" / "reviewer",
                "reviewer",
                "Review code changes",
                "Secret detailed instructions.",
            )
            runtime = SkillRuntime(
                SkillRegistry.for_project(repo_root, project_root)
            )
            prompt = AdvancedContextManager(
                memory_manager=MemoryManager(),
                skill_runtime=runtime,
            ).build("review this change")

            self.assertIn("reviewer", prompt)
            self.assertIn("Review code changes", prompt)
            self.assertIn("load_skill", prompt)
            self.assertNotIn("Secret detailed instructions.", prompt)

    def test_runs_declared_python_script_with_arguments(self):
        with TemporaryDirectory() as tmp:
            runtime = self._runtime_with_script(
                tmp,
                "runner",
                "import sys\nprint('args=' + ','.join(sys.argv[1:]))\n",
            )

            result = runtime.run_skill_script(
                "runner",
                "scripts/run.py",
                argv=["a", "b"],
            )

            self.assertIn("script: scripts/run.py", result)
            self.assertIn("exit_code: 0", result)
            self.assertIn("timed_out: False", result)
            self.assertIn("args=a,b", result)

    def test_script_runs_from_skill_root_and_reads_materials(self):
        with TemporaryDirectory() as tmp:
            runtime = self._runtime_with_script(
                tmp,
                "reader",
                "from pathlib import Path\n"
                "print(Path('references/data.txt').read_text())\n",
            )
            skill = runtime.registry.get("reader")
            reference = skill.root_path / "references" / "data.txt"
            reference.parent.mkdir()
            reference.write_text("material-ok", encoding="utf-8")

            result = runtime.run_skill_script("reader", "scripts/run.py")

            self.assertIn("exit_code: 0", result)
            self.assertIn("material-ok", result)

    def test_rejects_undeclared_non_python_and_escaping_scripts(self):
        with TemporaryDirectory() as tmp:
            runtime = self._runtime_with_script(
                tmp,
                "safe",
                "print('ok')\n",
            )
            skill = runtime.registry.get("safe")
            shell_script = skill.root_path / "scripts" / "run.sh"
            shell_script.write_text("echo bad", encoding="utf-8")
            runtime.registry.refresh()

            with self.assertRaises(ValueError):
                runtime.run_skill_script("safe", "scripts/missing.py")
            with self.assertRaises(ValueError):
                runtime.run_skill_script("safe", "scripts/run.sh")
            with self.assertRaises(ValueError):
                runtime.run_skill_script("safe", "../outside.py")

    def test_run_skill_script_requires_confirmation_in_registry(self):
        with TemporaryDirectory() as tmp:
            runtime = self._runtime_with_script(
                tmp,
                "runner",
                "print('confirmed')\n",
            )
            registry = ToolRegistry(
                ToolExecutionPolicy(allowed_access={"write"})
            )
            registry.register_tool(RunSkillScript(runtime))
            call = ToolCall(
                tool_name="run_skill_script",
                parameters={
                    "name": "runner",
                    "script_path": "scripts/run.py",
                },
            )

            pending = registry.execute_tool_call_structured(call)
            confirmed = registry.execute_tool_call_structured(
                call,
                confirmed=True,
            )

            self.assertEqual("confirmation_required", pending.status)
            self.assertEqual("success", confirmed.status)
            self.assertIn("confirmed", confirmed.output)

    def test_script_failure_and_timeout_return_clear_results(self):
        with TemporaryDirectory() as tmp:
            runtime = self._runtime_with_script(
                tmp,
                "failing",
                "import sys\nprint('before-fail')\nprint('bad', file=sys.stderr)\nsys.exit(7)\n",
            )
            failure = runtime.run_skill_script("failing", "scripts/run.py")
            self.assertIn("exit_code: 7", failure)
            self.assertIn("before-fail", failure)
            self.assertIn("bad", failure)

            runtime = self._runtime_with_script(
                tmp,
                "slow",
                "import time\nprint('start')\ntime.sleep(2)\n",
            )
            timeout = runtime.run_skill_script(
                "slow",
                "scripts/run.py",
                timeout_seconds=1,
            )
            self.assertIn("exit_code: timeout", timeout)
            self.assertIn("timed_out: True", timeout)

    def test_load_skill_does_not_execute_scripts(self):
        with TemporaryDirectory() as tmp:
            runtime = self._runtime_with_script(
                tmp,
                "loader",
                "from pathlib import Path\nPath('marker.txt').write_text('ran')\n",
            )
            skill = runtime.registry.get("loader")

            runtime.load_skill_context("loader")

            self.assertFalse((skill.root_path / "marker.txt").exists())

    def _write_skill(
            self,
            root: Path,
            name: str,
            description: str,
            instructions: str,
            mcp_dependencies: list[str] | None = None,
    ) -> None:
        root.mkdir(parents=True, exist_ok=True)
        dependencies = mcp_dependencies or []
        dependency_line = ""
        if dependencies:
            dependency_line = (
                "mcp_dependencies: ["
                + ", ".join(dependencies)
                + "]\n"
            )
        (root / "SKILL.md").write_text(
            "---\n"
            f"name: {name}\n"
            f"description: {description}\n"
            f"{dependency_line}"
            "---\n\n"
            f"{instructions}\n",
            encoding="utf-8",
        )

    def _runtime_with_script(
            self,
            tmp: str,
            name: str,
            script: str,
    ) -> SkillRuntime:
        repo_root = Path(tmp) / "repo"
        project_root = repo_root / "project1"
        skill_root = repo_root / ".agents" / "skills" / name
        self._write_skill(
            skill_root,
            name,
            f"{name} skill",
            "Run scripts when needed.",
        )
        script_path = skill_root / "scripts" / "run.py"
        script_path.parent.mkdir()
        script_path.write_text(script, encoding="utf-8")
        registry = SkillRegistry.for_project(repo_root, project_root)
        return SkillRuntime(registry, python_executable=Path(sys.executable))


if __name__ == "__main__":
    unittest.main()
