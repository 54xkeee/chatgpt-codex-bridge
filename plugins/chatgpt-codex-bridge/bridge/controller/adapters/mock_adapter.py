# Mock Executor Adapter for Tests and E2E Simulation
# Simulates full turn lifecycle, events, steer, and cancel without calling external processes.

import threading
import time
from .base import ExecutorAdapter


class MockExecutorAdapter(ExecutorAdapter):
    def __init__(self):
        self._id = "mock"
        self._turns = {}
        self._lock = threading.Lock()

    @property
    def id(self) -> str:
        return self._id

    def detect(self) -> dict:
        return {
            "id": self._id,
            "installed": True,
            "available": True,
            "binary_path": "mock://in-process",
            "version": "1.0.0-mock",
            "capabilities": {
                "steer": True,
                "cancel": True,
                "resume": True,
                "models": True,
                "thinking": True,
            },
        }

    def create_native_session(self, session) -> str:
        return f"mock-native-session-{session.session_id[:8]}"

    def start_turn(self, session, job_id: str, turn_spec: dict) -> dict:
        now = time.time()
        with self._lock:
            turn_record = {
                "session_id": session.session_id,
                "job_id": job_id,
                "status": "running",
                "objective": turn_spec.get("objective", ""),
                "started_at": now,
                "steer_messages": [],
                "events": [
                    {"index": 0, "type": "executor.started", "time": now, "executor": "mock"},
                    {"index": 1, "type": "turn.started", "time": now, "objective": turn_spec.get("objective", "")},
                    {"index": 2, "type": "assistant.delta", "time": now, "content": "Mock worker working on objective..."},
                    {"index": 3, "type": "tool.started", "time": now, "tool": "test_inspect"},
                    {"index": 4, "type": "tool.completed", "time": now, "tool": "test_inspect", "output": "workspace ok"},
                ],
            }
            self._turns[job_id] = turn_record
        return {"status": "started", "job_id": job_id}

    def steer(self, job_id: str, message: str) -> bool:
        with self._lock:
            turn = self._turns.get(job_id)
            if not turn or turn["status"] != "running":
                return False
            now = time.time()
            turn["steer_messages"].append(message)
            turn["events"].append({
                "index": len(turn["events"]),
                "type": "steer.accepted",
                "time": now,
                "message": message,
            })
            turn["events"].append({
                "index": len(turn["events"]),
                "type": "assistant.delta",
                "time": now,
                "content": f"Acknowledged steer: {message}",
            })
            return True

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            turn = self._turns.get(job_id)
            if not turn or turn["status"] != "running":
                return False
            now = time.time()
            turn["status"] = "cancelled"
            turn["events"].append({
                "index": len(turn["events"]),
                "type": "turn.cancelled",
                "time": now,
            })
            return True

    def mark_completed(self, job_id: str, summary="Mock completed successfully"):
        with self._lock:
            turn = self._turns.get(job_id)
            if turn and turn["status"] == "running":
                now = time.time()
                turn["status"] = "completed"
                turn["summary"] = summary
                turn["events"].append({
                    "index": len(turn["events"]),
                    "type": "turn.completed",
                    "time": now,
                })

    def poll_events(self, job_id: str, after_index: int = 0) -> list:
        with self._lock:
            turn = self._turns.get(job_id)
            if not turn:
                return []
            return [e for e in turn["events"] if e["index"] >= after_index]

    def get_result(self, job_id: str) -> dict:
        with self._lock:
            turn = self._turns.get(job_id)
            if not turn:
                return {"outcome": "not_found", "summary": "Job not found"}
            status = turn["status"]
            outcome = "completed" if status == "completed" else status
            return {
                "outcome": outcome,
                "summary": turn.get("summary", f"Mock execution finished with status '{status}'."),
                "changedFiles": [],
                "commands": [],
                "checks": [],
                "blockers": [],
                "questions": [],
                "nextStep": "review",
            }

    def dispose(self, session_id: str) -> None:
        with self._lock:
            to_del = [jid for jid, t in self._turns.items() if t.get("session_id") == session_id]
            for jid in to_del:
                del self._turns[jid]
