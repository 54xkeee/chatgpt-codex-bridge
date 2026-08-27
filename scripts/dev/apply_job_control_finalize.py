#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/bridge/codex-mcp-guard.py"
MIRROR = ROOT / "plugins/chatgpt-codex-bridge/bridge/codex-mcp-guard.py"
TESTS = ROOT / "tests/bridge/test-codex-mcp-guard.py"


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


text = SOURCE.read_text(encoding="utf-8")

# Keep absolute local filesystem paths internal. The signed capability and project
# display name are enough for model-visible supervision and handoff.
text = replace_once(
    text,
    '        "workspace": {"type": "string"},\n        "projectName": {"type": "string"},\n',
    '        "projectName": {"type": "string"},\n',
    "public workspace schema",
)
text = replace_once(
    text,
    '    for key in ("workspace", "projectName"):\n        if isinstance(state.get(key), str):\n            public[key] = state[key]\n',
    '    if isinstance(state.get("projectName"), str):\n        public["projectName"] = state["projectName"]\n',
    "public workspace projection",
)

# A queued worker is already spawned before enqueue returns. Stop that verified
# worker first, then let the controller record the terminal state; this prevents
# a just-starting worker from overwriting an interrupted state.
old_cancel = '''            if state.get("status") == "queued":\n                message = reason or "Codex 后台任务已在启动前取消。"\n                append_transcript(state, "controller", "cancel", message, delivery="applied")\n                _mark_job_interrupted(path, state, message)\n                queued = True\n            else:\n                message = reason or "请求停止当前 Codex 后台任务。"\n                self._append_control_locked(path, state, "cancel", message)\n                queued = False\n        if queued:\n            terminate_verified_job_worker(path)\n            return self.read(job_id)\n'''
new_cancel = '''            if state.get("status") == "queued":\n                message = reason or "Codex 后台任务已在启动前取消。"\n                queued = True\n            else:\n                message = reason or "请求停止当前 Codex 后台任务。"\n                self._append_control_locked(path, state, "cancel", message)\n                queued = False\n        if queued:\n            terminate_verified_job_worker(path)\n            state = self._state_for_path(path, reconcile=False)\n            if state.get("status") in ACTIVE_JOB_STATUSES:\n                append_transcript(\n                    state, "controller", "cancel", message, delivery="applied"\n                )\n                _mark_job_interrupted(path, state, message)\n                state = self._state_for_path(path, reconcile=False)\n            return state\n'''
text = replace_once(text, old_cancel, new_cancel, "queued cancel race")

SOURCE.write_text(text, encoding="utf-8")
MIRROR.write_text(text, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")

# Update old controller-policy assertions. Durable jobs no longer force a tight
# foreground wait loop; they explicitly support status/steer/cancel/resume.
tests = replace_once(
    tests,
    '        self.assertIn("review this result", joined["result"]["content"][0]["text"])\n        self.assertIn("same threadId", joined["result"]["content"][0]["text"])\n',
    '        self.assertIn("Review this result", joined["result"]["content"][0]["text"])\n        self.assertIn("same-thread codex-reply-async", joined["result"]["content"][0]["text"])\n',
    "terminal wait policy assertions",
)
tests = replace_once(
    tests,
    '    def test_codex_wait_is_bounded_and_requires_another_wait_while_running(self):\n',
    '    def test_codex_wait_is_bounded_and_leaves_active_job_durable(self):\n',
    "wait test name",
)
tests = replace_once(
    tests,
    '        self.assertIn("MUST call codex-wait again", message)\n        self.assertIn(job_id, message)\n',
    '        self.assertIn("job remains durable", message)\n        self.assertIn("steer or cancel", message)\n        self.assertIn(job_id, message)\n',
    "active wait policy assertion",
)
tests = replace_once(
    tests,
    '        self.assertEqual(structured["status"], "queued")\n        self.assertIn(\n            "MUST call codex-wait",\n            queued["result"]["content"][0]["text"],\n        )\n        self.assertIn("_meta", queued["result"])\n',
    '        self.assertEqual(structured["status"], "queued")\n        self.assertIn(\n            "durable",\n            queued["result"]["content"][0]["text"],\n        )\n        self.assertIn(\n            "codex-job-status",\n            queued["result"]["content"][0]["text"],\n        )\n        self.assertIn("_meta", queued["result"])\n',
    "async start durable assertion",
)
tests = replace_once(
    tests,
    '        self.assertIn(\n            "MUST call codex-wait",\n            queued["result"]["content"][0]["text"],\n        )\n\n        malformed = self.harness(scenario="async_malformed")\n',
    '        self.assertIn(\n            "durable",\n            queued["result"]["content"][0]["text"],\n        )\n        self.assertIn(\n            "steer or cancel",\n            queued["result"]["content"][0]["text"],\n        )\n\n        malformed = self.harness(scenario="async_malformed")\n',
    "async reply durable assertion",
)

# The raw project path remains durable internal state but must never appear in
# model-visible job output. Existing tests enforce this exact property.

anchor = '\n\nif __name__ == "__main__":\n'
if anchor not in tests:
    raise SystemExit("test insertion anchor missing")
extra = r'''

    def test_running_cancel_falls_back_to_verified_worker_and_is_idempotent(self):
        harness = self.harness(scenario="async_block", job_max_seconds=60)
        harness.initialize()
        queued = harness.call(3, "codex-run", {"prompt": "cancel blocked turn"})
        job_id = queued["result"]["structuredContent"]["jobId"]
        job_dir = harness.job_dir_for(job_id)
        status_path = job_dir / "status.json"
        deadline = time.time() + 3.0
        state = {}
        while time.time() < deadline:
            state = json.loads(status_path.read_text(encoding="utf-8"))
            if state.get("status") == "running" and state.get("internalTurnId"):
                break
            time.sleep(0.02)
        self.assertEqual(state.get("status"), "running")
        self.assertTrue(state.get("internalTurnId"))

        cancelled = harness.call(4, "codex-job-cancel", {
            "jobId": job_id,
            "reason": "user requested takeover",
        })["result"]["structuredContent"]
        self.assertEqual(cancelled["status"], "interrupted")
        self.assertFalse(cancelled["writerActive"])
        self.assertEqual(cancelled["threadHandoff"], "available")
        self.assertEqual(cancelled["nextAction"], "continue")
        self.assertIn("threadId", cancelled)

        durable = json.loads(status_path.read_text(encoding="utf-8"))
        worker = json.loads((job_dir / "worker.json").read_text(encoding="utf-8"))
        with self.assertRaises(ProcessLookupError):
            os.kill(worker["pid"], 0)
        controls = json.loads((job_dir / "controls.json").read_text(encoding="utf-8"))
        self.assertEqual([item["kind"] for item in controls["commands"]], ["cancel"])

        again = harness.call(5, "codex-job-cancel", {
            "jobId": job_id,
            "reason": "duplicate cancellation must be a no-op",
        })["result"]["structuredContent"]
        self.assertEqual(again["status"], "interrupted")
        self.assertEqual(again["threadId"], cancelled["threadId"])
        self.assertEqual(
            json.loads((job_dir / "controls.json").read_text(encoding="utf-8")),
            controls,
        )
        self.assertFalse(durable["writerActive"])
'''
tests = tests.replace(anchor, extra + anchor, 1)

TESTS.write_text(tests, encoding="utf-8")
