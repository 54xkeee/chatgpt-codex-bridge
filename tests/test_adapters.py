# Test Suite for Executor Adapters (Mock, Codex, Pi, Antigravity)

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, os.path.abspath("plugins/chatgpt-codex-bridge/bridge"))

from controller.session import ExecutorSession
from controller.adapters.mock_adapter import MockExecutorAdapter
from controller.adapters.codex_adapter import CodexExecutorAdapter
from controller.adapters.pi_adapter import PiExecutorAdapter
from controller.adapters.antigravity_adapter import AntigravityExecutorAdapter


class AdaptersTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="adapters-test-"))
        self.workspace = self.temp_dir / "workspace"
        self.workspace.mkdir()
        self.session = ExecutorSession(
            session_id="test-session-1234",
            executor="mock",
            workspace=str(self.workspace),
            permission_profile="build",
            display_objective="Adapter verification",
        )

    def tearDown(self):
        shutil.rmtree(str(self.temp_dir), ignore_errors=True)

    def test_mock_adapter_lifecycle(self):
        adapter = MockExecutorAdapter()
        detect = adapter.detect()
        self.assertTrue(detect["installed"])
        self.assertTrue(detect["capabilities"]["steer"])

        # Start turn
        turn = adapter.start_turn(self.session, "job-1", {"objective": "Test"})
        self.assertEqual(turn["status"], "started")

        # Steer
        steered = adapter.steer("job-1", "Steer instruction")
        self.assertTrue(steered)

        # Events
        events = adapter.poll_events("job-1", after_index=0)
        self.assertTrue(len(events) >= 5)
        event_types = [e["type"] for e in events]
        self.assertIn("steer.accepted", event_types)

        # Cancel
        cancelled = adapter.cancel("job-1")
        self.assertTrue(cancelled)

        # Result
        res = adapter.get_result("job-1")
        self.assertEqual(res["outcome"], "cancelled")

    def test_codex_adapter_detection(self):
        adapter = CodexExecutorAdapter(job_state_dir=str(self.temp_dir / "jobs"))
        detect = adapter.detect()
        self.assertEqual(detect["id"], "codex")
        self.assertIn("capabilities", detect)
        self.assertTrue(detect["capabilities"]["steer"])
        self.assertTrue(detect["capabilities"]["cancel"])

        # Native session creation
        native_thread = adapter.create_native_session(self.session)
        self.assertTrue(len(native_thread) > 10)

    def test_pi_adapter_detection(self):
        adapter = PiExecutorAdapter()
        detect = adapter.detect()
        self.assertEqual(detect["id"], "pi")
        self.assertTrue(detect["installed"])
        self.assertIn("0.84", detect["version"])
        self.assertTrue(detect["capabilities"]["mode_rpc"])
        self.assertTrue(detect["capabilities"]["steer"])
        self.assertTrue(detect["capabilities"]["cancel"])

        # Native session creation & turn lifecycle
        native_id = adapter.create_native_session(self.session)
        self.assertIn("pi-session-", native_id)

        turn = adapter.start_turn(self.session, "pi-job-1", {"objective": "Pi turn"})
        self.assertEqual(turn["status"], "started")

        steered = adapter.steer("pi-job-1", "Pi steer")
        self.assertTrue(steered)

        events = adapter.poll_events("pi-job-1")
        self.assertTrue(len(events) >= 2)

        res = adapter.get_result("pi-job-1")
        self.assertEqual(res["outcome"], "completed")

    def test_antigravity_adapter_detection(self):
        adapter = AntigravityExecutorAdapter()
        detect = adapter.detect()
        self.assertEqual(detect["id"], "antigravity")
        self.assertTrue(detect["installed"])
        self.assertEqual(detect["version"], "1.1.22")
        self.assertTrue(detect["capabilities"]["headless_stream_json"])
        self.assertTrue(detect["capabilities"]["conversation_resume"])
        self.assertTrue(detect["capabilities"]["dangerously_skip_permissions"])

        # Turn lifecycle
        turn = adapter.start_turn(self.session, "agy-job-1", {"objective": "Agy turn"})
        self.assertEqual(turn["status"], "started")

        cancelled = adapter.cancel("agy-job-1")
        self.assertTrue(cancelled)

        res = adapter.get_result("agy-job-1")
        self.assertEqual(res["outcome"], "cancelled")


if __name__ == "__main__":
    unittest.main()
