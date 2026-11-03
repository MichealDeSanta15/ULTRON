from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from vision.config import Settings
from vision.runtime import VisionRuntime


class VisionRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.runtime = VisionRuntime(Settings(data_dir=Path(self.temp_dir.name)))

    def tearDown(self) -> None:
        self.runtime.close()
        self.temp_dir.cleanup()

    def wait_for(self, task_id: str) -> dict:
        for _ in range(100):
            task = self.runtime.store.get_task(task_id)
            if task and task["status"] in {"completed", "failed", "cancelled", "awaiting_approval"}:
                return task
            time.sleep(0.02)
        self.fail("task did not reach a terminal state")

    def test_routes_and_completes_coding_request(self) -> None:
        task = self.runtime.create_task("Inspect this repository and explain how to run its tests")
        result = self.wait_for(task.id)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["route"], "coding")
        self.assertTrue(result["subtasks"])
        self.assertIn("Coding Agent", result["result"])

    def test_high_risk_request_requires_approval(self) -> None:
        task = self.runtime.create_task("Delete the old build artifacts")
        result = self.wait_for(task.id)
        self.assertEqual(result["status"], "awaiting_approval")
        approved = self.runtime.approve_task(task.id)
        self.assertEqual(approved["status"], "queued")
        result = self.wait_for(task.id)
        self.assertEqual(result["status"], "completed")

    def test_memory_round_trip(self) -> None:
        saved = self.runtime.store.add_memory("preference", "Use concise reports")
        memories = self.runtime.store.search_memories("concise")
        self.assertEqual(memories[0]["id"], saved["id"])


if __name__ == "__main__":
    unittest.main()
