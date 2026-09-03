# Test Suite for P0: Codex Legacy Session Gate Enforcement

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, os.path.abspath("plugins/chatgpt-codex-bridge/bridge"))

from controller.capability import CapabilityCodec, capability_context
from controller.session import SessionStore, STATUS_PENDING, STATUS_AUTHORIZED_IDLE
from controller.codex_gate import CodexSessionGate, LEGACY_START_TOOLS


class DummyApprovalServer:
    def get_url(self):
        return "http://127.0.0.1:18230/"


class CodexSessionGateTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="codex-gate-test-"))
        self.workspace = self.temp_dir / "project"
        self.workspace.mkdir()

        self.key_path = self.temp_dir / "cap.key"
        self.codec = CapabilityCodec(str(self.key_path), context=capability_context(str(self.workspace)))
        self.session_store = SessionStore(str(self.temp_dir))
        self.approval_server = DummyApprovalServer()

        self.gate = CodexSessionGate(
            session_store=self.session_store,
            capability_codec=self.codec,
            approval_server=self.approval_server,
            default_workspace=str(self.workspace),
        )

    def tearDown(self):
        shutil.rmtree(str(self.temp_dir), ignore_errors=True)

    def test_p0_legacy_tools_strictly_blocked_without_authorized_session(self):
        """P0: All execution-starting legacy tools are strictly blocked without an authorized session."""
        for tool in LEGACY_START_TOOLS:
            allowed, resp = self.gate.check_or_gate(
                tool_name=tool,
                arguments={"prompt": f"Test prompt for {tool}"},
                workspace=str(self.workspace),
            )
            self.assertFalse(allowed, f"{tool} was erroneously allowed without an authorized session!")
            self.assertEqual(resp["status"], STATUS_PENDING)
            self.assertEqual(resp["error"], "approval_required")
            self.assertIn("session_request_id", resp)
            self.assertIn("approval_url", resp)
            self.assertEqual(resp["executor"], "codex")

    def test_p0_legacy_tools_allowed_when_session_is_authorized(self):
        """P0: Once a Codex session is authorized for the workspace, legacy tools execute with 0 extra approvals."""
        # 1. First invocation blocked
        allowed, resp = self.gate.check_or_gate(
            tool_name="codex-start",
            arguments={"prompt": "Initial task"},
            workspace=str(self.workspace),
        )
        self.assertFalse(allowed)
        session_id = self.codec.decode("session-request", resp["session_request_id"])

        # 2. Local user approves the session
        self.session_store.allow_session(session_id)

        # 3. Subsequent invocations in the authorized session pass through
        allowed_now, session = self.gate.check_or_gate(
            tool_name="codex-start",
            arguments={"prompt": "Next task"},
            workspace=str(self.workspace),
        )
        self.assertTrue(allowed_now)
        self.assertIsNotNone(session)
        self.assertEqual(session.session_id, session_id)
        self.assertEqual(session.status, STATUS_AUTHORIZED_IDLE)

    def test_p0_read_only_tools_pass_without_gate(self):
        """Read-only and control tools do not require session gate intervention."""
        for tool in ("codex-wait", "codex-job-status", "codex-job-steer", "codex-job-cancel", "codex-model-list"):
            allowed, resp = self.gate.check_or_gate(
                tool_name=tool,
                arguments={"jobId": "some-job"},
                workspace=str(self.workspace),
            )
            self.assertTrue(allowed)
            self.assertIsNone(resp)


if __name__ == "__main__":
    unittest.main()
