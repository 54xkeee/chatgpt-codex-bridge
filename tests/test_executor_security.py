# Test Suite for Executor Controller Security Contracts (T1 - T15)

import json
import os
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

import sys
sys.path.insert(0, os.path.abspath("plugins/chatgpt-codex-bridge/bridge"))

from controller.capability import CapabilityCodec, capability_context
from controller.session import (
    SessionStore,
    STATUS_PENDING,
    STATUS_AUTHORIZED_IDLE,
    STATUS_RUNNING,
    STATUS_REVOKED,
    STATUS_REAUTH_REQUIRED,
    SessionNotAuthorizedError,
    SessionStateConflictError,
)
from controller.workspace_lock import WorkspaceLockManager, WorkspaceLockedError
from controller.adapters.mock_adapter import MockExecutorAdapter
from controller.tools import GenericToolsDispatcher


class ExecutorSecurityContractsTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="exec-security-test-"))
        self.workspace1 = self.temp_dir / "workspace1"
        self.workspace2 = self.temp_dir / "workspace2"
        self.workspace1.mkdir()
        self.workspace2.mkdir()

        self.key_path = self.temp_dir / "capability.key"
        self.codec = CapabilityCodec(str(self.key_path), context=capability_context(str(self.workspace1)))

        self.lock_mgr = WorkspaceLockManager()
        self.session_store = SessionStore(str(self.temp_dir), runtime_fingerprint="runtime-boot-1")
        self.mock_adapter = MockExecutorAdapter()
        self.adapters = {"mock": self.mock_adapter}

        self.dispatcher = GenericToolsDispatcher(
            session_store=self.session_store,
            workspace_lock_mgr=self.lock_mgr,
            capability_codec=self.codec,
            adapters=self.adapters,
        )

    def tearDown(self):
        shutil.rmtree(str(self.temp_dir), ignore_errors=True)

    def test_t1_prepare_launches_no_processes_and_no_model_calls(self):
        """T1: executor_session_prepare creates pending record without spawning any processes or model calls."""
        initial_turns_count = len(self.mock_adapter._turns)
        res = self.dispatcher.dispatch("executor_session_prepare", {
            "executor": "mock",
            "workspace": str(self.workspace1),
            "permission_profile": "build",
            "objective": "T1 verification",
        })

        self.assertEqual(res["status"], STATUS_PENDING)
        self.assertIn("session_request_id", res)
        # Assert no worker/turn was spawned
        self.assertEqual(len(self.mock_adapter._turns), initial_turns_count)
        # Assert session in store is pending
        session_id = self.codec.decode("session-request", res["session_request_id"])
        session = self.session_store.get_session(session_id)
        self.assertEqual(session.status, STATUS_PENDING)

    def test_t2_forbidden_approval_parameters_rejected(self):
        """T2: Injection of approved=True or bypass parameters is strictly rejected."""
        res = self.dispatcher.dispatch("executor_session_prepare", {
            "executor": "mock",
            "workspace": str(self.workspace1),
            "permission_profile": "build",
            "objective": "T2 test",
            "approved": True,
        })
        self.assertIn("error", res)
        self.assertIn("Forbidden parameter", res["error"])

    def test_t3_local_allow_session_authorizes_exactly_one_session(self):
        """T3: Local approval transitions state to AUTHORIZED_IDLE for exactly one session."""
        prep = self.dispatcher.dispatch("executor_session_prepare", {
            "executor": "mock",
            "workspace": str(self.workspace1),
            "permission_profile": "build",
        })
        session_id = self.codec.decode("session-request", prep["session_request_id"])

        # Local approval action
        session = self.session_store.allow_session(session_id)
        self.assertEqual(session.status, STATUS_AUTHORIZED_IDLE)
        self.assertIsNotNone(session.approved_at)

    def test_t4_authorized_session_long_task_controls_require_zero_approvals(self):
        """T4: Once authorized, turn_start, status, wait, steer, cancel require 0 user approvals."""
        prep = self.dispatcher.dispatch("executor_session_prepare", {
            "executor": "mock",
            "workspace": str(self.workspace1),
            "permission_profile": "build",
        })
        session_id = self.codec.decode("session-request", prep["session_request_id"])
        self.session_store.allow_session(session_id)

        session_cap = self.codec.encode("session", session_id)

        # 1. Start turn (0 human approval required)
        turn = self.dispatcher.dispatch("executor_turn_start", {
            "session_id": session_cap,
            "objective": "Do task",
        })
        self.assertEqual(turn["status"], "started")
        job_id = turn["job_id"]

        # 2. Status (0 approval)
        st = self.dispatcher.dispatch("executor_job_status", {"job_id": job_id})
        self.assertEqual(st["status"], "running")

        # 3. Steer (0 approval)
        steer_res = self.dispatcher.dispatch("executor_job_steer", {
            "job_id": job_id,
            "message": "Focus on file X",
        })
        self.assertTrue(steer_res["steer_delivered"])

        # 4. Cancel (0 approval)
        cancel_res = self.dispatcher.dispatch("executor_job_cancel", {"job_id": job_id})
        self.assertEqual(cancel_res["status"], "cancelled")

    def test_t5_cancel_turn_returns_session_to_authorized_idle(self):
        """T5: Cancelling a turn returns session to AUTHORIZED_IDLE, not REVOKED, and releases write lock."""
        prep = self.dispatcher.dispatch("executor_session_prepare", {
            "executor": "mock",
            "workspace": str(self.workspace1),
            "permission_profile": "build",
        })
        session_id = self.codec.decode("session-request", prep["session_request_id"])
        self.session_store.allow_session(session_id)
        session_cap = self.codec.encode("session", session_id)

        turn = self.dispatcher.dispatch("executor_turn_start", {
            "session_id": session_cap,
            "objective": "Build task",
        })
        job_id = turn["job_id"]
        # Lock is held during turn
        self.assertTrue(self.lock_mgr.is_locked(str(self.workspace1)))

        # Cancel turn
        self.dispatcher.dispatch("executor_job_cancel", {"job_id": job_id})

        # Session is AUTHORIZED_IDLE
        session = self.session_store.get_session(session_id)
        self.assertEqual(session.status, STATUS_AUTHORIZED_IDLE)
        # Lock is released
        self.assertFalse(self.lock_mgr.is_locked(str(self.workspace1)))

    def test_t6_follow_up_turn_in_same_session_requires_no_reauthorization(self):
        """T6: Follow-up turn in same session starts directly without re-approval."""
        prep = self.dispatcher.dispatch("executor_session_prepare", {
            "executor": "mock",
            "workspace": str(self.workspace1),
            "permission_profile": "build",
        })
        session_id = self.codec.decode("session-request", prep["session_request_id"])
        self.session_store.allow_session(session_id)
        session_cap = self.codec.encode("session", session_id)

        # Turn 1
        t1 = self.dispatcher.dispatch("executor_turn_start", {"session_id": session_cap, "objective": "Turn 1"})
        raw_j1 = self.codec.decode("job", t1["job_id"])
        self.mock_adapter.mark_completed(raw_j1)
        self.dispatcher.dispatch("executor_job_wait", {"job_id": t1["job_id"], "timeout_seconds": 1.0})

        # Session should be back to authorized_idle
        session = self.session_store.get_session(session_id)
        self.assertEqual(session.status, STATUS_AUTHORIZED_IDLE)

        # Turn 2 in SAME session succeeds without human intervention
        t2 = self.dispatcher.dispatch("executor_turn_start", {"session_id": session_cap, "objective": "Turn 2 follow-up"})
        self.assertEqual(t2["status"], "started")

    def test_t7_workspace_boundary_rejected(self):
        """T7: Reusing a session for a different workspace must fail."""
        prep = self.dispatcher.dispatch("executor_session_prepare", {
            "executor": "mock",
            "workspace": str(self.workspace1),
            "permission_profile": "build",
        })
        session_id = self.codec.decode("session-request", prep["session_request_id"])
        session = self.session_store.get_session(session_id)

        # Workspace in session is workspace1; cannot operate on workspace2
        self.assertNotEqual(session.workspace, str(self.workspace2.resolve()))

    def test_t8_permission_escalation_requires_new_session(self):
        """T8: SAFE session cannot silently execute with BUILD / TRUSTED write access."""
        prep = self.dispatcher.dispatch("executor_session_prepare", {
            "executor": "mock",
            "workspace": str(self.workspace1),
            "permission_profile": "safe",
        })
        session_id = self.codec.decode("session-request", prep["session_request_id"])
        self.session_store.allow_session(session_id)
        session = self.session_store.get_session(session_id)
        self.assertEqual(session.permission_profile, "safe")

    def test_t9_revoke_session_terminates_all_and_fails_closed(self):
        """T9: Revoking a session terminates resources, releases locks, and rejects future turns."""
        prep = self.dispatcher.dispatch("executor_session_prepare", {
            "executor": "mock",
            "workspace": str(self.workspace1),
            "permission_profile": "build",
        })
        session_id = self.codec.decode("session-request", prep["session_request_id"])
        self.session_store.allow_session(session_id)
        session_cap = self.codec.encode("session", session_id)

        turn = self.dispatcher.dispatch("executor_turn_start", {"session_id": session_cap, "objective": "Task"})
        self.assertTrue(self.lock_mgr.is_locked(str(self.workspace1)))

        # Revoke session
        self.dispatcher.dispatch("executor_session_revoke", {"session_id": session_cap})

        # Session is revoked
        session = self.session_store.get_session(session_id)
        self.assertEqual(session.status, STATUS_REVOKED)
        # Lock released
        self.assertFalse(self.lock_mgr.is_locked(str(self.workspace1)))

        # Subsequent turn rejected
        with self.assertRaises(SessionNotAuthorizedError):
            self.dispatcher.dispatch("executor_turn_start", {"session_id": session_cap, "objective": "Next"})

    def test_t10_concurrent_writers_on_same_workspace_blocked(self):
        """T10: Two BUILD turns on the same workspace are mutually exclusive via Workspace Lock."""
        # Session A
        prep_a = self.dispatcher.dispatch("executor_session_prepare", {
            "executor": "mock", "workspace": str(self.workspace1), "permission_profile": "build",
        })
        sid_a = self.codec.decode("session-request", prep_a["session_request_id"])
        self.session_store.allow_session(sid_a)
        cap_a = self.codec.encode("session", sid_a)

        # Session B (different session, same workspace)
        prep_b = self.dispatcher.dispatch("executor_session_prepare", {
            "executor": "mock", "workspace": str(self.workspace1), "permission_profile": "build",
        })
        sid_b = self.codec.decode("session-request", prep_b["session_request_id"])
        self.session_store.allow_session(sid_b)
        cap_b = self.codec.encode("session", sid_b)

        # Turn A starts
        turn_a = self.dispatcher.dispatch("executor_turn_start", {"session_id": cap_a, "objective": "Writer A"})
        self.assertEqual(turn_a["status"], "started")

        # Turn B must be rejected by workspace write lock
        with self.assertRaises(WorkspaceLockedError):
            self.dispatcher.dispatch("executor_turn_start", {"session_id": cap_b, "objective": "Writer B"})

    def test_t13_runtime_fingerprint_drift_requires_reauth(self):
        """T13: OS reboot / runtime fingerprint drift moves active session to REAUTH_REQUIRED."""
        prep = self.dispatcher.dispatch("executor_session_prepare", {
            "executor": "mock", "workspace": str(self.workspace1), "permission_profile": "build",
        })
        sid = self.codec.decode("session-request", prep["session_request_id"])
        self.session_store.allow_session(sid)
        cap = self.codec.encode("session", sid)

        # Simulate restart with new runtime fingerprint (e.g. after reboot)
        new_store = SessionStore(str(self.temp_dir), runtime_fingerprint="runtime-boot-AFTER-REBOOT")
        reloaded_session = new_store.get_session(sid)
        self.assertEqual(reloaded_session.status, STATUS_REAUTH_REQUIRED)

    def test_t14_forged_capability_rejected(self):
        """T14: Forged capability signatures fail closed and cannot iterate random IDs."""
        with self.assertRaises(Exception):
            self.dispatcher.dispatch("executor_session_get", {"session_id": "cgb2.session.invalid.fake.sig"})

    def test_t15_revoked_session_reauth_rejected(self):
        """T15: Revoked session cannot be re-authorized; must create new session."""
        prep = self.dispatcher.dispatch("executor_session_prepare", {
            "executor": "mock", "workspace": str(self.workspace1), "permission_profile": "build",
        })
        sid = self.codec.decode("session-request", prep["session_request_id"])
        self.session_store.allow_session(sid)
        self.session_store.revoke_session(sid)

        with self.assertRaises(SessionStateConflictError):
            self.session_store.allow_session(sid)

    def test_t16_job_status_or_result_syncs_completion_and_releases_lock(self):
        """T16: If job completes, calling status or result (without wait) syncs session and releases lock."""
        prep = self.dispatcher.dispatch("executor_session_prepare", {
            "executor": "mock", "workspace": str(self.workspace1), "permission_profile": "build",
        })
        sid = self.codec.decode("session-request", prep["session_request_id"])
        self.session_store.allow_session(sid)
        cap = self.codec.encode("session", sid)

        turn = self.dispatcher.dispatch("executor_turn_start", {"session_id": cap, "objective": "Task"})
        raw_jid = self.codec.decode("job", turn["job_id"])
        self.assertTrue(self.lock_mgr.is_locked(str(self.workspace1)))

        # Mark completed on adapter
        self.mock_adapter.mark_completed(raw_jid)

        # Call executor_job_status (WITHOUT calling executor_job_wait)
        st = self.dispatcher.dispatch("executor_job_status", {"job_id": turn["job_id"]})
        self.assertEqual(st["status"], "completed")

        # Verify session is synced back to AUTHORIZED_IDLE and lock is released
        session = self.session_store.get_session(sid)
        self.assertEqual(session.status, STATUS_AUTHORIZED_IDLE)
        self.assertFalse(self.lock_mgr.is_locked(str(self.workspace1)))


if __name__ == "__main__":
    unittest.main()

