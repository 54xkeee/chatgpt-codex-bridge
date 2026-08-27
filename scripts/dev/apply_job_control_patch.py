#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/bridge/codex-mcp-guard.py"
MIRROR = ROOT / "plugins/chatgpt-codex-bridge/bridge/codex-mcp-guard.py"
SKILL = ROOT / "plugins/chatgpt-codex-bridge/skills/chatgpt-codex-controller/SKILL.md"
CONTROLLER = ROOT / "plugins/chatgpt-codex-bridge/skills/chatgpt-codex-controller/references/controller-loop.md"
CONTRACT = ROOT / "plugins/chatgpt-codex-bridge/skills/chatgpt-codex-controller/references/mcp-contract.md"
TASKS = ROOT / "docs/specs/job-control-transcript-handoff/tasks.md"


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


text = SOURCE.read_text(encoding="utf-8")

text = replace_once(
    text,
    "JOB_WAIT_DEFAULT_SECONDS = 45.0\nJOB_WAIT_MAX_SECONDS = 55.0\nJOB_WAIT_POLL_SECONDS = 0.25\n",
    "JOB_WAIT_DEFAULT_SECONDS = 52.0\nJOB_WAIT_MAX_SECONDS = 55.0\nJOB_WAIT_POLL_SECONDS = 0.25\nJOB_CONTROL_POLL_SECONDS = 0.25\nJOB_CANCEL_GRACE_SECONDS = 1.5\nJOB_CONTROL_MAX_ITEMS = 100\nTRANSCRIPT_MAX_ITEMS = 100\nTRANSCRIPT_TEXT_LIMIT = 60_000\n",
    "wait constants",
)

text = replace_once(
    text,
    '        "report": {"type": "object", "additionalProperties": True},\n',
    '        "report": {"type": "object", "additionalProperties": True},\n'
    '        "transcript": {"type": "array", "items": {"type": "object"}},\n'
    '        "writerActive": {"type": "boolean"},\n'
    '        "threadHandoff": {\n'
    '            "type": "string",\n'
    '            "enum": ["pending", "bridge-owned", "available", "unavailable"],\n'
    '        },\n'
    '        "workspace": {"type": "string"},\n'
    '        "projectName": {"type": "string"},\n',
    "async output fields",
)

text = replace_once(
    text,
    '        "phase", "activity", "lastEventAt", "failureStage", "nextAction",\n    ],\n}\n',
    '        "phase", "activity", "lastEventAt", "failureStage", "nextAction",\n'
    '        "transcript", "writerActive", "threadHandoff",\n'
    '    ],\n}\n',
    "async required fields",
)

old_run_desc = '''                "Run a task against the bridge's existing workspace as a durable "\n                "background job. Use this for repository work, diagnostics, tests, "\n                "research, and other tasks that may exceed one request deadline. "\n                "It returns a jobId immediately. After it returns, MUST call "\n                "codex-wait with that jobId and MUST keep calling codex-wait while "\n                "the job is queued or running."\n'''
new_run_desc = '''                "Run a task against the bridge's existing workspace as a durable "\n                "background job. Use this for repository work, diagnostics, tests, "\n                "research, and other tasks that may exceed one request deadline. "\n                "It returns a durable jobId immediately. The controller may wait, "\n                "inspect status/transcript, steer, cancel, or return later."\n'''
text = replace_once(text, old_run_desc, new_run_desc, "run description")

old_start_desc = '''                "It returns a jobId immediately and renders a status component. "\n                "After it returns, MUST call codex-wait with that jobId and MUST "\n                "keep calling codex-wait while the job is queued or running. "\n                "MUST NOT answer the user merely because this job was submitted."\n'''
new_start_desc = '''                "It returns a durable jobId immediately and renders a status "\n                "component. The controller may wait, inspect status/transcript, "\n                "steer, cancel, or return later while the job remains recoverable."\n'''
text = replace_once(text, old_start_desc, new_start_desc, "start description")

old_reply_desc = '''                "job. Use for corrections, follow-up work, or a signed threadId "\n                "returned by codex-thread-list. After it returns, MUST call "\n                "codex-wait with that jobId and MUST keep calling codex-wait "\n                "while queued or running. MUST NOT answer the user merely because "\n                "this continuation was submitted."\n'''
new_reply_desc = '''                "job. Use for corrections or follow-up work after a prior turn, "\n                "or a signed threadId returned by codex-thread-list. For an active "\n                "turn prefer codex-job-steer. The returned job remains durable even "\n                "when the controller is not foreground-polling it."\n'''
text = replace_once(text, old_reply_desc, new_reply_desc, "reply description")

old_wait_tool = '''        {\n            "name": "codex-wait",\n            "title": "Wait for Codex Background Job",\n            "description": (\n                "Join one existing durable Codex job. Each call waits for a fixed "\n                "bounded interval under one minute. If the returned status is "\n                "queued or running, MUST call this tool again with the same jobId "\n                "and MUST NOT answer the user yet. On completion, review "\n                "the Codex result. If the user's full requested project remains "\n                "incomplete, MUST call codex-reply-async with the same threadId, "\n                "then MUST join the new job with codex-wait. Stop only when the "\n                "full request is verified complete, needs material user input, "\n                "or has a real terminal blocker."\n            ),\n            "inputSchema": {\n                "type": "object",\n                "additionalProperties": False,\n                "properties": {"jobId": {"type": "string"}},\n                "required": ["jobId"],\n            },\n            "outputSchema": ASYNC_OUTPUT_SCHEMA,\n            "annotations": {\n                "readOnlyHint": True,\n                "destructiveHint": False,\n                "idempotentHint": True,\n                "openWorldHint": False,\n            },\n            "_meta": {"ui": {"visibility": ["model"]}},\n        },\n'''
new_wait_tool = '''        {\n            "name": "codex-wait",\n            "title": "Wait for Codex Background Job",\n            "description": (\n                "Wait for one durable Codex job for a bounded interval and return "\n                "its current state. timeoutSeconds defaults to the bridge wait "\n                "setting and is capped below one MCP request minute. An active job "\n                "remains durable; the controller may wait again, inspect status, "\n                "steer, cancel, or return control to the user."\n            ),\n            "inputSchema": {\n                "type": "object",\n                "additionalProperties": False,\n                "properties": {\n                    "jobId": {"type": "string"},\n                    "timeoutSeconds": {\n                        "type": "number",\n                        "minimum": 0.01,\n                        "maximum": JOB_WAIT_MAX_SECONDS,\n                    },\n                },\n                "required": ["jobId"],\n            },\n            "outputSchema": ASYNC_OUTPUT_SCHEMA,\n            "annotations": READ_ONLY_ANNOTATIONS,\n            "_meta": {"ui": {"visibility": ["model"]}},\n        },\n'''
text = replace_once(text, old_wait_tool, new_wait_tool, "wait tool")

old_status_tool = '''        {\n            "name": "codex-job-status",\n            "title": "Read Codex Background Job",\n            "description": "Read one durable Codex job without waiting.",\n            "inputSchema": {\n                "type": "object",\n                "additionalProperties": False,\n                "properties": {"jobId": {"type": "string"}},\n                "required": ["jobId"],\n            },\n            "outputSchema": ASYNC_OUTPUT_SCHEMA,\n            "annotations": {\n                "readOnlyHint": True,\n                "destructiveHint": False,\n                "idempotentHint": True,\n                "openWorldHint": False,\n            },\n            "_meta": {\n                "ui": {"visibility": ["app"]},\n                "openai/visibility": "private",\n                "openai/widgetAccessible": True,\n            },\n        },\n'''
new_status_tool = '''        {\n            "name": "codex-job-status",\n            "title": "Read Codex Background Job",\n            "description": (\n                "Read one durable Codex job immediately without waiting. Returns "\n                "the public controller/Codex transcript, structured activity report, "\n                "and whether the Codex thread writer is still bridge-owned or "\n                "available for Desktop handoff."\n            ),\n            "inputSchema": {\n                "type": "object",\n                "additionalProperties": False,\n                "properties": {"jobId": {"type": "string"}},\n                "required": ["jobId"],\n            },\n            "outputSchema": ASYNC_OUTPUT_SCHEMA,\n            "annotations": READ_ONLY_ANNOTATIONS,\n            "_meta": {\n                "ui": {"visibility": ["model", "app"]},\n                "openai/widgetAccessible": True,\n            },\n        },\n        {\n            "name": "codex-job-steer",\n            "title": "Steer Running Codex Job",\n            "description": (\n                "Send an additional instruction into the exact active Codex turn "\n                "for this durable job. This keeps the same thread/turn and does not "\n                "create a second writer or follow-up thread."\n            ),\n            "inputSchema": {\n                "type": "object",\n                "additionalProperties": False,\n                "properties": {\n                    "jobId": {"type": "string"},\n                    "prompt": {"type": "string"},\n                },\n                "required": ["jobId", "prompt"],\n            },\n            "outputSchema": ASYNC_OUTPUT_SCHEMA,\n            "annotations": SAFETY_ANNOTATIONS,\n        },\n        {\n            "name": "codex-job-cancel",\n            "title": "Cancel Codex Background Job",\n            "description": (\n                "Idempotently interrupt only this signed durable Codex job. Running "\n                "jobs use the exact App Server turn interrupt first; a verified "\n                "bridge-owned worker-process termination is only a bounded fallback."\n            ),\n            "inputSchema": {\n                "type": "object",\n                "additionalProperties": False,\n                "properties": {\n                    "jobId": {"type": "string"},\n                    "reason": {"type": "string", "maxLength": 4000},\n                },\n                "required": ["jobId"],\n            },\n            "outputSchema": ASYNC_OUTPUT_SCHEMA,\n            "annotations": {\n                "readOnlyHint": False,\n                "destructiveHint": True,\n                "idempotentHint": True,\n                "openWorldHint": False,\n            },\n        },\n'''
text = replace_once(text, old_status_tool, new_status_tool, "status/control tools")

text = replace_once(
    text,
    '    allowed_job_files = {"request.json", "status.json", "worker.json"}\n',
    '    allowed_job_files = {"request.json", "status.json", "worker.json", "controls.json"}\n',
    "purge control allowlist",
)
text = replace_once(
    text,
    '                r"(?:request|status|worker)\\.json\\.tmp\\.[0-9a-f]{32}", item.name\n',
    '                r"(?:request|status|worker|controls)\\.json\\.tmp\\.[0-9a-f]{32}", item.name\n',
    "purge temporary allowlist",
)

insert_before_public = '''\n\ndef transcript_entry(role, kind, text, at=None, delivery="recorded"):\n    raw = text if isinstance(text, str) else ""\n    truncated = len(raw) > TRANSCRIPT_TEXT_LIMIT\n    return {\n        "role": role,\n        "kind": kind,\n        "text": raw[:TRANSCRIPT_TEXT_LIMIT],\n        "textTruncated": truncated,\n        "at": float(time.time() if at is None else at),\n        "delivery": delivery,\n    }\n\n\ndef append_transcript(state, role, kind, text, at=None, delivery="recorded", control_id=""):\n    transcript = state.setdefault("transcript", [])\n    if not isinstance(transcript, list):\n        transcript = []\n        state["transcript"] = transcript\n    if len(transcript) >= TRANSCRIPT_MAX_ITEMS:\n        return\n    entry = transcript_entry(role, kind, text, at=at, delivery=delivery)\n    if control_id:\n        entry["controlId"] = control_id\n    transcript.append(entry)\n\n\ndef update_control_delivery(state, control_id, delivery):\n    transcript = state.get("transcript")\n    if not isinstance(transcript, list):\n        return\n    for entry in reversed(transcript):\n        if isinstance(entry, dict) and entry.get("controlId") == control_id:\n            entry["delivery"] = delivery\n            return\n\n\ndef read_controls(path):\n    control_path = Path(path) / "controls.json"\n    if control_path.is_symlink() or not control_path.is_file():\n        raise GuardProtocolError("invalid job control state")\n    payload = read_json_object(control_path)\n    commands = payload.get("commands")\n    if not isinstance(commands, list) or len(commands) > JOB_CONTROL_MAX_ITEMS:\n        raise GuardProtocolError("invalid job control state")\n    return commands\n\n\ndef terminate_verified_job_worker(job_dir, wait_seconds=3.0):\n    job_dir = Path(job_dir)\n    worker_path = job_dir / "worker.json"\n    if worker_path.is_symlink() or not worker_path.is_file():\n        return False\n    worker = read_json_object(worker_path)\n    pid = worker.get("pid")\n    if not process_exists(pid):\n        return False\n    process_group_id = worker.get("processGroupId", pid)\n    recorded_job_dir = worker.get("jobDir", str(job_dir))\n    recorded_guard = worker.get("guardScript", "")\n    if os.name == "nt":\n        live_process_group_id = pid\n    else:\n        try:\n            live_process_group_id = os.getpgid(pid)\n        except ProcessLookupError:\n            return False\n        except (OSError, PermissionError) as error:\n            raise GuardProtocolError("managed worker ownership could not be verified") from error\n    if (\n        isinstance(pid, bool)\n        or not isinstance(pid, int)\n        or process_group_id != pid\n        or recorded_job_dir != str(job_dir)\n        or live_process_group_id != pid\n        or not _worker_command_matches(pid, job_dir, recorded_guard)\n    ):\n        raise GuardProtocolError("managed worker ownership could not be verified")\n    if os.name == "nt":\n        taskkill = os.path.join(\n            os.environ.get("SYSTEMROOT", r"C:\\Windows"), "System32", "taskkill.exe"\n        )\n        try:\n            subprocess.run(\n                [taskkill, "/PID", str(pid), "/T", "/F"],\n                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,\n                stderr=subprocess.DEVNULL, timeout=max(15.0, wait_seconds),\n                check=False, env=filtered_child_environment(),\n            )\n        except subprocess.TimeoutExpired:\n            pass\n    else:\n        try:\n            os.killpg(pid, signal.SIGTERM)\n        except ProcessLookupError:\n            pass\n    deadline = time.monotonic() + wait_seconds\n    while process_exists(pid) and time.monotonic() < deadline:\n        time.sleep(0.05)\n    if process_exists(pid) and os.name != "nt":\n        try:\n            os.killpg(pid, signal.SIGKILL)\n        except ProcessLookupError:\n            pass\n        deadline = time.monotonic() + 1.0\n        while process_exists(pid) and time.monotonic() < deadline:\n            time.sleep(0.05)\n    if process_exists(pid):\n        raise GuardProtocolError("managed worker did not stop")\n    return True\n\n\ndef process_worker_controls(client, path, state, thread_id, turn_id, processed_ids):\n    if not thread_id or not turn_id:\n        return\n    for command in read_controls(path):\n        if not isinstance(command, dict):\n            raise GuardProtocolError("invalid job control state")\n        control_id = command.get("id")\n        kind = command.get("kind")\n        if not isinstance(control_id, str) or not control_id or control_id in processed_ids:\n            continue\n        if kind == "steer":\n            prompt = command.get("prompt")\n            if not isinstance(prompt, str) or not prompt:\n                raise GuardProtocolError("invalid steer command")\n            client.send({\n                "method": "turn/steer",\n                "id": "bridge-steer-" + control_id,\n                "params": {\n                    "threadId": thread_id,\n                    "expectedTurnId": turn_id,\n                    "input": [{"type": "text", "text": prompt}],\n                },\n            })\n            update_control_delivery(state, control_id, "sent")\n            state["activity"] = "已向正在运行的 Codex 回合插入补充指令。"\n        elif kind == "cancel":\n            client.send({\n                "method": "turn/interrupt",\n                "id": "bridge-cancel-" + control_id,\n                "params": {"threadId": thread_id, "turnId": turn_id},\n            })\n            update_control_delivery(state, control_id, "sent")\n            state["activity"] = "已请求中断当前 Codex 回合。"\n        else:\n            raise GuardProtocolError("invalid job control command")\n        processed_ids.add(control_id)\n        now = time.time()\n        state.update({"lastEventAt": now, "updatedAt": now})\n        atomic_write_json(Path(path) / "status.json", state)\n'''
text = replace_once(text, "\n\ndef public_job_state(state):\n", insert_before_public + "\n\ndef public_job_state(state):\n", "control helpers")

old_mark = '''def _mark_job_interrupted(job_dir, state):\n    if state.get("status") not in ACTIVE_JOB_STATUSES:\n        return\n    content = state.get("content") or "本机 Codex 后台进程已被安全撤销。"\n    state.update({\n        "status": "interrupted",\n        "content": content,\n        "phase": "interrupted",\n        "activity": content,\n        "lastEventAt": time.time(),\n        "failureStage": state.get("phase", "working"),\n        "nextAction": "repair",\n        "updatedAt": time.time(),\n    })\n    finish_job_report(state, "interrupted", content, "repair")\n    atomic_write_json(job_dir / "status.json", state)\n'''
new_mark = '''def _mark_job_interrupted(job_dir, state, reason=""):\n    if state.get("status") not in ACTIVE_JOB_STATUSES:\n        return\n    content = reason or state.get("content") or "本机 Codex 后台进程已被安全撤销。"\n    thread_id = state.get("threadId")\n    state.update({\n        "status": "interrupted",\n        "content": content,\n        "phase": "interrupted",\n        "activity": content,\n        "lastEventAt": time.time(),\n        "failureStage": state.get("phase", "working"),\n        "nextAction": "continue" if isinstance(thread_id, str) and thread_id else "none",\n        "writerActive": False,\n        "threadHandoff": "available" if isinstance(thread_id, str) and thread_id else "unavailable",\n        "updatedAt": time.time(),\n    })\n    finish_job_report(state, "interrupted", content, state["nextAction"])\n    atomic_write_json(job_dir / "status.json", state)\n'''
text = replace_once(text, old_mark, new_mark, "interrupted state")

old_public_tail = '''    report = state.get("report")\n    if isinstance(report, dict):\n        public["report"] = report\n    thread_id = state.get("threadId")\n    if isinstance(thread_id, str) and thread_id:\n        public["threadId"] = thread_id\n    return public\n'''
new_public_tail = '''    report = state.get("report")\n    if isinstance(report, dict):\n        public["report"] = report\n    transcript = state.get("transcript")\n    public["transcript"] = transcript if isinstance(transcript, list) else []\n    public["writerActive"] = bool(state.get("writerActive"))\n    handoff = state.get("threadHandoff")\n    public["threadHandoff"] = (\n        handoff\n        if handoff in ("pending", "bridge-owned", "available", "unavailable")\n        else ("bridge-owned" if public["writerActive"] else "unavailable")\n    )\n    for key in ("workspace", "projectName"):\n        if isinstance(state.get(key), str):\n            public[key] = state[key]\n    thread_id = state.get("threadId")\n    if isinstance(thread_id, str) and thread_id:\n        public["threadId"] = thread_id\n    return public\n'''
text = replace_once(text, old_public_tail, new_public_tail, "public job state")

old_join_text = '''    if join_required:\n        text = (\n            f"Codex background job {public['jobId']} is {public['status']}. "\n            "You MUST call codex-wait with this jobId now and MUST keep calling "\n            "it while the job is queued or running. MUST NOT answer the user "\n            "merely because the background job was submitted."\n        )\n'''
new_join_text = '''    if join_required:\n        text = (\n            f"Codex background job {public['jobId']} is {public['status']}. "\n            "It is durable. You may call codex-wait, inspect codex-job-status, "\n            "steer or cancel the active job, or return later with the same jobId."\n        )\n'''
text = replace_once(text, old_join_text, new_join_text, "job result policy")

old_wait_active = '''    if status in ACTIVE_JOB_STATUSES:\n        text = (\n            f"Codex job {job_id} is still {status}. You MUST call codex-wait "\n            "again with this same jobId now. MUST NOT answer the user yet."\n        )\n'''
new_wait_active = '''    if status in ACTIVE_JOB_STATUSES:\n        text = (\n            f"Codex job {job_id} is still {status}. The job remains durable. "\n            "You may wait again, inspect its transcript/status, steer or cancel it, "\n            "or return control to the user and resume later with the same jobId."\n        )\n'''
text = replace_once(text, old_wait_active, new_wait_active, "wait active text")

old_wait_complete = '''            "You MUST review this result "\n            "against the user's full request now. If work remains, call "\n            "codex-reply-async with the same threadId, then call codex-wait on "\n            "the new jobId.\\n\\nBEGIN UNTRUSTED CODEX OUTPUT\\n"\n'''
new_wait_complete = '''            "Review this result against the user's full request. If work remains "\n            "after this terminal turn, a same-thread codex-reply-async continuation "\n            "can be started.\\n\\nBEGIN UNTRUSTED CODEX OUTPUT\\n"\n'''
text = replace_once(text, old_wait_complete, new_wait_complete, "wait completed text")

old_request = '''            request = {\n                "jobId": job_id,\n                "internalJobId": internal_job_id,\n                "prompt": effective_prompt,\n'''
new_request = '''            request = {\n                "jobId": job_id,\n                "internalJobId": internal_job_id,\n                "userPrompt": prompt,\n                "prompt": effective_prompt,\n'''
text = replace_once(text, old_request, new_request, "raw user prompt")

old_state_head = '''            state = {\n                "jobId": job_id,\n                "internalJobId": internal_job_id,\n                "status": "failed" if allocation_error else "queued",\n'''
new_state_head = '''            state = {\n                "jobId": job_id,\n                "internalJobId": internal_job_id,\n                "status": "failed" if allocation_error else "queued",\n                "workspace": workspace,\n                "projectName": display_name,\n                "writerActive": False,\n                "threadHandoff": "pending",\n                "transcript": [transcript_entry("controller", "prompt", prompt, created_at, "submitted")],\n'''
text = replace_once(text, old_state_head, new_state_head, "initial transcript")

text = replace_once(
    text,
    '            atomic_write_json(path / "request.json", request)\n            atomic_write_json(path / "status.json", state)\n',
    '            atomic_write_json(path / "request.json", request)\n            atomic_write_json(path / "status.json", state)\n            atomic_write_json(path / "controls.json", {"commands": []})\n',
    "control file creation",
)

old_wait_method = '''    def wait(self, job_id, timeout_seconds):\n        deadline = time.monotonic() + timeout_seconds\n        state = self.read(job_id)\n        while state.get("status") in ACTIVE_JOB_STATUSES:\n            remaining = deadline - time.monotonic()\n            if remaining <= 0:\n                break\n            time.sleep(min(JOB_WAIT_POLL_SECONDS, remaining))\n            state = self.read(job_id)\n        return state\n'''
new_wait_method = '''    def _append_control_locked(self, path, state, kind, text):\n        control_path = path / "controls.json"\n        payload = read_json_object(control_path)\n        commands = payload.get("commands")\n        if not isinstance(commands, list) or len(commands) >= JOB_CONTROL_MAX_ITEMS:\n            raise GuardProtocolError("job control limit reached")\n        control_id = str(uuid.uuid4())\n        command = {"id": control_id, "kind": kind, "createdAt": time.time()}\n        field = "prompt" if kind == "steer" else "reason"\n        command[field] = text\n        commands.append(command)\n        atomic_write_json(control_path, {"commands": commands})\n        append_transcript(\n            state, "controller", kind, text, command["createdAt"], "queued", control_id\n        )\n        state["lastEventAt"] = command["createdAt"]\n        state["updatedAt"] = command["createdAt"]\n        atomic_write_json(path / "status.json", state)\n        return control_id\n\n    def steer(self, job_id, prompt):\n        if (\n            not isinstance(prompt, str)\n            or not prompt\n            or len(prompt.encode("utf-8")) > PROMPT_MAX_BYTES\n        ):\n            raise GuardProtocolError("invalid steer prompt")\n        with self._locked_admission():\n            path = self.job_dir(job_id)\n            state = self._state_for_path(path)\n            if state.get("status") != "running" or not state.get("internalTurnId"):\n                raise GuardProtocolError("job has no steerable active turn")\n            self._append_control_locked(path, state, "steer", prompt)\n            return self._state_for_path(path, reconcile=False)\n\n    def cancel(self, job_id, reason=""):\n        if not isinstance(reason, str) or len(reason) > 4000:\n            raise GuardProtocolError("invalid cancel reason")\n        reason = reason.strip()\n        with self._locked_admission():\n            path = self.job_dir(job_id)\n            state = self._state_for_path(path)\n            if state.get("status") in TERMINAL_JOB_STATUSES:\n                return state\n            if state.get("status") == "queued":\n                message = reason or "Codex 后台任务已在启动前取消。"\n                append_transcript(state, "controller", "cancel", message, delivery="applied")\n                _mark_job_interrupted(path, state, message)\n                queued = True\n            else:\n                message = reason or "请求停止当前 Codex 后台任务。"\n                self._append_control_locked(path, state, "cancel", message)\n                queued = False\n        if queued:\n            terminate_verified_job_worker(path)\n            return self.read(job_id)\n        deadline = time.monotonic() + JOB_CANCEL_GRACE_SECONDS\n        state = self.read(job_id)\n        while state.get("status") in ACTIVE_JOB_STATUSES and time.monotonic() < deadline:\n            time.sleep(0.05)\n            state = self.read(job_id)\n        if state.get("status") in ACTIVE_JOB_STATUSES:\n            terminate_verified_job_worker(path)\n            state = self._state_for_path(path, reconcile=False)\n            if state.get("status") in ACTIVE_JOB_STATUSES:\n                _mark_job_interrupted(\n                    path, state, reason or "Codex 后台任务已取消并释放线程写入权。"\n                )\n            state = self._state_for_path(path, reconcile=False)\n        return state\n\n    def wait(self, job_id, timeout_seconds):\n        deadline = time.monotonic() + timeout_seconds\n        state = self.read(job_id)\n        while state.get("status") in ACTIVE_JOB_STATUSES:\n            remaining = deadline - time.monotonic()\n            if remaining <= 0:\n                break\n            time.sleep(min(JOB_WAIT_POLL_SECONDS, remaining))\n            state = self.read(job_id)\n        return state\n'''
text = replace_once(text, old_wait_method, new_wait_method, "job control methods")

old_read_head = '''    def read(self):\n        if self.process.stdout is None:\n            raise GuardProtocolError("Codex App Server stdout unavailable")\n        while b"\\n" not in self.buffer:\n            remaining = self.deadline - time.monotonic()\n            if remaining <= 0:\n                raise JobDeadlineExceeded("Codex job deadline exceeded")\n'''
new_read_head = '''    def read(self, timeout_seconds=None):\n        if self.process.stdout is None:\n            raise GuardProtocolError("Codex App Server stdout unavailable")\n        read_deadline = self.deadline\n        if timeout_seconds is not None:\n            if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:\n                raise GuardProtocolError("invalid App Server read timeout")\n            read_deadline = min(read_deadline, time.monotonic() + timeout_seconds)\n        while b"\\n" not in self.buffer:\n            remaining = read_deadline - time.monotonic()\n            if remaining <= 0:\n                if time.monotonic() >= self.deadline:\n                    raise JobDeadlineExceeded("Codex job deadline exceeded")\n                return None\n'''
text = replace_once(text, old_read_head, new_read_head, "bounded app-server read")

text = replace_once(
    text,
    '''                if event is None:\n                    raise JobDeadlineExceeded("Codex job deadline exceeded")\n''',
    '''                if event is None:\n                    if time.monotonic() >= self.deadline:\n                        raise JobDeadlineExceeded("Codex job deadline exceeded")\n                    return None\n''',
    "windows bounded read",
)
text = replace_once(
    text,
    '''                if not ready:\n                    raise JobDeadlineExceeded("Codex job deadline exceeded")\n''',
    '''                if not ready:\n                    if time.monotonic() >= self.deadline:\n                        raise JobDeadlineExceeded("Codex job deadline exceeded")\n                    return None\n''',
    "posix bounded read",
)

text = replace_once(
    text,
    '''    state = read_json_object(path / "status.json")\n    now = time.time()\n    state.update({\n        "status": "running",\n''',
    '''    state = read_json_object(path / "status.json")\n    if state.get("status") != "queued":\n        return 0 if state.get("status") == "interrupted" else EXIT_PROTOCOL\n    now = time.time()\n    state.update({\n        "status": "running",\n''',
    "queued cancellation race",
)

text = replace_once(
    text,
    '''        "nextAction": "wait",\n        "report": state.get("report") if isinstance(state.get("report"), dict) else initial_job_report(),\n''',
    '''        "nextAction": "wait",\n        "writerActive": False,\n        "threadHandoff": "pending",\n        "report": state.get("report") if isinstance(state.get("report"), dict) else initial_job_report(),\n''',
    "running handoff defaults",
)

old_record_nonlocals = '''    def record_event(message):\n        nonlocal content, final_answer_seen, terminal_status, current_stage\n'''
new_record_nonlocals = '''    def record_event(message):\n        nonlocal content, final_answer_seen, terminal_status, current_stage\n'''
text = replace_once(text, old_record_nonlocals, new_record_nonlocals, "record anchor")

old_update_report = '''                item = params.get("item")\n                update_report_from_item(state, item)\n                current_stage = state.get("phase", current_stage)\n                candidate, is_final = app_server_agent_message(item)\n'''
new_update_report = '''                item = params.get("item")\n                update_report_from_item(state, item)\n                if isinstance(item, dict):\n                    item_type = item.get("type")\n                    if item_type == "agentMessage" and isinstance(item.get("text"), str):\n                        append_transcript(\n                            state, "codex", "message", item["text"],\n                            delivery=item.get("phase", "observed"),\n                        )\n                    elif item_type == "plan" and isinstance(item.get("text"), str):\n                        append_transcript(state, "codex", "plan", item["text"])\n                current_stage = state.get("phase", current_stage)\n                candidate, is_final = app_server_agent_message(item)\n'''
text = replace_once(text, old_update_report, new_update_report, "record transcript")

old_thread_state = '''            "phase": "thread",\n            "activity": "Codex 对话已就绪，准备开始执行。",\n            "lastEventAt": time.time(),\n'''
new_thread_state = '''            "phase": "thread",\n            "activity": "Codex 对话已就绪，准备开始执行。",\n            "writerActive": True,\n            "threadHandoff": "bridge-owned",\n            "lastEventAt": time.time(),\n'''
text = replace_once(text, old_thread_state, new_thread_state, "thread ownership")

old_turn_result_tail = '''        expected_turn_id = turn["id"]\n        if turn.get("status") in ("completed", "failed", "interrupted", "cancelled"):\n            terminal_status = turn["status"]\n            content = content or app_server_turn_message(turn)\n        while not terminal_status:\n            message = client.read()\n            if "method" in message and "id" in message:\n                raise GuardProtocolError("unexpected Codex App Server request")\n            record_event(message)\n'''
new_turn_result_tail = '''        expected_turn_id = turn["id"]\n        state["internalTurnId"] = expected_turn_id\n        state["writerActive"] = True\n        state["threadHandoff"] = "bridge-owned"\n        state["updatedAt"] = time.time()\n        atomic_write_json(path / "status.json", state)\n        processed_control_ids = set()\n        if turn.get("status") in ("completed", "failed", "interrupted", "cancelled"):\n            terminal_status = turn["status"]\n            content = content or app_server_turn_message(turn)\n        while not terminal_status:\n            process_worker_controls(\n                client, path, state, thread_id, expected_turn_id, processed_control_ids\n            )\n            message = client.read(timeout_seconds=JOB_CONTROL_POLL_SECONDS)\n            if message is None:\n                continue\n            if "method" in message and "id" in message:\n                raise GuardProtocolError("unexpected Codex App Server request")\n            if "id" in message and "method" not in message:\n                continue\n            record_event(message)\n'''
text = replace_once(text, old_turn_result_tail, new_turn_result_tail, "worker controls")

old_terminal_branch = '''        if (\n            terminal_status == "completed"\n            and thread_id\n            and content\n            and not missing_scaffold\n        ):\n'''
new_terminal_branch = '''        if terminal_status in ("interrupted", "cancelled"):\n            interruption = content or "Codex 后台任务已中断。"\n            state.update({\n                "status": "interrupted",\n                "threadId": public_thread_id,\n                "internalThreadId": thread_id,\n                "content": interruption,\n                "contentTruncated": content_truncated,\n                "phase": "interrupted",\n                "activity": interruption,\n                "lastEventAt": time.time(),\n                "failureStage": "",\n                "nextAction": "continue" if public_thread_id else "none",\n                "updatedAt": time.time(),\n                "exitCode": 0,\n            })\n            finish_job_report(state, "interrupted", interruption, state["nextAction"])\n        elif (\n            terminal_status == "completed"\n            and thread_id\n            and content\n            and not missing_scaffold\n        ):\n'''
text = replace_once(text, old_terminal_branch, new_terminal_branch, "terminal interruption mapping")

old_finally = '''    finally:\n        if client is not None:\n            client.close()\n    atomic_write_json(path / "status.json", state)\n'''
new_finally = '''    finally:\n        if client is not None:\n            client.close()\n        state["writerActive"] = False\n        state["threadHandoff"] = "available" if public_thread_id else "unavailable"\n        state.pop("internalTurnId", None)\n        state["updatedAt"] = time.time()\n    atomic_write_json(path / "status.json", state)\n'''
text = replace_once(text, old_finally, new_finally, "writer handoff finally")

old_wait_handler = '''        if name == "codex-wait":\n            if set(arguments) != {"jobId"} or not isinstance(\n                arguments.get("jobId"), str\n            ):\n                self.invalid_params(request_id)\n                return\n            try:\n                state = self.job_store.wait(\n                    arguments["jobId"], self.job_wait_seconds\n                )\n            except GuardProtocolError:\n                self.invalid_params(request_id, "Unknown or invalid jobId")\n                return\n            self.emit(wait_tool_result(request_id, state))\n            return\n'''
new_wait_handler = '''        if name == "codex-wait":\n            if (\n                "jobId" not in arguments\n                or set(arguments) - {"jobId", "timeoutSeconds"}\n                or not isinstance(arguments.get("jobId"), str)\n            ):\n                self.invalid_params(request_id)\n                return\n            timeout_seconds = arguments.get("timeoutSeconds", self.job_wait_seconds)\n            if (\n                isinstance(timeout_seconds, bool)\n                or not isinstance(timeout_seconds, (int, float))\n                or not math.isfinite(timeout_seconds)\n                or timeout_seconds < 0.01\n                or timeout_seconds > JOB_WAIT_MAX_SECONDS\n            ):\n                self.invalid_params(request_id)\n                return\n            try:\n                state = self.job_store.wait(arguments["jobId"], float(timeout_seconds))\n            except GuardProtocolError:\n                self.invalid_params(request_id, "Unknown or invalid jobId")\n                return\n            self.emit(wait_tool_result(request_id, state))\n            return\n        if name == "codex-job-steer":\n            if set(arguments) != {"jobId", "prompt"}:\n                self.invalid_params(request_id)\n                return\n            try:\n                state = self.job_store.steer(arguments.get("jobId"), arguments.get("prompt"))\n            except GuardProtocolError as error:\n                self.invalid_params(request_id, str(error)[:200])\n                return\n            self.emit(job_tool_result(request_id, state))\n            return\n        if name == "codex-job-cancel":\n            if "jobId" not in arguments or set(arguments) - {"jobId", "reason"}:\n                self.invalid_params(request_id)\n                return\n            try:\n                state = self.job_store.cancel(\n                    arguments.get("jobId"), arguments.get("reason", "")\n                )\n            except GuardProtocolError as error:\n                self.invalid_params(request_id, str(error)[:200])\n                return\n            self.emit(job_tool_result(request_id, state))\n            return\n'''
text = replace_once(text, old_wait_handler, new_wait_handler, "async control handlers")

text = replace_once(
    text,
    '''                "codex-job-open",\n                "codex-job-status",\n            ):\n''',
    '''                "codex-job-open",\n                "codex-job-status",\n                "codex-job-steer",\n                "codex-job-cancel",\n            ):\n''',
    "async routing",
)

SOURCE.write_text(text, encoding="utf-8")
MIRROR.write_text(text, encoding="utf-8")

skill = SKILL.read_text(encoding="utf-8")
skill = skill.replace(
    "- When the task targets the bridge's existing workspace or an existing\n  repository under it, MUST call `codex-run(prompt)`. It returns a durable job\n  immediately; call `codex-wait(jobId)` next and keep calling it while the\n  status is `queued` or `running`.\n",
    "- When the task targets the bridge's existing workspace or an existing\n  repository under it, use `codex-run(prompt)`. It returns a durable job\n  immediately. Use `codex-wait(jobId, timeoutSeconds?)` when foreground joining\n  is useful, or `codex-job-status(jobId)` for an immediate transcript/status\n  snapshot. The job remains recoverable if you return control to the user.\n",
)
skill = skill.replace(
    "  The call returns a durable job immediately. MUST call\n  `codex-wait(jobId)` next and keep calling it with the same job ID while the\n  status is `queued` or `running`; do not answer the user merely because the\n  job was submitted.\n",
    "  The call returns a durable job immediately. Join it with `codex-wait` when\n  useful, inspect it with `codex-job-status`, and preserve the job ID for later\n  recovery.\n",
)
skill = skill.replace(
    "- When `codex-wait` returns `completed`, review its Codex result against the\n",
    "- While a job is active, use `codex-job-steer(jobId, prompt)` to add or\n  correct instructions inside the exact active turn. Use\n  `codex-job-cancel(jobId, reason?)` to stop only that job. Cancellation is\n  idempotent and releases the bridge writer before advertising Desktop handoff.\n- `codex-job-status` exposes the public controller/Codex transcript. Use\n  `codex-thread-read` for persisted turn history and command/file activity when\n  the user wants to inspect the concrete conversation. Private reasoning is not\n  exposed. `writerActive=true` / `threadHandoff=bridge-owned` means Codex Desktop\n  must not become a second writer; `threadHandoff=available` means the bridge\n  has released the writer and the thread can be taken over from Codex Desktop.\n- When `codex-wait` returns `completed`, review its Codex result against the\n",
)
skill = skill.replace(
    "- Stop issuing MCP calls only when the requested work and verification are\n  complete, material user input is required, or a real terminal blocker exists.\n",
    "- Continuous foreground polling is a controller choice, not a bridge\n  invariant. Stop polling when the user needs control, another foreground action\n  is more useful, or the durable job can be resumed later. Do not claim\n  unsolicited delivery while ChatGPT is inactive.\n",
)
SKILL.write_text(skill, encoding="utf-8")

controller = CONTROLLER.read_text(encoding="utf-8")
controller += "\n\n## Live control and handoff\n\nUse `codex-job-status` for an immediate public transcript and lifecycle snapshot. Use `codex-job-steer` to add instructions to an active turn and `codex-job-cancel` to stop only that durable job. `codex-wait` is a bounded join, not a requirement to monopolize the foreground. Never create a second writer for a bridge-owned thread; wait for `threadHandoff=available` before telling the user the thread is ready for writable Codex Desktop takeover.\n"
CONTROLLER.write_text(controller, encoding="utf-8")

contract = CONTRACT.read_text(encoding="utf-8")
contract += "\n\n## Scoped job controls\n\n`codex-job-status(jobId)` is the immediate model-visible snapshot. It includes the bounded public transcript, report, and writer/handoff state. `codex-job-steer(jobId,prompt)` targets the exact active turn through App Server `turn/steer`. `codex-job-cancel(jobId,reason?)` is idempotent, requests exact `turn/interrupt` first, and only then falls back to verified termination of that job's bridge-owned worker. `codex-wait(jobId,timeoutSeconds?)` is a bounded join and may return an active state.\n"
CONTRACT.write_text(contract, encoding="utf-8")

tasks = TASKS.read_text(encoding="utf-8")
for number in range(2, 9):
    tasks = tasks.replace(f"- [ ] T{number}", f"- [x] T{number}")
TASKS.write_text(tasks, encoding="utf-8")
