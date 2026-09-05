"""测试自定义记忆名称下的上下文构建。"""

import unittest

from project1.context.advanced_context_manager import AdvancedContextManager
from project1.context.react_context_manager import ReActContextManager
from project1.memory.memory_manager import MemoryManager


class StubMemory:
    def __init__(self):
        self.memories = {}

    def add(self, memory_item):
        self.memories[memory_item.id] = memory_item

    def retrieve(self, query, limit=5, **kwargs):
        return list(self.memories.values())[:limit]

    def get_all_memories(self):
        return self.memories


class ConfigurableMemoryNamesTest(unittest.TestCase):
    def setUp(self):
        self.manager = MemoryManager(
            enable_working_memory=True,
            enable_episodic_memory=True,
            working_memory=StubMemory(),
            episodic_memory=StubMemory(),
            working_memory_name="session",
            episodic_memory_name="profile",
        )
        self.manager.add("session", "当前对话", "user")
        self.manager.add("profile", "长期信息", "user")

    def test_manager_registers_configured_names(self):
        self.assertEqual({"session", "profile"}, set(self.manager.memory_types))
        self.assertNotIn("working", self.manager.memory_types)
        self.assertNotIn("episodic", self.manager.memory_types)

    def test_react_context_uses_manager_names(self):
        prompt = ReActContextManager(memory_manager=self.manager).build("问题")

        self.assertIn("当前对话", prompt)
        self.assertIn("长期信息", prompt)

    def test_advanced_context_uses_manager_names(self):
        prompt = AdvancedContextManager(memory_manager=self.manager).build("问题")

        self.assertIn("当前对话", prompt)
        self.assertIn("长期信息", prompt)

    def test_names_must_be_distinct(self):
        with self.assertRaises(ValueError):
            MemoryManager(
                working_memory_name="memory",
                episodic_memory_name="memory",
            )


if __name__ == "__main__":
    unittest.main()
