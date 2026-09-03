# Codex Adapter for Executor Controller
# Reuses existing Codex App Server, thread lifecycle, and structured report mechanisms.

import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from .base import ExecutorAdapter


class CodexExecutorAdapter(ExecutorAdapter):
    def __init__(self, codex_bin="", job_state_dir=""):
        self._id = "codex"
        self.codex_bin = codex_bin or self._find_codex_bin()
        self.job_state_dir = Path(job_state_dir) if job_state_dir else None
        self._threads = {}

    @property
    def id(self) -> str:
        return self._id

    def _find_codex_bin(self):
        candidate = shutil.which("codex") or shutil.which("codex.cmd") or shutil.which("codex.exe")
        if candidate:
            return candidate
        # Common fallback locations on Windows
        npm_bin = Path(os.environ.get("APPDATA", "")) / "npm" / "codex.cmd"
        if npm_bin.is_file():
            return str(npm_bin)
        return "codex"

    def detect(self) -> dict:
        installed = False
        version = "unknown"
        bin_path = self.codex_bin
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
            "capabilities": {
                "steer": True,
                "cancel": True,
                "resume": True,
                "models": True,
                "thinking": True,
                "app_server": True,
            },
        }

    def create_native_session(self, session) -> str:
        # Generate or bind native Codex thread ID
        native_id = session.native_session_id
        if not native_id:
            native_id = f"01{uuid.uuid4().hex[:30]}"
            self._threads[session.session_id] = native_id
        return native_id

    def start_turn(self, session, job_id: str, turn_spec: dict) -> dict:
        # In real bridge integration, turn_start dispatches to run_job / AppServer
        # Record turn mapping
        native_thread = self.create_native_session(session)
        return {
            "status": "started",
            "job_id": job_id,
            "thread_id": native_thread,
        }

    def steer(self, job_id: str, message: str) -> bool:
        if self.job_state_dir:
            job_dir = self.job_state_dir / job_id
            if job_dir.is_dir():
                controls_path = job_dir / "controls.json"
                controls = []
                if controls_path.is_file():
                    try:
                        controls = json.loads(controls_path.read_text(encoding="utf-8"))
                    except Exception:
                        controls = []
                controls.append({
                    "action": "steer",
                    "content": message,
                    "createdAt": time.time(),
                    "delivered": False,
                })
                controls_path.write_text(json.dumps(controls, indent=2), encoding="utf-8")
                return True
        return False

    def cancel(self, job_id: str) -> bool:
        if self.job_state_dir:
            job_dir = self.job_state_dir / job_id
            if job_dir.is_dir():
                controls_path = job_dir / "controls.json"
                controls = []
                if controls_path.is_file():
                    try:
                        controls = json.loads(controls_path.read_text(encoding="utf-8"))
                    except Exception:
                        controls = []
                controls.append({
                    "action": "cancel",
                    "createdAt": time.time(),
                    "delivered": False,
                })
                controls_path.write_text(json.dumps(controls, indent=2), encoding="utf-8")
                return True
        return False

    def poll_events(self, job_id: str, after_index: int = 0) -> list:
        if self.job_state_dir:
            transcript_path = self.job_state_dir / job_id / "transcript.jsonl"
            if transcript_path.is_file():
                events = []
                try:
                    for line in transcript_path.read_text(encoding="utf-8").splitlines():
                        if line.strip():
                            events.append(json.loads(line))
                    return events[after_index:]
                except Exception:
                    pass
        return []

    def get_result(self, job_id: str) -> dict:
        if self.job_state_dir:
            status_path = self.job_state_dir / job_id / "status.json"
            if status_path.is_file():
                try:
                    data = json.loads(status_path.read_text(encoding="utf-8"))
                    report = data.get("report")
                    if report:
                        return report
                    return {
                        "outcome": data.get("status", "unknown"),
                        "summary": data.get("content", ""),
                        "changedFiles": [],
                        "commands": [],
                        "checks": [],
                        "blockers": [],
                        "questions": [],
                        "nextStep": data.get("nextAction", "review"),
                    }
                except Exception:
                    pass
        return {"outcome": "not_found", "summary": "Job state unavailable"}

    def dispose(self, session_id: str) -> None:
        self._threads.pop(session_id, None)
