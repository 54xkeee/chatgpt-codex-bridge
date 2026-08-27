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

old_queued_reconcile = '''        if reconcile and state.get("status") == "queued":\n            worker_path = path / "worker.json"\n            if worker_path.is_symlink():\n                raise GuardProtocolError("invalid job state")\n            worker = read_json_object(worker_path) if worker_path.is_file() else {"pid": None}\n            if not process_exists(worker.get("pid")):\n                content = state.get("content") or "本机 Codex 后台进程已中断。"\n                state.update({\n                    "status": "interrupted",\n                    "content": content,\n                    "phase": "interrupted",\n                    "activity": content,\n                    "lastEventAt": time.time(),\n                    "failureStage": state.get("phase", "queued"),\n                    "nextAction": "repair",\n                    "updatedAt": time.time(),\n                })\n                finish_job_report(state, "interrupted", content, "repair")\n                atomic_write_json(path / "status.json", state)\n'''
new_queued_reconcile = '''        if reconcile and state.get("status") == "queued":\n            worker_path = path / "worker.json"\n            if worker_path.is_symlink():\n                raise GuardProtocolError("invalid job state")\n            worker = read_json_object(worker_path) if worker_path.is_file() else {"pid": None}\n            if not process_exists(worker.get("pid")):\n                _mark_job_interrupted(path, state, "本机 Codex 后台进程已中断。")\n                state = read_json_object(path / "status.json")\n'''
text = replace_once(text, old_queued_reconcile, new_queued_reconcile, "queued reconcile")

old_running_reconcile = '''        if (\n            reconcile\n            and state.get("status") == "running"\n            and not process_exists(state.get("pid"))\n        ):\n            content = state.get("content") or "本机 Codex 后台进程已中断。"\n            state.update({\n                "status": "interrupted",\n                "content": content,\n                "phase": "interrupted",\n                "activity": content,\n                "lastEventAt": time.time(),\n                "failureStage": state.get("phase", "working"),\n                "nextAction": "repair",\n                "updatedAt": time.time(),\n            })\n            finish_job_report(state, "interrupted", content, "repair")\n            atomic_write_json(path / "status.json", state)\n'''
new_running_reconcile = '''        if (\n            reconcile\n            and state.get("status") == "running"\n            and not process_exists(state.get("pid"))\n        ):\n            _mark_job_interrupted(path, state, "本机 Codex 后台进程已中断。")\n            state = read_json_object(path / "status.json")\n'''
text = replace_once(text, old_running_reconcile, new_running_reconcile, "running reconcile")

old_append_control = '''        commands.append(command)\n        atomic_write_json(control_path, {"commands": commands})\n        append_transcript(\n            state, "controller", kind, text, command["createdAt"], "queued", control_id\n        )\n        state["lastEventAt"] = command["createdAt"]\n        state["updatedAt"] = command["createdAt"]\n        atomic_write_json(path / "status.json", state)\n        return control_id\n'''
new_append_control = '''        commands.append(command)\n        atomic_write_json(control_path, {"commands": commands})\n        return control_id\n'''
text = replace_once(text, old_append_control, new_append_control, "single-writer control mailbox")

old_steer_send = '''            client.send({\n                "method": "turn/steer",\n                "id": "bridge-steer-" + control_id,\n                "params": {\n                    "threadId": thread_id,\n                    "expectedTurnId": turn_id,\n                    "input": [{"type": "text", "text": prompt}],\n                },\n            })\n            update_control_delivery(state, control_id, "sent")\n            state["activity"] = "已向正在运行的 Codex 回合插入补充指令。"\n'''
new_steer_send = '''            client.send({\n                "method": "turn/steer",\n                "id": "bridge-steer-" + control_id,\n                "params": {\n                    "threadId": thread_id,\n                    "expectedTurnId": turn_id,\n                    "input": [{"type": "text", "text": prompt}],\n                },\n            })\n            append_transcript(\n                state, "controller", "steer", prompt, command.get("createdAt"),\n                "sent", control_id\n            )\n            state["activity"] = "已向正在运行的 Codex 回合插入补充指令。"\n'''
text = replace_once(text, old_steer_send, new_steer_send, "steer transcript")

old_cancel_send = '''            client.send({\n                "method": "turn/interrupt",\n                "id": "bridge-cancel-" + control_id,\n                "params": {"threadId": thread_id, "turnId": turn_id},\n            })\n            update_control_delivery(state, control_id, "sent")\n            state["activity"] = "已请求中断当前 Codex 回合。"\n'''
new_cancel_send = '''            reason = command.get("reason")\n            if not isinstance(reason, str):\n                raise GuardProtocolError("invalid cancel command")\n            client.send({\n                "method": "turn/interrupt",\n                "id": "bridge-cancel-" + control_id,\n                "params": {"threadId": thread_id, "turnId": turn_id},\n            })\n            append_transcript(\n                state, "controller", "cancel", reason, command.get("createdAt"),\n                "sent", control_id\n            )\n            state["activity"] = "已请求中断当前 Codex 回合。"\n'''
text = replace_once(text, old_cancel_send, new_cancel_send, "cancel transcript")

old_public_transcript = '''    transcript = state.get("transcript")\n    public["transcript"] = transcript if isinstance(transcript, list) else []\n'''
new_public_transcript = '''    transcript = state.get("transcript")\n    public_transcript = []\n    if isinstance(transcript, list):\n        for entry in transcript[:TRANSCRIPT_MAX_ITEMS]:\n            if not isinstance(entry, dict):\n                continue\n            public_transcript.append({\n                key: value for key, value in entry.items()\n                if key != "controlId"\n            })\n    public["transcript"] = public_transcript\n'''
text = replace_once(text, old_public_transcript, new_public_transcript, "hide internal control ids")

SOURCE.write_text(text, encoding="utf-8")
MIRROR.write_text(text, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
start = tests.index("    def test_tools_list_exposes_only_truthfully_annotated_narrow_tools(self):")
end = tests.index("\n    def test_catalog_tools_cover_projects_repositories_threads_history_and_jobs", start)
new_tool_test = '''    def test_tools_list_exposes_only_truthfully_annotated_narrow_tools(self):\n        harness = self.harness()\n        response = harness.initialize()\n        tools = response["result"]["tools"]\n        by_name = {tool["name"]: tool for tool in tools}\n        self.assertEqual(\n            [tool["name"] for tool in tools],\n            [\n                "codex", "codex-reply", "codex-run", "codex-start",\n                "codex-reply-async", "codex-wait", "codex-job-open",\n                "codex-job-status", "codex-job-steer", "codex-job-cancel",\n                "codex-overview", "codex-project-list",\n                "codex-repository-list", "codex-thread-list",\n                "codex-thread-read", "codex-job-list",\n            ],\n        )\n        for name in ("codex", "codex-reply", "codex-run", "codex-start", "codex-reply-async", "codex-job-steer"):\n            self.assertEqual(by_name[name]["annotations"], SAFETY_ANNOTATIONS)\n        for name in ("codex-wait", "codex-job-open", "codex-job-status", "codex-overview", "codex-project-list", "codex-repository-list", "codex-thread-list", "codex-thread-read", "codex-job-list"):\n            self.assertEqual(by_name[name]["annotations"], READ_ONLY_ANNOTATIONS)\n        self.assertTrue(by_name["codex-job-cancel"]["annotations"]["destructiveHint"])\n        self.assertTrue(by_name["codex-job-cancel"]["annotations"]["idempotentHint"])\n        self.assertEqual(by_name["codex-wait"]["_meta"]["ui"]["visibility"], ["model"])\n        self.assertEqual(by_name["codex-job-status"]["_meta"]["ui"]["visibility"], ["model", "app"])\n        self.assertNotIn("openai/visibility", by_name["codex-job-status"]["_meta"])\n        self.assertIn("timeoutSeconds", by_name["codex-wait"]["inputSchema"]["properties"])\n        self.assertEqual(by_name["codex-wait"]["inputSchema"]["required"], ["jobId"])\n        self.assertNotIn("MUST call", by_name["codex-run"]["description"])\n        self.assertNotIn("MUST call", by_name["codex-wait"]["description"])\n        self.assertIn("workspace-new-project", by_name["codex-start"]["description"])\n        self.assertIn("same thread/turn", by_name["codex-job-steer"]["description"])\n        self.assertIn("turn interrupt", by_name["codex-job-cancel"]["description"])\n        expected_statuses = ["queued", "running", "completed", "failed", "interrupted"]\n        for name in ("codex-run", "codex-start", "codex-reply-async", "codex-wait", "codex-job-open", "codex-job-status", "codex-job-steer", "codex-job-cancel"):\n            schema = by_name[name]["outputSchema"]\n            self.assertEqual(schema["properties"]["status"]["enum"], expected_statuses)\n            for field in ("transcript", "writerActive", "threadHandoff"):\n                self.assertIn(field, schema["required"])\n\n        codex_schema = by_name["codex"]["inputSchema"]\n        self.assertEqual(codex_schema["required"], ["prompt"])\n        self.assertEqual(set(codex_schema["properties"]), {"prompt"})\n        reply_schema = by_name["codex-reply"]["inputSchema"]\n        self.assertEqual(reply_schema["required"], ["prompt", "threadId"])\n        self.assertEqual(set(reply_schema["properties"]), {"prompt", "threadId"})\n\n'''
tests = tests[:start] + new_tool_test + tests[end:]

# A second tool-name list is used to verify multiplexed initialize replay.
old_names = '''                "codex-job-open",\n                "codex-job-status",\n                "codex-overview",\n'''
new_names = '''                "codex-job-open",\n                "codex-job-status",\n                "codex-job-steer",\n                "codex-job-cancel",\n                "codex-overview",\n'''
tests = tests.replace(old_names, new_names)

anchor = '\n\nif __name__ == "__main__":\n'
if anchor not in tests:
    raise SystemExit("test insertion anchor missing")
extra_tests = r'''

    def test_public_job_state_exposes_auditable_transcript_and_handoff_without_control_ids(self):
        module_spec = importlib.util.spec_from_file_location(
            "chatgpt_codex_guard_transcript_test", GUARD,
        )
        guard_module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(guard_module)
        state = {
            "jobId": "signed-job",
            "status": "running",
            "content": "",
            "updatedAt": 1.0,
            "lastEventAt": 1.0,
            "writerActive": True,
            "threadHandoff": "bridge-owned",
            "workspace": "/tmp/workspace",
            "projectName": "demo",
            "transcript": [],
        }
        guard_module.append_transcript(
            state, "controller", "prompt", "exact prompt", 1.0, "submitted", "private-control-id"
        )
        guard_module.append_transcript(
            state, "codex", "message", "public reply", 2.0, "final_answer"
        )
        public = guard_module.public_job_state(state)
        self.assertTrue(public["writerActive"])
        self.assertEqual(public["threadHandoff"], "bridge-owned")
        self.assertEqual(public["transcript"][0]["text"], "exact prompt")
        self.assertEqual(public["transcript"][1]["text"], "public reply")
        self.assertNotIn("controlId", json.dumps(public["transcript"]))

    def test_worker_controls_use_exact_turn_steer_and_interrupt_and_record_public_transcript(self):
        module_spec = importlib.util.spec_from_file_location(
            "chatgpt_codex_guard_controls_test", GUARD,
        )
        guard_module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(guard_module)
        job_dir = self.root / "control-helper-job"
        job_dir.mkdir()
        controls = {
            "commands": [
                {"id": "steer-1", "kind": "steer", "prompt": "change direction", "createdAt": 1.0},
                {"id": "cancel-1", "kind": "cancel", "reason": "stop now", "createdAt": 2.0},
            ]
        }
        (job_dir / "controls.json").write_text(json.dumps(controls), encoding="utf-8")
        state = {
            "jobId": "signed-job", "internalJobId": "unused", "status": "running",
            "content": "", "updatedAt": 0.0, "lastEventAt": 0.0,
            "transcript": [], "report": guard_module.initial_job_report(),
        }
        (job_dir / "status.json").write_text(json.dumps(state), encoding="utf-8")

        class FakeClient:
            def __init__(self):
                self.messages = []
            def send(self, message):
                self.messages.append(message)

        client = FakeClient()
        processed = set()
        guard_module.process_worker_controls(
            client, job_dir, state, "raw-thread", "raw-turn", processed
        )
        self.assertEqual([m["method"] for m in client.messages], ["turn/steer", "turn/interrupt"])
        self.assertEqual(client.messages[0]["params"], {
            "threadId": "raw-thread",
            "expectedTurnId": "raw-turn",
            "input": [{"type": "text", "text": "change direction"}],
        })
        self.assertEqual(client.messages[1]["params"], {
            "threadId": "raw-thread", "turnId": "raw-turn",
        })
        self.assertEqual([entry["kind"] for entry in state["transcript"]], ["steer", "cancel"])
        self.assertEqual([entry["text"] for entry in state["transcript"]], ["change direction", "stop now"])
        self.assertEqual(processed, {"steer-1", "cancel-1"})

    def test_wait_timeout_is_caller_bounded_and_status_is_model_visible(self):
        harness = self.harness(scenario="async_slow", job_wait_seconds=0.05)
        response = harness.initialize()
        by_name = {tool["name"]: tool for tool in response["result"]["tools"]}
        self.assertEqual(by_name["codex-job-status"]["_meta"]["ui"]["visibility"], ["model", "app"])
        queued = harness.call(3, "codex-run", {"prompt": "bounded wait"})
        job_id = queued["result"]["structuredContent"]["jobId"]
        joined = harness.call(4, "codex-wait", {"jobId": job_id, "timeoutSeconds": 0.02})
        self.assertIn(joined["result"]["structuredContent"]["status"], ("queued", "running", "completed"))
        too_long = harness.call(5, "codex-wait", {"jobId": job_id, "timeoutSeconds": 56})
        self.assertEqual(too_long["error"]["code"], -32602)
'''
tests = tests.replace(anchor, extra_tests + anchor, 1)
TESTS.write_text(tests, encoding="utf-8")
