# Test Suite for Localhost 127.0.0.1 Approval Server

import json
import os
import re
import shutil
import tempfile
import unittest
import urllib.request
import urllib.error
from pathlib import Path

import sys
sys.path.insert(0, os.path.abspath("plugins/chatgpt-codex-bridge/bridge"))

from controller.session import SessionStore, STATUS_PENDING, STATUS_AUTHORIZED_IDLE, STATUS_REVOKED
from controller.workspace_lock import WorkspaceLockManager
from controller.approval_server import ApprovalServer
from controller.adapters.mock_adapter import MockExecutorAdapter


class ApprovalServerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="approval-test-"))
        self.workspace = self.temp_dir / "workspace"
        self.workspace.mkdir()

        self.session_store = SessionStore(str(self.temp_dir))
        self.lock_mgr = WorkspaceLockManager()
        self.mock_adapter = MockExecutorAdapter()

        # Direct connection without system proxy
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        # Dynamic port to prevent collision
        self.server = ApprovalServer(
            session_store=self.session_store,
            workspace_lock_mgr=self.lock_mgr,
            adapter_registry={"mock": self.mock_adapter},
            port=0,
        )
        self.base_url = self.server.start()

    def tearDown(self):
        self.server.stop()
        shutil.rmtree(str(self.temp_dir), ignore_errors=True)

    def _extract_csrf_token(self, html):
        match = re.search(r'CSRF_TOKEN\s*=\s*"([a-f0-9]+)"', html)
        if match:
            return match.group(1)
        return ""

    def test_get_page_renders_without_side_effects(self):
        """GET / renders HTML and does not alter any session state."""
        session = self.session_store.prepare_session("mock", str(self.workspace), "build", "Initial")
        self.assertEqual(session.status, STATUS_PENDING)

        req = urllib.request.Request(self.base_url)
        with self.opener.open(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode("utf-8")
            self.assertIn("Executor Controller", html)
            self.assertIn(session.session_id, html)
            token = self._extract_csrf_token(html)
            self.assertTrue(len(token) > 10)

        # Re-check state: MUST still be pending!
        reloaded = self.session_store.get_session(session.session_id)
        self.assertEqual(reloaded.status, STATUS_PENDING)

    def test_post_without_csrf_token_rejected(self):
        """POST /api/sessions/<id>/approve without CSRF token is rejected with 403."""
        session = self.session_store.prepare_session("mock", str(self.workspace), "build", "Initial")
        url = f"{self.base_url}api/sessions/{session.session_id}/approve"

        req = urllib.request.Request(
            url,
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.opener.open(req, timeout=5)
        self.assertEqual(ctx.exception.code, 403)

        # State remains pending
        reloaded = self.session_store.get_session(session.session_id)
        self.assertEqual(reloaded.status, STATUS_PENDING)

    def test_post_with_valid_csrf_approves_session(self):
        """POST with valid CSRF token successfully approves session to AUTHORIZED_IDLE."""
        session = self.session_store.prepare_session("mock", str(self.workspace), "build", "Initial")

        # Get CSRF token from page
        with self.opener.open(self.base_url, timeout=5) as resp:
            html = resp.read().decode("utf-8")
            csrf_token = self._extract_csrf_token(html)

        url = f"{self.base_url}api/sessions/{session.session_id}/approve"
        payload = json.dumps({"csrf_token": csrf_token}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-CSRF-Token": csrf_token,
            },
            method="POST",
        )
        with self.opener.open(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["action"], "approved")

        reloaded = self.session_store.get_session(session.session_id)
        self.assertEqual(reloaded.status, STATUS_AUTHORIZED_IDLE)

    def test_post_revoke_session(self):
        """POST /api/sessions/<id>/revoke transitions session to REVOKED."""
        session = self.session_store.prepare_session("mock", str(self.workspace), "build", "Initial")
        self.session_store.allow_session(session.session_id)

        with self.opener.open(self.base_url, timeout=5) as resp:
            csrf_token = self._extract_csrf_token(resp.read().decode("utf-8"))

        url = f"{self.base_url}api/sessions/{session.session_id}/revoke"
        req = urllib.request.Request(
            url,
            data=json.dumps({"csrf_token": csrf_token}).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-CSRF-Token": csrf_token},
            method="POST",
        )
        with self.opener.open(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["action"], "revoked")

        reloaded = self.session_store.get_session(session.session_id)
        self.assertEqual(reloaded.status, STATUS_REVOKED)


if __name__ == "__main__":
    unittest.main()
