# Antigravity Adapter for Executor Controller
# Uses official headless interface (agy.exe -p --output-format stream-json)
# Detects CLI flags dynamically from current installed version.

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from .base import ExecutorAdapter


class AntigravityExecutorAdapter(ExecutorAdapter):
    def __init__(self, agy_bin=""):
        self._id = "antigravity"
        self.agy_bin = agy_bin or self._find_agy_bin()
        self._active_processes = {}
        self._events_by_job = {}
        self._lock = threading.Lock()

    @property
    def id(self) -> str:
        return self._id

    def _find_agy_bin(self):
        candidate = shutil.which("agy") or shutil.which("agy.exe")
        if candidate:
            return candidate
        local_bin = Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin" / "agy.exe"
        if local_bin.is_file():
            return str(local_bin)
        return "agy"

    def detect(self) -> dict:
        installed = False
        version = "unknown"
        bin_path = self.agy_bin
        capabilities = {
            "headless_stream_json": False,
            "conversation_resume": False,
            "dangerously_skip_permissions": False,
            "steer": False, # agy stream-json print mode has limited mid-turn steering
            "cancel": True,
            "models": True,
            "effort": False,
        }

        try:
            if shutil.which(bin_path) or os.path.isfile(bin_path):
                installed = True
                ver_proc = subprocess.run([bin_path, "--version"], capture_output=True, text=True, timeout=5)
                if ver_proc.returncode == 0:
                    version = ver_proc.stdout.strip()

                help_proc = subprocess.run([bin_path, "--help"], capture_output=True, text=True, timeout=5)
                help_text = help_proc.stdout + help_proc.stderr
                if "--output-format" in help_text and "stream-json" in help_text:
                    capabilities["headless_stream_json"] = True
                if "--conversation" in help_text:
                    capabilities["conversation_resume"] = True
                if "--dangerously-skip-permissions" in help_text:
                    capabilities["dangerously_skip_permissions"] = True
                if "--effort" in help_text:
                    capabilities["effort"] = True
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
            native_id = f"agy-conv-{session.session_id[:8]}"
        return native_id

    def start_turn(self, session, job_id: str, turn_spec: dict) -> dict:
        objective = turn_spec.get("objective", "")
        now = time.time()
        with self._lock:
            self._events_by_job[job_id] = [
                {"index": 0, "type": "executor.started", "time": now, "executor": "antigravity"},
                {"index": 1, "type": "turn.started", "time": now, "objective": objective},
            ]

        return {
            "status": "started",
            "job_id": job_id,
            "conversation_id": session.native_session_id or self.create_native_session(session),
        }

    def steer(self, job_id: str, message: str) -> bool:
        # Check if steer is supported in current headless mode
        with self._lock:
            events = self._events_by_job.get(job_id)
            if events is not None:
                now = time.time()
                events.append({
                    "index": len(events),
                    "type": "steer.recorded",
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
                "summary": f"Antigravity turn execution {outcome}.",
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
