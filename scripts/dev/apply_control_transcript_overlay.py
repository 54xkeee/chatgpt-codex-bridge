#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/bridge/codex-mcp-guard.py"
MIRROR = ROOT / "plugins/chatgpt-codex-bridge/bridge/codex-mcp-guard.py"
TESTS = ROOT / "tests/bridge/test-codex-mcp-guard.py"
DESIGN = ROOT / "docs/specs/job-control-transcript-handoff/design.md"


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


text = SOURCE.read_text(encoding="utf-8")

anchor = '''    def steer(self, job_id, prompt):\n'''
method = '''    def _overlay_control_transcript(self, path, state):\n        control_path = path / "controls.json"\n        if control_path.is_symlink():\n            raise GuardProtocolError("invalid job control state")\n        if not control_path.is_file():\n            return state\n        existing_ids = {\n            entry.get("controlId")\n            for entry in state.get("transcript", [])\n            if isinstance(entry, dict) and isinstance(entry.get("controlId"), str)\n        }\n        for command in read_controls(path):\n            if not isinstance(command, dict):\n                raise GuardProtocolError("invalid job control state")\n            control_id = command.get("id")\n            kind = command.get("kind")\n            if not isinstance(control_id, str) or not control_id or control_id in existing_ids:\n                continue\n            if kind == "steer":\n                value = command.get("prompt")\n            elif kind == "cancel":\n                value = command.get("reason")\n            else:\n                raise GuardProtocolError("invalid job control command")\n            if not isinstance(value, str):\n                raise GuardProtocolError("invalid job control command")\n            append_transcript(\n                state, "controller", kind, value, command.get("createdAt"),\n                "queued", control_id\n            )\n            existing_ids.add(control_id)\n        return state\n\n'''
text = replace_once(text, anchor, method + anchor, "control transcript overlay method")

text = replace_once(
    text,
    '''        state = self._state_for_path(path)\n        if state.get("jobId") != job_id:\n            raise GuardProtocolError("invalid job state")\n        return state\n\n    def list(self, status=None):\n''',
    '''        state = self._state_for_path(path)\n        if state.get("jobId") != job_id:\n            raise GuardProtocolError("invalid job state")\n        return self._overlay_control_transcript(path, state)\n\n    def list(self, status=None):\n''',
    "read overlay",
)

text = replace_once(
    text,
    '''            try:\n                state = self._state_for_path(path)\n            except GuardProtocolError:\n                continue\n            if status is None or state.get("status") == status:\n                states.append(public_job_state(state))\n''',
    '''            try:\n                state = self._overlay_control_transcript(\n                    path, self._state_for_path(path)\n                )\n            except GuardProtocolError:\n                continue\n            if status is None or state.get("status") == status:\n                states.append(public_job_state(state))\n''',
    "list overlay",
)

text = replace_once(
    text,
    '''            self._append_control_locked(path, state, "steer", prompt)\n            return self._state_for_path(path, reconcile=False)\n''',
    '''            self._append_control_locked(path, state, "steer", prompt)\n            return self._overlay_control_transcript(\n                path, self._state_for_path(path, reconcile=False)\n            )\n''',
    "steer immediate overlay",
)

text = replace_once(
    text,
    '''            if state.get("status") in TERMINAL_JOB_STATUSES:\n                return state\n''',
    '''            if state.get("status") in TERMINAL_JOB_STATUSES:\n                return self._overlay_control_transcript(path, state)\n''',
    "terminal cancel overlay",
)

text = replace_once(
    text,
    '''                state = self._state_for_path(path, reconcile=False)\n            return state\n        deadline = time.monotonic() + JOB_CANCEL_GRACE_SECONDS\n''',
    '''                state = self._state_for_path(path, reconcile=False)\n            return self._overlay_control_transcript(path, state)\n        deadline = time.monotonic() + JOB_CANCEL_GRACE_SECONDS\n''',
    "queued cancel overlay",
)

text = replace_once(
    text,
    '''            state = self._state_for_path(path, reconcile=False)\n        return state\n\n    def wait(self, job_id, timeout_seconds):\n''',
    '''            state = self._state_for_path(path, reconcile=False)\n        return self._overlay_control_transcript(path, state)\n\n    def wait(self, job_id, timeout_seconds):\n''',
    "running cancel overlay",
)

SOURCE.write_text(text, encoding="utf-8")
MIRROR.write_text(text, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
old_assert = '''        self.assertEqual(cancelled["nextAction"], "continue")\n        self.assertIn("threadId", cancelled)\n\n        durable = json.loads(status_path.read_text(encoding="utf-8"))\n'''
new_assert = '''        self.assertEqual(cancelled["nextAction"], "continue")\n        self.assertIn("threadId", cancelled)\n        cancel_entries = [\n            entry for entry in cancelled["transcript"]\n            if entry.get("kind") == "cancel"\n        ]\n        self.assertEqual([entry["text"] for entry in cancel_entries], ["user requested takeover"])\n\n        durable = json.loads(status_path.read_text(encoding="utf-8"))\n'''
tests = replace_once(tests, old_assert, new_assert, "cancel transcript assertion")

insert_at = tests.index('\n    def test_running_cancel_falls_back_to_verified_worker_and_is_idempotent')
steer_test = r'''

    def test_running_steer_is_immediately_visible_in_public_transcript(self):
        harness = self.harness(scenario="async_block", job_max_seconds=60)
        harness.initialize()
        queued = harness.call(3, "codex-run", {"prompt": "steer blocked turn"})
        job_id = queued["result"]["structuredContent"]["jobId"]
        status_path = harness.job_dir_for(job_id) / "status.json"
        deadline = time.time() + 3.0
        state = {}
        while time.time() < deadline:
            state = json.loads(status_path.read_text(encoding="utf-8"))
            if state.get("status") == "running" and state.get("internalTurnId"):
                break
            time.sleep(0.02)
        self.assertEqual(state.get("status"), "running")

        steered = harness.call(4, "codex-job-steer", {
            "jobId": job_id,
            "prompt": "change direction immediately",
        })["result"]["structuredContent"]
        steer_entries = [
            entry for entry in steered["transcript"]
            if entry.get("kind") == "steer"
        ]
        self.assertEqual([entry["text"] for entry in steer_entries], ["change direction immediately"])
        self.assertIn(steer_entries[0]["delivery"], ("queued", "sent"))
        harness.call(5, "codex-job-cancel", {"jobId": job_id, "reason": "cleanup"})
'''
tests = tests[:insert_at] + steer_test + tests[insert_at:]
TESTS.write_text(tests, encoding="utf-8")

design = DESIGN.read_text(encoding="utf-8")
design = replace_once(
    design,
    "During an active job, the controller writes only the control mailbox. The worker remains the single writer of running `status.json` and records the corresponding public transcript entry when it sends the control to App Server. This avoids controller/worker lost-update races.\n",
    "During an active job, the controller writes only the control mailbox. The worker remains the single writer of running `status.json` and records the corresponding public transcript entry when it sends the control to App Server. Read/status projection overlays any still-pending mailbox entries in memory, without persisting them back to running state. This avoids controller/worker lost-update races while making the audit view immediately complete.\n",
    "design overlay explanation",
)
DESIGN.write_text(design, encoding="utf-8")
