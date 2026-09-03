# Executor Session Layer & State Machine
# Implements session-level authorization lifecycle and durable persistence.

import json
import os
import time
import uuid
from pathlib import Path


VALID_EXECUTORS = frozenset({"codex", "pi", "antigravity", "mock"})
VALID_PROFILES = frozenset({"safe", "build", "trusted"})

STATUS_PENDING = "pending_approval"
STATUS_AUTHORIZED_IDLE = "authorized_idle"
STATUS_RUNNING = "running"
STATUS_REAUTH_REQUIRED = "reauth_required"
STATUS_DENIED = "denied"
STATUS_REVOKED = "revoked"


class SessionError(Exception):
    pass


class SessionNotFoundError(SessionError):
    pass


class SessionNotAuthorizedError(SessionError):
    pass


class SessionStateConflictError(SessionError):
    pass


class ExecutorSession:
    def __init__(
        self,
        session_id,
        executor,
        workspace,
        permission_profile,
        display_objective,
        status=STATUS_PENDING,
        native_session_id="",
        current_job_id=None,
        created_at=None,
        approved_at=None,
        revoked_at=None,
        runtime_fingerprint="",
    ):
        self.session_id = session_id
        self.executor = executor.lower()
        self.workspace = os.path.realpath(str(workspace)) if os.path.exists(str(workspace)) else str(workspace)
        self.permission_profile = permission_profile.lower()
        self.display_objective = display_objective or ""
        self.status = status
        self.native_session_id = native_session_id or ""
        self.current_job_id = current_job_id
        self.created_at = created_at or time.time()
        self.approved_at = approved_at
        self.revoked_at = revoked_at
        self.runtime_fingerprint = runtime_fingerprint or ""

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "executor": self.executor,
            "workspace": self.workspace,
            "permission_profile": self.permission_profile,
            "display_objective": self.display_objective,
            "status": self.status,
            "native_session_id": self.native_session_id,
            "current_job_id": self.current_job_id,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "revoked_at": self.revoked_at,
            "runtime_fingerprint": self.runtime_fingerprint,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            session_id=data["session_id"],
            executor=data["executor"],
            workspace=data["workspace"],
            permission_profile=data["permission_profile"],
            display_objective=data.get("display_objective", ""),
            status=data.get("status", STATUS_PENDING),
            native_session_id=data.get("native_session_id", ""),
            current_job_id=data.get("current_job_id"),
            created_at=data.get("created_at"),
            approved_at=data.get("approved_at"),
            revoked_at=data.get("revoked_at"),
            runtime_fingerprint=data.get("runtime_fingerprint", ""),
        )


class SessionStore:
    def __init__(self, storage_dir, runtime_fingerprint=""):
        self.storage_dir = Path(storage_dir)
        self.sessions_dir = self.storage_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_fingerprint = runtime_fingerprint
        self._cache = {}
        self._load_all()

    def _session_file(self, session_id):
        return self.sessions_dir / f"{session_id}.json"

    def _load_all(self):
        for path in self.sessions_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                session = ExecutorSession.from_dict(data)
                # Check runtime fingerprint shift on load
                if self.runtime_fingerprint and session.runtime_fingerprint:
                    if session.runtime_fingerprint != self.runtime_fingerprint:
                        if session.status in (STATUS_AUTHORIZED_IDLE, STATUS_RUNNING):
                            session.status = STATUS_REAUTH_REQUIRED
                            session.current_job_id = None
                            self._save_session(session)
                self._cache[session.session_id] = session
            except Exception:
                continue

    def _save_session(self, session):
        self._cache[session.session_id] = session
        path = self._session_file(session.session_id)
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
        temp_path.replace(path)

    def prepare_session(self, executor, workspace, permission_profile, objective=""):
        executor_clean = str(executor).lower().strip()
        if executor_clean not in VALID_EXECUTORS:
            raise SessionError(f"Unsupported executor '{executor}'. Supported: {sorted(VALID_EXECUTORS)}")

        profile_clean = str(permission_profile).lower().strip()
        if profile_clean not in VALID_PROFILES:
            raise SessionError(f"Unsupported permission profile '{permission_profile}'. Supported: {sorted(VALID_PROFILES)}")

        canonical_workspace = os.path.realpath(str(workspace))
        if not os.path.exists(canonical_workspace) or not os.path.isdir(canonical_workspace):
            raise SessionError(f"Workspace directory does not exist: {workspace}")

        session_id = str(uuid.uuid4())
        session = ExecutorSession(
            session_id=session_id,
            executor=executor_clean,
            workspace=canonical_workspace,
            permission_profile=profile_clean,
            display_objective=str(objective or ""),
            status=STATUS_PENDING,
            runtime_fingerprint=self.runtime_fingerprint,
        )
        self._save_session(session)
        return session

    def get_session(self, session_id):
        session = self._cache.get(session_id)
        if session is None:
            path = self._session_file(session_id)
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    session = ExecutorSession.from_dict(data)
                    self._cache[session_id] = session
                except Exception:
                    pass
        if session is None:
            raise SessionNotFoundError(f"Executor session '{session_id}' not found")
        return session

    def list_sessions(self, executor=None, status=None):
        results = list(self._cache.values())
        if executor:
            results = [s for s in results if s.executor == executor.lower()]
        if status:
            results = [s for s in results if s.status == status]
        return sorted(results, key=lambda s: s.created_at, reverse=True)

    def allow_session(self, session_id):
        """
        Executed only by local human approval handler!
        """
        session = self.get_session(session_id)
        if session.status == STATUS_REVOKED:
            raise SessionStateConflictError("Revoked session cannot be re-authorized. Please create a new session.")
        session.status = STATUS_AUTHORIZED_IDLE
        session.approved_at = time.time()
        session.runtime_fingerprint = self.runtime_fingerprint
        self._save_session(session)
        return session

    def deny_session(self, session_id):
        session = self.get_session(session_id)
        session.status = STATUS_DENIED
        self._save_session(session)
        return session

    def start_turn(self, session_id, job_id, native_session_id=""):
        session = self.get_session(session_id)
        if session.status == STATUS_PENDING:
            raise SessionNotAuthorizedError("Session is pending local human approval. Turn start rejected.")
        if session.status == STATUS_REAUTH_REQUIRED:
            raise SessionNotAuthorizedError("Session requires local human re-authorization. Turn start rejected.")
        if session.status == STATUS_REVOKED:
            raise SessionNotAuthorizedError("Session has been revoked. Turn start rejected.")
        if session.status == STATUS_DENIED:
            raise SessionNotAuthorizedError("Session was denied by human. Turn start rejected.")
        if session.status == STATUS_RUNNING:
            raise SessionStateConflictError(f"Session is already running job '{session.current_job_id}'. Concurrent turns prohibited.")

        session.status = STATUS_RUNNING
        session.current_job_id = job_id
        if native_session_id:
            session.native_session_id = native_session_id
        self._save_session(session)
        return session

    def finish_turn(self, session_id, job_id):
        try:
            session = self.get_session(session_id)
        except SessionNotFoundError:
            return
        if session.status == STATUS_RUNNING and (session.current_job_id == job_id or not session.current_job_id):
            session.status = STATUS_AUTHORIZED_IDLE
            session.current_job_id = None
            self._save_session(session)

    def cancel_turn(self, session_id, job_id=None):
        try:
            session = self.get_session(session_id)
        except SessionNotFoundError:
            return
        if session.status == STATUS_RUNNING:
            session.status = STATUS_AUTHORIZED_IDLE
            session.current_job_id = None
            self._save_session(session)

    def revoke_session(self, session_id):
        session = self.get_session(session_id)
        session.status = STATUS_REVOKED
        session.revoked_at = time.time()
        session.current_job_id = None
        self._save_session(session)
        return session

    def find_authorized_session(self, executor, workspace, permission_profile=None):
        canonical_workspace = os.path.realpath(str(workspace))
        norm_ws = os.path.normcase(canonical_workspace)
        candidates = self.list_sessions(executor=executor)
        for s in candidates:
            if s.status in (STATUS_AUTHORIZED_IDLE, STATUS_RUNNING):
                if os.path.normcase(s.workspace) == norm_ws:
                    if permission_profile is None or s.permission_profile == permission_profile.lower():
                        return s
        return None
