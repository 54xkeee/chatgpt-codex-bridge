"""Contract tests for the ZCode provider of the bridge guard.

The Codex contract suite (test-codex-mcp-guard.py) stays the regression base
for the codex provider; this file covers the zcode provider seam: the zcode-*
tool surface, the ZCode Protocol worker loop, steer/cancel semantics, model
config failure mapping, and the session-backed catalog.
"""

import importlib.util
import json
import os
import select
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD_SOURCE = REPO_ROOT / "scripts" / "bridge" / "codex-mcp-guard.py"

_spec = importlib.util.spec_from_file_location("zcode_guard_module", GUARD_SOURCE)
guard_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard_module)

FAKE_ZCODE_SOURCE = r'''
import json, os, sys, time

argv0 = sys.argv[0]
base = os.path.basename(argv0)
scenario = "normal"
if base.startswith("fake-zcode-"):
    scenario = base[len("fake-zcode-"):-3]

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(argv0)),
                          "fake-zcode-" + scenario + ".state.jsonl")

def record(entry):
    with open(STATE_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

def emit(message):
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    record({"emitted": message})

def reply(request_id, result):
    sys.stdout.write(json.dumps({"id": request_id, "result": result}, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    record({"replied": request_id, "result": result})

def reply_error(request_id, code, code_name, message):
    body = {"code": code, "message": message}
    if code_name:
        body = {"code": code, "data": {"code": code_name, "message": message}, "message": message}
    sys.stdout.write(json.dumps({"id": request_id, "error": body}, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    record({"replied": request_id, "error": body})

def read_line():
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line)

def workspace_of(path):
    return {"workspaceKey": path, "workspacePath": path}

state = {
    "requests": [],
    "sessions": {},
    "running_session": None,
    "prefs_replies": 0,
    "stops": 0,
    "sends": 0,
}
counter = {"value": 0}

def next_turn_id():
    counter["value"] += 1
    return "turn_fake_%04d" % counter["value"]

def main():
    while True:
        line = read_line()
        if line is None:
            return 0
        if not isinstance(line, dict):
            continue
        method = line.get("method")
        params = line.get("params") or {}
        request_id = line.get("id")
        state["requests"].append({"method": method, "params": params})
        record({"received": {"method": method, "params": params}})
        if method is None:
            # A response to one of our server->client requests. Bridge request
            # ids may be strings, so discrimination is on the missing method.
            if "result" in line and isinstance(line.get("result"), dict):
                if line["result"].get("nativeSearchEnhancementsEnabled") is False:
                    state["prefs_ok"] = True
                record({"prefs_reply": line})
            continue

        if method == "session/create":
            if scenario == "model_config_missing":
                reply_error(request_id, -32603, "model_config_missing",
                            "Model config is missing. Create ~/.zcode/cli/config.json with an explicit model provider before running ZCode.")
                continue
            # The real server asks the client for runtime preferences while
            # materializing a session; the guard must answer them.
            emit({"id": "server-prefs-1",
                  "method": "session/requestRuntimePreferences",
                  "params": {"sessionId": "pending",
                             "scope": "runtime-materialization"}})
            while True:
                inner = read_line()
                if inner is None:
                    return 0
                if inner.get("id") == "server-prefs-1" and "result" in inner:
                    prefs_ok = (
                        inner["result"].get("nativeSearchEnhancementsEnabled") is False
                    )
                    record({"prefs_reply": inner, "prefs_ok": prefs_ok})
                    break
                record({"unexpected_during_prefs": inner})
            requested = params.get("sessionId")
            session_id = requested or ("sess_fake_%04d" % counter["value"])
            if scenario == "wrong_session":
                session_id = (requested or "") + "_other"
            workspace = (params.get("workspace") or {}).get("workspacePath", "")
            record({"session": session_id, "workspace": workspace})
            reply(request_id, {
                "session": {
                    "sessionId": session_id,
                    "mode": params.get("mode", "build"),
                    "status": "idle",
                    "title": "",
                    "createdAt": 1,
                    "updatedAt": 1,
                    "workspace": workspace_of(workspace),
                }
            })
            continue

        if method == "session/setMode":
            reply(request_id, {"accepted": True})
            continue

        if method == "session/subscribe":
            reply(request_id, {"sessionId": params.get("sessionId"), "eventSeq": 0, "events": []})
            continue

        if method == "session/send":
            state["sends"] += 1
            session_id = params.get("sessionId")
            content = params.get("content", "")
            input_id = params.get("inputId")
            reply(request_id, {"accepted": True, "sessionId": session_id, "stateRevision": state["sends"]})
            running = state.get("running_session")
            if running is not None and running == session_id:
                running_turn = state.get("running_turn", "")
                emit({"method": "session/event", "params": {
                    "type": "turn.steerQueued", "turnId": running_turn,
                    "sessionId": session_id, "seq": 90,
                    "payload": {"inputPreview": content[:80], "input": content},
                }})
                record({"steered": content})
                if scenario == "steer":
                    emit({"method": "session/event", "params": {
                        "type": "turn.completed", "turnId": running_turn,
                        "sessionId": session_id, "seq": 91,
                        "payload": {"response": "STEERED-RESULT " + content[-24:], "resultType": "success"},
                    }})
                    state["running_session"] = None
                continue
            turn_id = next_turn_id()
            if scenario in ("cancel", "steer") and input_id and input_id.startswith("bridge-initial"):
                state["running_session"] = session_id
                state["running_turn"] = turn_id
                emit({"method": "state.updated", "params": {
                    "type": "state.updated", "reason": "prompt_started",
                    "patch": {"status": "running"}, "sessionId": session_id,
                }})
                emit({"method": "session/event", "params": {
                    "type": "turn.started", "turnId": turn_id,
                    "sessionId": session_id, "seq": 10,
                    "payload": {"input": content, "turnNumber": 0},
                }})
                continue
            emit({"method": "session/event", "params": {
                "type": "turn.started", "turnId": turn_id,
                "sessionId": session_id, "seq": 10,
                "payload": {"input": content, "turnNumber": 0},
            }})
            if scenario == "empty_response":
                emit({"method": "session/event", "params": {
                    "type": "turn.started", "turnId": turn_id,
                    "sessionId": session_id, "seq": 10,
                    "payload": {"input": content, "turnNumber": 0},
                }})
                emit({"method": "session/event", "params": {
                    "type": "turn.completed", "turnId": turn_id,
                    "sessionId": session_id, "seq": 12,
                    "payload": {"resultType": "success"},
                }})
                continue
            emit({"method": "session/event", "params": {
                "type": "message.upserted", "turnId": turn_id,
                "sessionId": session_id, "seq": 11,
                "payload": {"message": {"role": "assistant", "parts": [
                    {"type": "text", "text": "working on: " + content[:32]},
                ]}},
            }})
            if scenario == "fail":
                emit({"method": "session/event", "params": {
                    "type": "turn.failed", "turnId": turn_id,
                    "sessionId": session_id, "seq": 12,
                    "payload": {"error": {"type": "model_error", "message": "synthetic zcode failure"}},
                }})
                continue
            if scenario == "empty_response":
                emit({"method": "session/event", "params": {
                    "type": "turn.completed", "turnId": turn_id,
                    "sessionId": session_id, "seq": 12,
                    "payload": {"resultType": "success"},
                }})
                continue
            emit({"method": "session/event", "params": {
                "type": "turn.completed", "turnId": turn_id,
                "sessionId": session_id, "seq": 12,
                "payload": {"response": "ZCODE-FINAL: " + content[:40], "resultType": "success"},
            }})
            continue

        if method == "session/stop":
            state["stops"] += 1
            reply(request_id, {"accepted": True})
            session_id = params.get("sessionId")
            running_turn = state.get("running_turn")
            if running_turn is not None:
                emit({"method": "session/event", "params": {
                    "type": "turn.failed", "turnId": running_turn,
                    "sessionId": session_id, "seq": 95,
                    "payload": {"error": {"type": "model_error", "message": "provider aborted after stop"}},
                }})
                state["running_turn"] = None
            continue

        if method == "session/list":
            fixture_path = os.path.join(os.path.dirname(os.path.abspath(argv0)),
                                        "fake-zcode-" + scenario + ".sessions.json")
            sessions = []
            if os.path.exists(fixture_path):
                with open(fixture_path, encoding="utf-8") as handle:
                    sessions = json.load(handle)
            reply(request_id, {"sessions": sessions})
            continue

        if method == "session/read":
            fixture_path = os.path.join(os.path.dirname(os.path.abspath(argv0)),
                                        "fake-zcode-" + scenario + ".sessions.json")
            sessions = []
            if os.path.exists(fixture_path):
                with open(fixture_path, encoding="utf-8") as handle:
                    sessions = json.load(handle)
            target = params.get("sessionId")
            found = next((s for s in sessions if s.get("sessionId") == target), None)
            if found is None:
                reply_error(request_id, -32602, "", "unknown session")
            else:
                reply(request_id, {"session": found})
            continue

        if method == "session/messages":
            reply(request_id, {"messages": [
                {"info": {"role": "user"}, "parts": [{"type": "text", "text": "history question"}]},
                {"info": {"role": "assistant"}, "parts": [{"type": "text", "text": "history answer"}]},
            ]})
            continue

        reply_error(request_id, -32601, "", "Method not found: " + str(method))

if __name__ == "__main__":
    sys.exit(main())
'''

PUBLIC_TOOLS_FULL = (
    "zcode", "zcode-reply", "zcode-run", "zcode-start", "zcode-reply-async",
    "zcode-wait", "zcode-job-open", "zcode-job-status", "zcode-job-steer",
    "zcode-job-cancel", "zcode-overview", "zcode-project-list",
    "zcode-repository-list", "zcode-thread-list", "zcode-thread-read",
    "zcode-job-list",
)


class ZcodeGuardHarness:
    def __init__(self, workspace, scenario="normal", preset="full", job_wait_seconds=0.5):
        self.workspace = str(workspace)
        self.root = Path(tempfile.mkdtemp(prefix="zcode-guard-harness-"))
        self.fake_dir = self.root / "fake-zcode"
        self.fake_dir.mkdir()
        self.fake_path = self.fake_dir / ("fake-zcode-" + scenario + ".py")
        self.fake_path.write_text(
            "#!/usr/bin/env python3\n" + FAKE_ZCODE_SOURCE, encoding="utf-8"
        )
        self.fake_path.chmod(0o755)
        self.jobs_dir = self.root / "jobs"
        self.jobs_dir.mkdir()
        self.guard_path = self.root / "guard.py"
        shutil.copyfile(GUARD_SOURCE, self.guard_path)
        args = [
            sys.executable,
            str(self.guard_path),
            "--workspace", self.workspace,
            "--provider", "zcode",
            "--zcode-bin", str(self.fake_path),
            "--zcode-cjs", str(self.fake_path),
            "--job-state-dir", str(self.jobs_dir),
            "--job-wait-seconds", str(job_wait_seconds),
        ]
        if preset == "full":
            args += ["--sandbox", "danger-full-access", "--approval-policy", "never"]
        else:
            args += ["--sandbox", "workspace-write", "--approval-policy", "on-request"]
        self.process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        self.buffer = bytearray()
        self.stderr = []
        self.next_request_id = 100

    def send(self, message):
        self.process.stdin.write(
            json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n"
        )
        self.process.stdin.flush()

    def call(self, method, params, id_value):
        self.send({"jsonrpc": "2.0", "id": id_value, "method": method, "params": params})

    def receive(self, timeout=15.0):
        while b"\n" not in self.buffer:
            ready, _, _ = select.select([self.process.stdout], [], [], timeout)
            if not ready:
                raise AssertionError("guard stdout timeout")
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                stderr = ""
                try:
                    stderr = self.process.stderr.read().decode("utf-8", "replace")
                except Exception:
                    pass
                raise AssertionError("guard stdout closed; stderr=" + stderr[-2000:])
            self.buffer.extend(chunk)
        newline = self.buffer.find(b"\n")
        raw = bytes(self.buffer[:newline])
        del self.buffer[: newline + 1]
        return json.loads(raw.decode("utf-8"))

    def drain_until(self, predicate, timeout=25.0):
        import time as _time
        deadline = _time.monotonic() + timeout
        messages = []
        while _time.monotonic() < deadline:
            try:
                ready, _, _ = select.select([self.process.stdout], [], [], 0.25)
            except (OSError, ValueError):
                break
            if not ready:
                if predicate(messages):
                    return messages
                continue
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                break
            self.buffer.extend(chunk)
            while b"\n" in self.buffer:
                newline = self.buffer.find(b"\n")
                raw = bytes(self.buffer[:newline])
                del self.buffer[: newline + 1]
                try:
                    messages.append(json.loads(raw.decode("utf-8")))
                except json.JSONDecodeError:
                    continue
            if predicate(messages):
                return messages
        return messages

    def initialize(self):
        self.call("initialize", {"protocolVersion": "2025-06-18"}, 1)
        response = self.receive()
        assert response["id"] == 1 and "result" in response
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.call("tools/list", {}, 2)
        listed = self.receive()
        assert listed["id"] == 2
        return listed["result"]["tools"]

    def capabilities(self):
        key_path = self.jobs_dir / "capability.key"
        for _ in range(100):
            if key_path.is_file():
                break
            import time as _time
            _time.sleep(0.05)
        return guard_module.CapabilityCodec(
            key_path,
            guard_module.capability_context(
                self.workspace, "danger-full-access", "never"
            ),
        )

    def call_tool(self, name, arguments, id_value):
        self.call("tools/call", {"name": name, "arguments": arguments}, id_value)
        return self.receive()

    def wait_for_terminal(self, job_id, id_value, timeout=30.0):
        import time as _time
        deadline = _time.monotonic() + timeout
        cursor = 300
        while _time.monotonic() < deadline:
            response = self.call_tool(
                "zcode-wait", {"jobId": job_id, "timeoutSeconds": 0.5}, cursor
            )
            cursor += 1
            structured = response.get("result", {}).get("structuredContent", {})
            status = structured.get("status")
            if status in ("completed", "failed", "interrupted"):
                return response
        raise AssertionError("job did not reach a terminal state")

    def fake_state_path(self):
        return self.fake_dir / (self.fake_path.stem + ".state.jsonl")

    def fake_state(self):
        entries = []
        path = self.fake_state_path()
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    entries.append(json.loads(line))
        return entries

    def close(self):
        try:
            if self.process.poll() is None:
                self.process.stdin.close()
                self.process.wait(timeout=5)
        except Exception:
            self.process.kill()
            self.process.wait(timeout=5)
        try:
            stderr = self.process.stderr.read().decode("utf-8", "replace")
        except Exception:
            stderr = ""
        if stderr:
            self.stderr.append(stderr)
        shutil.rmtree(self.root, ignore_errors=True)


class ZcodeMcpGuardContractTest(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="zcode-workspace-"))
        (self.workspace / "repo").mkdir()

    def tearDown(self):
        shutil.rmtree(self.workspace, ignore_errors=True)

    def start_guard(self, **kwargs):
        harness = ZcodeGuardHarness(self.workspace, **kwargs)
        self.addCleanup(harness.close)
        return harness

    def test_tools_list_exposes_truthful_zcode_surface(self):
        harness = self.start_guard()
        tools = harness.initialize()
        names = [tool["name"] for tool in tools]
        self.assertEqual(names, list(PUBLIC_TOOLS_FULL))
        for tool in tools:
            self.assertNotIn("codex", tool["name"])
            self.assertNotIn("Codex", tool.get("description", ""))

    def test_codex_prefixed_tools_are_rejected(self):
        harness = self.start_guard()
        harness.initialize()
        response = harness.call_tool("codex-run", {"prompt": "x"}, 500)
        self.assertEqual(response["error"]["code"], -32601)

    def test_provider_configuration_requires_zcode_paths(self):
        provider_arguments = [
            "--run-job", str(self.workspace),
            "--workspace", str(self.workspace),
            "--provider", "zcode",
            "--job-max-seconds", "14400",
            "--sandbox", "danger-full-access",
            "--approval-policy", "never",
        ]
        with self.assertRaises(guard_module.GuardConfigurationError):
            guard_module.parse_worker_configuration(provider_arguments)
        daemon_arguments = [
            "--workspace", str(self.workspace),
            "--provider", "zcode",
            "--sandbox", "danger-full-access",
            "--approval-policy", "never",
        ]
        with self.assertRaises(guard_module.GuardConfigurationError):
            guard_module.parse_configuration(daemon_arguments)

    def test_guard_answers_runtime_preferences_request(self):
        import time as _time
        harness = self.start_guard()
        harness.initialize()
        harness.call_tool("zcode-run", {"prompt": "pref check"}, 501)
        found = False
        deadline = _time.monotonic() + 20.0
        while _time.monotonic() < deadline and not found:
            for entry in harness.fake_state():
                if entry.get("prefs_reply"):
                    self.assertIs(
                        entry["prefs_reply"]["result"].get(
                            "nativeSearchEnhancementsEnabled"
                        ),
                        False,
                    )
                    self.assertTrue(entry.get("prefs_ok"))
                    found = True
                    break
            if not found:
                _time.sleep(0.2)
        self.assertTrue(found, "fake never observed a valid prefs reply")

    def test_durable_job_completes_with_transcript_and_handoff(self):
        harness = self.start_guard()
        harness.initialize()
        response = harness.call_tool("zcode-run", {"prompt": "build the widget"}, 510)
        structured = response["result"]["structuredContent"]
        job_id = structured["jobId"]
        self.assertEqual(structured["status"], "queued")
        final = harness.wait_for_terminal(job_id, 511)
        terminal = final["result"]["structuredContent"]
        self.assertEqual(terminal["status"], "completed")
        self.assertTrue(terminal["content"].startswith("ZCODE-FINAL: "))
        self.assertEqual(terminal["writerActive"], False)
        self.assertEqual(terminal["threadHandoff"], "available")
        self.assertIn("build the widget", json.dumps(terminal["transcript"], ensure_ascii=False))
        kinds = [entry["kind"] for entry in terminal["transcript"]]
        self.assertIn("message", kinds)
        for entry in terminal["transcript"]:
            self.assertNotIn("controlId", entry)
        report = terminal["report"]
        self.assertEqual(report["outcome"], "completed")

    def test_running_steer_is_recorded_and_delivered(self):
        harness = self.start_guard(scenario="steer")
        harness.initialize()
        response = harness.call_tool("zcode-run", {"prompt": "long task"}, 520)
        job_id = response["result"]["structuredContent"]["jobId"]
        capabilities = harness.capabilities()
        internal_job_id = capabilities.decode("job", job_id)
        job_dir = Path(harness.jobs_dir) / internal_job_id
        controls = {
            "commands": [{
                "id": "steer-control-1",
                "kind": "steer",
                "createdAt": 1.0,
                "prompt": "switch to the fast path",
            }]
        }
        (job_dir / "controls.json").write_text(
            json.dumps(controls), encoding="utf-8"
        )
        final = harness.wait_for_terminal(job_id, 521)
        terminal = final["result"]["structuredContent"]
        self.assertEqual(terminal["status"], "completed")
        self.assertIn("STEERED-RESULT", terminal["content"])
        steers = [
            entry for entry in terminal["transcript"] if entry["kind"] == "steer"
        ]
        self.assertTrue(steers)
        self.assertEqual(steers[-1]["delivery"], "sent")
        stops = [
            entry for entry in harness.fake_state()
            if entry.get("received", {}).get("method") == "session/stop"
        ]
        self.assertEqual(len(stops), 0)

    def test_running_cancel_is_scoped_idempotent_and_releases_writer(self):
        harness = self.start_guard(scenario="cancel")
        harness.initialize()
        response = harness.call_tool("zcode-run", {"prompt": "cancellable task"}, 530)
        job_id = response["result"]["structuredContent"]["jobId"]
        capabilities = harness.capabilities()
        internal_job_id = capabilities.decode("job", job_id)
        job_dir = Path(harness.jobs_dir) / internal_job_id
        controls = {
            "commands": [{
                "id": "cancel-control-1",
                "kind": "cancel",
                "createdAt": 1.0,
                "reason": "user changed mind",
            }]
        }
        (job_dir / "controls.json").write_text(json.dumps(controls), encoding="utf-8")
        final = harness.wait_for_terminal(job_id, 531)
        terminal = final["result"]["structuredContent"]
        self.assertEqual(terminal["status"], "interrupted")
        self.assertEqual(terminal["writerActive"], False)
        self.assertEqual(terminal["threadHandoff"], "available")
        cancels = [
            entry for entry in terminal["transcript"] if entry["kind"] == "cancel"
        ]
        self.assertTrue(cancels)
        self.assertIn("user changed mind", cancels[-1]["text"])
        repeat = harness.call_tool("zcode-job-cancel", {"jobId": job_id, "reason": "again"}, 532)
        self.assertEqual(
            repeat["result"]["structuredContent"]["status"], "interrupted"
        )
        stops = [
            entry for entry in harness.fake_state()
            if entry.get("received", {}).get("method") == "session/stop"
        ]
        self.assertEqual(len(stops), 1)

    def test_model_config_missing_maps_to_repair(self):
        harness = self.start_guard(scenario="model_config_missing")
        harness.initialize()
        response = harness.call_tool("zcode-run", {"prompt": "needs model"}, 540)
        job_id = response["result"]["structuredContent"]["jobId"]
        final = harness.wait_for_terminal(job_id, 541)
        terminal = final["result"]["structuredContent"]
        self.assertEqual(terminal["status"], "failed")
        self.assertEqual(terminal["failureStage"], "zcode_model_config")
        self.assertEqual(terminal["nextAction"], "repair")

    def test_failed_turn_reports_failure(self):
        harness = self.start_guard(scenario="fail")
        harness.initialize()
        response = harness.call_tool("zcode-run", {"prompt": "doomed"}, 550)
        job_id = response["result"]["structuredContent"]["jobId"]
        final = harness.wait_for_terminal(job_id, 551)
        terminal = final["result"]["structuredContent"]
        self.assertEqual(terminal["status"], "failed")
        self.assertTrue(terminal["content"])
        self.assertEqual(terminal["report"]["outcome"], "failed")
        self.assertEqual(terminal["writerActive"], False)
        self.assertEqual(terminal["report"]["outcome"], "failed")

    def test_completed_without_content_fails_closed(self):
        harness = self.start_guard(scenario="empty_response")
        harness.initialize()
        response = harness.call_tool("zcode-run", {"prompt": "silent"}, 560)
        job_id = response["result"]["structuredContent"]["jobId"]
        final = harness.wait_for_terminal(job_id, 561)
        terminal = final["result"]["structuredContent"]
        self.assertEqual(terminal["status"], "failed")

    def test_workspace_safe_preset_exposes_only_sync_pair(self):
        harness = self.start_guard(preset="scoped")
        tools = harness.initialize()
        self.assertEqual([tool["name"] for tool in tools], ["zcode", "zcode-reply"])
        response = harness.call_tool("zcode", {"prompt": "quick diagnostic"}, 570)
        structured = response["result"]["structuredContent"]
        self.assertTrue(structured["threadId"])
        self.assertIn("quick diagnostic", structured["content"])

    def test_catalog_lists_sessions_inside_roots_only(self):
        harness = self.start_guard(scenario="normal")
        sessions_path = harness.fake_dir / (harness.fake_path.stem + ".sessions.json")
        sessions_path.write_text(json.dumps([
            {
                "sessionId": "sess_inside",
                "status": "idle",
                "title": "inside session",
                "createdAt": 1,
                "updatedAt": 2,
                "workspace": {"workspaceKey": str(self.workspace / "repo"),
                              "workspacePath": str(self.workspace / "repo")},
            },
            {
                "sessionId": "sess_outside",
                "status": "idle",
                "title": "outside session",
                "createdAt": 1,
                "updatedAt": 3,
                "workspace": {"workspaceKey": str(self.workspace.parent),
                              "workspacePath": str(self.workspace.parent)},
            },
        ]), encoding="utf-8")
        harness.initialize()
        response = harness.call_tool("zcode-thread-list", {}, 580)
        threads = response["result"]["structuredContent"]["threads"]
        names = [thread["name"] for thread in threads]
        self.assertIn("inside session", names)
        self.assertNotIn("outside session", names)
        thread_id = threads[0]["threadId"]
        read = harness.call_tool("zcode-thread-read", {"threadId": thread_id}, 581)
        history = read["result"]["structuredContent"]
        kinds = [item["type"] for turn in history["turns"] for item in turn["items"]]
        self.assertIn("userMessage", kinds)
        self.assertIn("agentMessage", kinds)


if __name__ == "__main__":
    unittest.main()
