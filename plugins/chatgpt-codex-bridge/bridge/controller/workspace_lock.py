# Workspace Write Lock Manager for Single Writer Enforcement
# Ties lock ownership strictly to active Turn / Job, NOT entire Session.

import os
import threading
import time


class WorkspaceLockError(Exception):
    pass


class WorkspaceLockedError(WorkspaceLockError):
    def __init__(self, workspace, owner_session, owner_job, permission_profile):
        super().__init__(
            f"Workspace '{workspace}' is locked by active session '{owner_session}' "
            f"(job '{owner_job}', permission '{permission_profile}'). Concurrent write execution is prohibited."
        )
        self.workspace = workspace
        self.owner_session = owner_session
        self.owner_job = owner_job
        self.permission_profile = permission_profile


class WorkspaceLockManager:
    def __init__(self):
        self._lock = threading.Lock()
        # map: canonical_workspace -> { "session_id": str, "job_id": str, "permission": str, "acquired_at": float }
        self._active_locks = {}

    @staticmethod
    def _canonical(path):
        resolved = os.path.realpath(str(path)) if os.path.exists(str(path)) else os.path.abspath(str(path))
        return os.path.normcase(resolved)

    def acquire_turn_write_lock(self, workspace, session_id, job_id, permission_profile):
        """
        Acquires exclusive write lock for a BUILD or TRUSTED turn.
        SAFE turns are read-only and do not require the write lock.
        """
        if permission_profile.lower() == "safe":
            return True

        canonical = self._canonical(workspace)
        with self._lock:
            existing = self._active_locks.get(canonical)
            if existing is not None:
                # If current turn already holds it, idempotent success
                if existing.get("job_id") == job_id:
                    return True
                raise WorkspaceLockedError(
                    workspace=workspace,
                    owner_session=existing.get("session_id", ""),
                    owner_job=existing.get("job_id", ""),
                    permission_profile=existing.get("permission", ""),
                )

            self._active_locks[canonical] = {
                "session_id": session_id,
                "job_id": job_id,
                "permission": permission_profile,
                "acquired_at": time.time(),
                "display_workspace": str(workspace),
            }
            return True

    def release_turn_write_lock(self, workspace, job_id=None):
        """
        Releases write lock when a turn finishes, fails, is cancelled, or is revoked.
        """
        canonical = self._canonical(workspace)
        with self._lock:
            existing = self._active_locks.get(canonical)
            if existing is not None:
                if job_id is None or existing.get("job_id") == job_id:
                    del self._active_locks[canonical]
                    return True
            return False

    def release_all_for_session(self, session_id):
        """
        Releases any locks held by any turn in this session (e.g. upon revoke).
        """
        with self._lock:
            to_remove = [k for k, v in self._active_locks.items() if v.get("session_id") == session_id]
            for k in to_remove:
                del self._active_locks[k]

    def get_lock_info(self, workspace):
        canonical = self._canonical(workspace)
        with self._lock:
            existing = self._active_locks.get(canonical)
            if existing is None:
                return None
            return dict(existing)

    def is_locked(self, workspace):
        return self.get_lock_info(workspace) is not None
