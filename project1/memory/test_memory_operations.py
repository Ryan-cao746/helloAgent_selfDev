"""测试记忆批量操作的校验、原子失败与 UUID 唯一性。"""

import unittest

from pydantic import ValidationError

from project1.memory.memory_manager import MemoryManager
from project1.memory.memory_operation import (
    MemoryOperationBatch,
)
from project1.memory.memory_types.simple_working_memory import SimpleWorkingMemory


class MemoryOperationBatchTest(unittest.TestCase):
    def setUp(self):
        self.manager = MemoryManager(
            enable_episodic_memory=True,
            episodic_memory=SimpleWorkingMemory(),
        )
        self.manager.add("episodic", "旧内容", "user")
        self.original_id = self.manager.get_all_by_type("episodic")[0].id

    def test_accepts_legacy_summary_field(self):
        batch = MemoryOperationBatch.model_validate({
            "operations": [{
                "operation": "UPDATE",
                "target_id": self.original_id,
                "summary": "新内容",
            }]
        })

        self.assertEqual("新内容", batch.operations[0].content)

    def test_rejects_missing_conditional_fields(self):
        with self.assertRaises(ValidationError):
            MemoryOperationBatch.model_validate({
                "operations": [{"operation": "UPDATE"}]
            })

    def test_rejects_conflicting_targets(self):
        with self.assertRaises(ValidationError):
            MemoryOperationBatch.model_validate({
                "operations": [
                    {
                        "operation": "UPDATE",
                        "target_id": self.original_id,
                        "content": "新内容",
                    },
                    {
                        "operation": "DELETE",
                        "target_id": self.original_id,
                    },
                ]
            })

    def test_applies_valid_batch(self):
        batch = MemoryOperationBatch.model_validate({
            "operations": [
                {
                    "operation": "UPDATE",
                    "target_id": self.original_id,
                    "content": "新内容",
                },
                {
                    "operation": "ADD",
                    "content": "新增内容",
                },
            ]
        })

        applied_count = self.manager.apply_operation_batch("episodic", batch)
        contents = {
            memory.content for memory in self.manager.get_all_by_type("episodic")
        }

        self.assertEqual(2, applied_count)
        self.assertEqual({"新内容", "新增内容"}, contents)

    def test_invalid_target_does_not_partially_apply(self):
        before = {
            memory.id: memory.content
            for memory in self.manager.get_all_by_type("episodic")
        }
        batch = MemoryOperationBatch.model_validate({
            "operations": [
                {
                    "operation": "ADD",
                    "content": "不应提交",
                },
                {
                    "operation": "UPDATE",
                    "target_id": "missing-id",
                    "content": "无效更新",
                },
            ]
        })

        with self.assertRaises(ValueError):
            self.manager.apply_operation_batch("episodic", batch)

        after = {
            memory.id: memory.content
            for memory in self.manager.get_all_by_type("episodic")
        }
        self.assertEqual(before, after)

    def test_rapid_adds_use_distinct_ids(self):
        self.manager.add("episodic", "第二条", "user")
        self.manager.add("episodic", "第三条", "user")

        ids = {
            memory.id for memory in self.manager.get_all_by_type("episodic")
        }
        self.assertEqual(3, len(ids))


if __name__ == "__main__":
    unittest.main()
