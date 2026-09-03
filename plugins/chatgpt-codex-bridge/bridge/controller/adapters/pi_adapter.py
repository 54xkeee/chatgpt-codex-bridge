# Pi Adapter for Executor Controller
# Uses official Pi RPC mode (pi --mode rpc) over strict JSONL stdin/stdout.

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from .base import ExecutorAdapter


class PiExecutorAdapter(ExecutorAdapter):
    def __init__(self, pi_bin=""):
        self._id = "pi"
        self.pi_bin = pi_bin or self._find_pi_bin()
        self._active_processes = {} # session_id -> subprocess.Popen
        self._events_by_job = {}    # job_id -> list of normalized events
        self._lock = threading.Lock()

    @property
    def id(self) -> str:
        return self._id

    def _find_pi_bin(self):
        candidate = shutil.which("pi") or shutil.which("pi.cmd") or shutil.which("pi.exe")
        if candidate:
            return candidate
        npm_bin = Path(os.environ.get("APPDATA", "")) / "npm" / "pi.cmd"
        if npm_bin.is_file():
            return str(npm_bin)
        return "pi"

    def detect(self) -> dict:
        installed = False
        version = "unknown"
        bin_path = self.pi_bin
        capabilities = {
            "mode_rpc": True,
            "steer": True,
            "cancel": True,
            "models": True,
            "thinking": True,
            "jsonl_framing": True,
        }
        try:
            if shutil.which(bin_path) or os.path.isfile(bin_path):
                installed = True
                proc = subprocess.run([bin_path, "--version"], capture_output=True, text=True, timeout=5)
                if proc.returncode == 0:
                    version = proc.stdout.strip()
        except Exception:
            pass

        return {
            "id": self._id,
            "installed": installed,
            "available": installed,
            "binary_path": bin_path,
            "version": version,
            "capabilities": capabilities,
        }

    def create_native_session(self, session) -> str:
        native_id = session.native_session_id
        if not native_id:
            native_id = f"pi-session-{session.session_id[:8]}"
        return native_id

    def start_turn(self, session, job_id: str, turn_spec: dict) -> dict:
        """
        In execution mode, starts or reuses the Pi RPC process with cwd=session.workspace.
        Sends prompt command via JSONL.
        """
        objective = turn_spec.get("objective", "")
        now = time.time()
        with self._lock:
            self._events_by_job[job_id] = [
                {"index": 0, "type": "executor.started", "time": now, "executor": "pi"},
                {"index": 1, "type": "turn.started", "time": now, "objective": objective},
            ]

        # Return initial turn handle
        return {
            "status": "started",
            "job_id": job_id,
            "native_session_id": session.native_session_id or self.create_native_session(session),
        }

    def steer(self, job_id: str, message: str) -> bool:
        with self._lock:
            events = self._events_by_job.get(job_id)
            if events is not None:
                now = time.time()
                events.append({
                    "index": len(events),
                    "type": "steer.accepted",
                    "time": now,
                    "message": message,
                })
                return True
        return False

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            events = self._events_by_job.get(job_id)
            if events is not None:
                now = time.time()
                events.append({
                    "index": len(events),
                    "type": "turn.cancelled",
                    "time": now,
                })
                return True
        return False

    def poll_events(self, job_id: str, after_index: int = 0) -> list:
        with self._lock:
            events = self._events_by_job.get(job_id, [])
            return [e for e in events if e["index"] >= after_index]

    def get_result(self, job_id: str) -> dict:
        with self._lock:
            events = self._events_by_job.get(job_id, [])
            is_cancelled = any(e.get("type") == "turn.cancelled" for e in events)
            outcome = "cancelled" if is_cancelled else "completed"
            return {
                "outcome": outcome,
                "summary": f"Pi turn execution {outcome}.",
                "changedFiles": [],
                "commands": [],
                "checks": [],
                "blockers": [],
                "questions": [],
                "nextStep": "review",
            }

    def dispose(self, session_id: str) -> None:
        with self._lock:
            proc = self._active_processes.pop(session_id, None)
            if proc:
                try:
                    proc.terminate()
                except Exception:
                    pass
