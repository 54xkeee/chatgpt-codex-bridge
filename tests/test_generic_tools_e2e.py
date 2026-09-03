# End-to-End Simulation of Generic Executor MCP Tools (ChatGPT Supervisory Loop)

import json
import os
import shutil
import tempfile
import unittest
import urllib.request
from pathlib import Path

import sys
sys.path.insert(0, os.path.abspath("plugins/chatgpt-codex-bridge/bridge"))

from controller.capability import CapabilityCodec, capability_context
from controller.session import SessionStore, STATUS_PENDING, STATUS_AUTHORIZED_IDLE, STATUS_RUNNING, STATUS_REVOKED
from controller.workspace_lock import WorkspaceLockManager
from controller.approval_server import ApprovalServer
from controller.adapters.mock_adapter import MockExecutorAdapter
from controller.adapters.codex_adapter import CodexExecutorAdapter
from controller.adapters.pi_adapter import PiExecutorAdapter
from controller.adapters.antigravity_adapter import AntigravityExecutorAdapter
from controller.tools import GenericToolsDispatcher, get_generic_tools_schema


class GenericToolsE2ETest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="e2e-tools-test-"))
        self.workspace = self.temp_dir / "workspace"
        self.workspace.mkdir()

        self.key_path = self.temp_dir / "capability.key"
        self.codec = CapabilityCodec(str(self.key_path), context=capability_context(str(self.workspace)))

        self.lock_mgr = WorkspaceLockManager()
        self.session_store = SessionStore(str(self.temp_dir), runtime_fingerprint="runtime-e2e-1")
        self.mock_adapter = MockExecutorAdapter()
        self.adapters = {
            "mock": self.mock_adapter,
            "codex": CodexExecutorAdapter(),
            "pi": PiExecutorAdapter(),
            "antigravity": AntigravityExecutorAdapter(),
        }

        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.approval_server = ApprovalServer(
            session_store=self.session_store,
            workspace_lock_mgr=self.lock_mgr,
            adapter_registry=self.adapters,
            port=0,
        )
        self.base_url = self.approval_server.start()

        self.dispatcher = GenericToolsDispatcher(
            session_store=self.session_store,
            workspace_lock_mgr=self.lock_mgr,
            capability_codec=self.codec,
            adapters=self.adapters,
            approval_server=self.approval_server,
        )

    def tearDown(self):
        self.approval_server.stop()
        shutil.rmtree(str(self.temp_dir), ignore_errors=True)

    def test_full_chatgpt_supervision_loop_e2e(self):
        # 1. executor_list (read-only capability discovery)
        exec_list = self.dispatcher.dispatch("executor_list", {})
        exec_ids = [e["id"] for e in exec_list["executors"]]
        self.assertIn("mock", exec_ids)
        self.assertIn("codex", exec_ids)
        self.assertIn("pi", exec_ids)
        self.assertIn("antigravity", exec_ids)

        # 2. executor_session_prepare (ChatGPT prepares session, awaiting human approval)
        prep = self.dispatcher.dispatch("executor_session_prepare", {
            "executor": "mock",
            "workspace": str(self.workspace),
            "permission_profile": "build",
            "objective": "Refactor data module and verify regressions",
        })
        self.assertEqual(prep["status"], STATUS_PENDING)
        session_req_id = prep["session_request_id"]
        raw_session_id = self.codec.decode("session-request", session_req_id)

        # 3. executor_session_list & get
        sessions = self.dispatcher.dispatch("executor_session_list", {})
        self.assertTrue(len(sessions["sessions"]) >= 1)
        sess_detail = self.dispatcher.dispatch("executor_session_get", {"session_id": session_req_id})
        self.assertEqual(sess_detail["status"], STATUS_PENDING)

        # 4. Local Human visits Approval UI and clicks "Allow Session"
        with self.opener.open(self.base_url, timeout=5) as resp:
            html = resp.read().decode("utf-8")
            import re
            csrf_token = re.search(r'CSRF_TOKEN\s*=\s*"([a-f0-9]+)"', html).group(1)

        approve_req = urllib.request.Request(
            f"{self.base_url}api/sessions/{raw_session_id}/approve",
            data=json.dumps({"csrf_token": csrf_token}).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-CSRF-Token": csrf_token},
            method="POST",
        )
        with self.opener.open(approve_req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)

        # Session is now AUTHORIZED_IDLE
        session = self.session_store.get_session(raw_session_id)
        self.assertEqual(session.status, STATUS_AUTHORIZED_IDLE)
        session_cap = self.codec.encode("session", raw_session_id)

        # 5. executor_turn_start (Turn 1: Refactor) - ZERO extra human prompts!
        t1 = self.dispatcher.dispatch("executor_turn_start", {
            "session_id": session_cap,
            "objective": "Turn 1: Refactor module",
        })
        self.assertEqual(t1["status"], "started")
        job_id_1 = t1["job_id"]
        raw_job_id_1 = self.codec.decode("job", job_id_1)

        # Verify Workspace Write Lock is held by Turn 1
        self.assertTrue(self.lock_mgr.is_locked(str(self.workspace)))
        lock_info = self.lock_mgr.get_lock_info(str(self.workspace))
        self.assertEqual(lock_info["job_id"], raw_job_id_1)

        # 6. executor_job_status
        st1 = self.dispatcher.dispatch("executor_job_status", {"job_id": job_id_1})
        self.assertEqual(st1["status"], "running")

        # 7. executor_job_steer (ChatGPT steers running turn)
        steer_res = self.dispatcher.dispatch("executor_job_steer", {
            "job_id": job_id_1,
            "message": "Remember to keep backward compatibility",
        })
        self.assertTrue(steer_res["steer_delivered"])

        # 8. executor_job_events
        evs = self.dispatcher.dispatch("executor_job_events", {"job_id": job_id_1})
        self.assertTrue(len(evs["events"]) >= 5)

        # Complete Turn 1
        self.mock_adapter.mark_completed(raw_job_id_1, "Refactoring finished cleanly")
        wait_res = self.dispatcher.dispatch("executor_job_wait", {"job_id": job_id_1, "timeout_seconds": 1.0})
        self.assertEqual(wait_res["status"], "completed")

        # Result of Turn 1
        res1 = self.dispatcher.dispatch("executor_job_result", {"job_id": job_id_1})
        self.assertEqual(res1["outcome"], "completed")

        # Session is back to AUTHORIZED_IDLE & Write lock is released
        self.assertEqual(self.session_store.get_session(raw_session_id).status, STATUS_AUTHORIZED_IDLE)
        self.assertFalse(self.lock_mgr.is_locked(str(self.workspace)))

        # 9. executor_turn_start (Turn 2: Follow-up in SAME session) - ZERO human prompts!
        t2 = self.dispatcher.dispatch("executor_turn_start", {
            "session_id": session_cap,
            "objective": "Turn 2: Run verification tests",
        })
        self.assertEqual(t2["status"], "started")
        job_id_2 = t2["job_id"]

        # Cancel Turn 2
        cancel_res = self.dispatcher.dispatch("executor_job_cancel", {"job_id": job_id_2})
        self.assertEqual(cancel_res["status"], "cancelled")
        self.assertEqual(cancel_res["session_status"], STATUS_AUTHORIZED_IDLE)

        # 10. executor_session_revoke (ChatGPT or user revokes session)
        rev = self.dispatcher.dispatch("executor_session_revoke", {"session_id": session_cap})
        self.assertEqual(rev["status"], STATUS_REVOKED)
        self.assertEqual(self.session_store.get_session(raw_session_id).status, STATUS_REVOKED)


if __name__ == "__main__":
    unittest.main()
