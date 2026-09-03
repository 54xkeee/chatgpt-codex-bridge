# Generic Executor MCP Tools Definitions & Dispatcher
# Implements the 12 unified executor_* tools for ChatGPT supervision.

import time
import uuid
from .capability import CapabilityProtocolError
from .session import (
    STATUS_PENDING,
    STATUS_AUTHORIZED_IDLE,
    STATUS_RUNNING,
    STATUS_REVOKED,
    STATUS_REAUTH_REQUIRED,
    SessionNotAuthorizedError,
    SessionStateConflictError,
    SessionNotFoundError,
)
from .workspace_lock import WorkspaceLockedError


def get_generic_tools_schema():
    return [
        {
            "name": "executor_list",
            "title": "List Available Executors",
            "description": "Discover installed executors (Codex, Pi, Antigravity) and their capabilities. Read-only.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
        {
            "name": "executor_session_prepare",
            "title": "Prepare Executor Session",
            "description": (
                "Prepare a new executor session awaiting local human authorization. "
                "Does NOT launch any process or consume model calls until approved locally."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "executor": {
                        "type": "string",
                        "enum": ["codex", "pi", "antigravity", "mock"],
                        "description": "The target executor worker.",
                    },
                    "workspace": {
                        "type": "string",
                        "description": "Absolute canonical directory path of the target workspace.",
                    },
                    "permission_profile": {
                        "type": "string",
                        "enum": ["safe", "build", "trusted"],
                        "description": "Permission profile for the session (safe=read-only, build=normal, trusted=elevated).",
                    },
                    "objective": {
                        "type": "string",
                        "description": "Human-readable summary of the session's initial objective.",
                    },
                },
                "required": ["executor", "workspace", "permission_profile"],
                "additionalProperties": False,
            },
        },
        {
            "name": "executor_session_list",
            "title": "List Executor Sessions",
            "description": "List existing executor sessions with their authorization and lifecycle status.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "executor": {"type": "string", "enum": ["codex", "pi", "antigravity", "mock"]},
                    "status": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "executor_session_get",
            "title": "Get Executor Session",
            "description": "Get detailed state and authorization information for an executor session.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Signed session capability or raw session UUID."},
                },
                "required": ["session_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "executor_session_revoke",
            "title": "Revoke Executor Session",
            "description": "Revoke an executor session permanently, terminating any running processes and releasing locks.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Signed session capability or raw session UUID."},
                },
                "required": ["session_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "executor_turn_start",
            "title": "Start Executor Turn",
            "description": (
                "Start an execution turn in an AUTHORIZED session. "
                "Requires zero repeated human approvals within an authorized session."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Signed session capability."},
                    "objective": {"type": "string", "description": "Specific instruction/objective for this turn."},
                    "context": {"type": "string", "description": "Additional context or file references."},
                    "constraints": {"type": "array", "items": {"type": "string"}},
                    "success_criteria": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["session_id", "objective"],
                "additionalProperties": False,
            },
        },
        {
            "name": "executor_job_status",
            "title": "Get Executor Job Status",
            "description": "Check current phase, activity, and status of an executor job.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Signed job capability."},
                },
                "required": ["job_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "executor_job_wait",
            "title": "Wait For Executor Job",
            "description": "Wait for an executor job to complete or progress, bounded by timeout.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Signed job capability."},
                    "timeout_seconds": {"type": "number", "default": 30.0, "maximum": 55.0},
                },
                "required": ["job_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "executor_job_steer",
            "title": "Steer Executor Job",
            "description": "Provide steering guidance into an actively running turn without stopping the session.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Signed job capability."},
                    "message": {"type": "string", "description": "Steering guidance for the running agent."},
                },
                "required": ["job_id", "message"],
                "additionalProperties": False,
            },
        },
        {
            "name": "executor_job_cancel",
            "title": "Cancel Executor Turn",
            "description": "Cancel currently running turn, returning the session to AUTHORIZED_IDLE for subsequent turns.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Signed job capability."},
                },
                "required": ["job_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "executor_job_result",
            "title": "Get Executor Job Result",
            "description": "Get structured outcome report (changed files, commands, checks, blockers) for a completed turn.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Signed job capability."},
                },
                "required": ["job_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "executor_job_events",
            "title": "Get Executor Job Events",
            "description": "Read normalized chronological execution events for a turn.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Signed job capability."},
                    "after_index": {"type": "integer", "default": 0},
                },
                "required": ["job_id"],
                "additionalProperties": False,
            },
        },
    ]


class GenericToolsDispatcher:
    def __init__(self, session_store, workspace_lock_mgr, capability_codec, adapters, approval_server=None):
        self.session_store = session_store
        self.workspace_lock_mgr = workspace_lock_mgr
        self.capability_codec = capability_codec
        self.adapters = adapters
        self.approval_server = approval_server
        self._jobs = {} # internal_job_id -> job dict

    def _resolve_session_id(self, cap_or_id):
        try:
            return self.capability_codec.decode("session", cap_or_id)
        except Exception:
            try:
                return self.capability_codec.decode("session-request", cap_or_id)
            except Exception:
                # Try raw UUID if valid
                try:
                    uuid.UUID(str(cap_or_id))
                    return str(cap_or_id)
                except Exception:
                    raise CapabilityProtocolError("invalid capability")

    def _resolve_job_id(self, cap_or_id):
        try:
            return self.capability_codec.decode("job", cap_or_id)
        except Exception:
            try:
                uuid.UUID(str(cap_or_id))
                return str(cap_or_id)
            except Exception:
                raise CapabilityProtocolError("invalid capability")

    def _sync_job_completion(self, job_id, outcome):
        if outcome in ("completed", "failed", "cancelled"):
            job = self._jobs.get(job_id)
            if job and job.get("status") == "running":
                job["status"] = outcome
                session_id = job.get("session_id")
                if session_id:
                    self.workspace_lock_mgr.release_turn_write_lock(job.get("workspace", ""), job_id)
                    self.session_store.finish_turn(session_id, job_id)

    def dispatch(self, name, arguments):
        if not isinstance(arguments, dict):
            arguments = {}

        if name == "executor_list":
            result = []
            for adapter_id, adapter in self.adapters.items():
                result.append(adapter.detect())
            return {"executors": result}

        elif name == "executor_session_prepare":
            # Security verification: ensure no approved bypass was injected
            for forbidden in ("approved", "approval_token", "force", "skip_approval", "auto_approve"):
                if forbidden in arguments:
                    return {"error": f"Forbidden parameter: {forbidden}"}

            executor = arguments["executor"]
            workspace = arguments["workspace"]
            permission_profile = arguments["permission_profile"]
            objective = arguments.get("objective", "")

            session = self.session_store.prepare_session(
                executor=executor,
                workspace=workspace,
                permission_profile=permission_profile,
                objective=objective,
            )

            signed_req = self.capability_codec.encode("session-request", session.session_id)
            approval_url = self.approval_server.get_url() if self.approval_server else "http://127.0.0.1:18230/"
            return {
                "session_request_id": signed_req,
                "status": STATUS_PENDING,
                "executor": session.executor,
                "workspace": session.workspace,
                "permission_profile": session.permission_profile,
                "approval_url": approval_url,
                "message": f"Session created. Local human authorization is required at: {approval_url}",
            }

        elif name == "executor_session_list":
            sessions = self.session_store.list_sessions(
                executor=arguments.get("executor"),
                status=arguments.get("status"),
            )
            out = []
            for s in sessions:
                item = s.to_dict()
                aud = "session" if s.status in (STATUS_AUTHORIZED_IDLE, STATUS_RUNNING) else "session-request"
                item["capability"] = self.capability_codec.encode(aud, s.session_id)
                out.append(item)
            return {"sessions": out}

        elif name == "executor_session_get":
            session_id = self._resolve_session_id(arguments["session_id"])
            session = self.session_store.get_session(session_id)
            item = session.to_dict()
            aud = "session" if session.status in (STATUS_AUTHORIZED_IDLE, STATUS_RUNNING) else "session-request"
            item["capability"] = self.capability_codec.encode(aud, session.session_id)
            return item

        elif name == "executor_session_revoke":
            session_id = self._resolve_session_id(arguments["session_id"])
            session = self.session_store.get_session(session_id)
            # Release write locks
            self.workspace_lock_mgr.release_all_for_session(session_id)
            # Terminate adapter
            adapter = self.adapters.get(session.executor)
            if adapter:
                adapter.dispose(session_id)
            self.session_store.revoke_session(session_id)
            return {"status": STATUS_REVOKED, "session_id": session_id}

        elif name == "executor_turn_start":
            session_id = self._resolve_session_id(arguments["session_id"])
            session = self.session_store.get_session(session_id)
            if session.status != STATUS_AUTHORIZED_IDLE:
                raise SessionNotAuthorizedError(
                    f"Cannot start turn in session with status '{session.status}'. Must be '{STATUS_AUTHORIZED_IDLE}'."
                )

            job_id = str(uuid.uuid4())
            # Acquire Turn Write Lock if BUILD or TRUSTED
            self.workspace_lock_mgr.acquire_turn_write_lock(
                workspace=session.workspace,
                session_id=session_id,
                job_id=job_id,
                permission_profile=session.permission_profile,
            )

            # Transition session to RUNNING
            self.session_store.start_turn(session_id, job_id)

            # Delegate to adapter
            adapter = self.adapters.get(session.executor)
            if not adapter:
                raise ValueError(f"Executor adapter '{session.executor}' not configured")

            adapter_res = adapter.start_turn(session, job_id, arguments)
            signed_job = self.capability_codec.encode("job", job_id)
            signed_session = self.capability_codec.encode("session", session_id)

            self._jobs[job_id] = {
                "job_id": job_id,
                "session_id": session_id,
                "executor": session.executor,
                "workspace": session.workspace,
                "status": "running",
                "started_at": time.time(),
                "objective": arguments.get("objective", ""),
            }

            return {
                "status": "started",
                "session_id": signed_session,
                "job_id": signed_job,
                "objective": arguments.get("objective", ""),
                "adapter": adapter_res,
            }

        elif name == "executor_job_status":
            job_id = self._resolve_job_id(arguments["job_id"])
            job = self._jobs.get(job_id, {})
            executor = job.get("executor", "mock")
            adapter = self.adapters.get(executor)
            result = adapter.get_result(job_id) if adapter else {}
            outcome = result.get("outcome", job.get("status", "unknown"))
            self._sync_job_completion(job_id, outcome)
            return {
                "job_id": self.capability_codec.encode("job", job_id),
                "status": outcome,
                "phase": outcome,
                "activity": f"{executor.upper()} execution {outcome}",
                "objective": job.get("objective", ""),
                "started_at": job.get("started_at"),
            }

        elif name == "executor_job_wait":
            job_id = self._resolve_job_id(arguments["job_id"])
            timeout = min(float(arguments.get("timeout_seconds", 30.0)), 55.0)
            job = self._jobs.get(job_id, {})
            executor = job.get("executor", "mock")
            adapter = self.adapters.get(executor)

            start_t = time.monotonic()
            poll_interval = 0.1
            while time.monotonic() - start_t < timeout:
                if adapter:
                    res = adapter.get_result(job_id)
                    outcome = res.get("outcome", "running")
                    if outcome in ("completed", "failed", "cancelled"):
                        self._sync_job_completion(job_id, outcome)
                        return {
                            "status": outcome,
                            "completed": True,
                            "job_id": self.capability_codec.encode("job", job_id),
                            "result": res,
                        }
                time.sleep(poll_interval)

            return {
                "status": "running",
                "completed": False,
                "job_id": self.capability_codec.encode("job", job_id),
            }

        elif name == "executor_job_steer":
            job_id = self._resolve_job_id(arguments["job_id"])
            message = arguments["message"]
            job = self._jobs.get(job_id, {})
            adapter = self.adapters.get(job.get("executor", "mock"))
            if not adapter:
                raise ValueError("Adapter not found for job")
            success = adapter.steer(job_id, message)
            return {"job_id": self.capability_codec.encode("job", job_id), "steer_delivered": success}

        elif name == "executor_job_cancel":
            job_id = self._resolve_job_id(arguments["job_id"])
            job = self._jobs.get(job_id, {})
            adapter = self.adapters.get(job.get("executor", "mock"))
            if adapter:
                adapter.cancel(job_id)

            session_id = job.get("session_id")
            if session_id:
                # Release write lock
                self.workspace_lock_mgr.release_turn_write_lock(job.get("workspace", ""), job_id)
                # Transition session back to AUTHORIZED_IDLE
                self.session_store.cancel_turn(session_id, job_id)

            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "cancelled"

            return {
                "status": "cancelled",
                "job_id": self.capability_codec.encode("job", job_id),
                "session_status": STATUS_AUTHORIZED_IDLE,
                "message": "Turn cancelled. Session returned to AUTHORIZED_IDLE for follow-up turns.",
            }

        elif name == "executor_job_result":
            job_id = self._resolve_job_id(arguments["job_id"])
            job = self._jobs.get(job_id, {})
            adapter = self.adapters.get(job.get("executor", "mock"))
            res = adapter.get_result(job_id) if adapter else {}
            outcome = res.get("outcome") if isinstance(res, dict) else None
            if outcome:
                self._sync_job_completion(job_id, outcome)
            return res


        elif name == "executor_job_events":
            job_id = self._resolve_job_id(arguments["job_id"])
            after_index = int(arguments.get("after_index", 0))
            job = self._jobs.get(job_id, {})
            adapter = self.adapters.get(job.get("executor", "mock"))
            events = adapter.poll_events(job_id, after_index=after_index) if adapter else []
            return {"job_id": self.capability_codec.encode("job", job_id), "events": events}

        raise ValueError(f"Unknown executor tool: {name}")
