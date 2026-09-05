"""测试工作目录解析、越界校验和文件配置加载。"""

import json
import tempfile
import unittest
from pathlib import Path

from project1.config.file_config import FileConfig, load_file_config
from project1.tools.built_in._paths import PathEscapeError, resolve_path


class ResolvePathTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def test_relative_path_resolves_under_workspace(self):
        result = resolve_path(self.workspace, "sub/dir/file.txt")
        self.assertEqual(self.workspace / "sub" / "dir" / "file.txt", result)

    def test_root_path_resolves_to_workspace(self):
        self.assertEqual(self.workspace, resolve_path(self.workspace, "."))

    def test_absolute_path_within_workspace(self):
        target = self.workspace / "a" / "b.txt"
        self.assertEqual(target, resolve_path(self.workspace, str(target)))

    def test_parent_traversal_is_rejected(self):
        with self.assertRaises(PathEscapeError):
            resolve_path(self.workspace, "../outside.txt")

    def test_absolute_path_outside_workspace_is_rejected(self):
        outside = self.workspace.parent / "other.txt"
        with self.assertRaises(PathEscapeError):
            resolve_path(self.workspace, str(outside))

    def test_tilde_is_expanded(self):
        home = Path.home().resolve()
        result = resolve_path(home, "~/x.txt")
        self.assertEqual(home / "x.txt", result)


class FileConfigTest(unittest.TestCase):
    def test_load_file_config_parses_workspace_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(
                json.dumps({"file": {"workspace_root": "workspace"}}),
                encoding="utf-8",
            )
            config = load_file_config(config_path)
            self.assertEqual(Path("workspace"), config.workspace_root)

    def test_load_file_config_returns_default_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = load_file_config(Path(tmp) / "missing.json")
            self.assertEqual(Path("."), config.workspace_root)

    def test_resolve_workspace_root_resolves_relative(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            config = FileConfig(workspace_root=Path("sub"))
            self.assertEqual(base / "sub", config.resolve_workspace_root(base))


if __name__ == "__main__":
    unittest.main()
