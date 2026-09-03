# Executor Adapter Base Interface
# Defines standard lifecycle hooks for Codex, Pi, Antigravity, and Mock workers.

import abc


class ExecutorAdapter(abc.ABC):
    @property
    @abc.abstractmethod
    def id(self) -> str:
        pass

    @abc.abstractmethod
    def detect(self) -> dict:
        """
        Detects installation, availability, executable path, version, and supported capabilities.
        Must be read-only and never trigger model calls.
        """
        pass

    @abc.abstractmethod
    def create_native_session(self, session) -> str:
        """
        Creates or registers a native session identifier (e.g. thread ID, RPC session dir, conversation ID).
        """
        pass

    @abc.abstractmethod
    def start_turn(self, session, job_id: str, turn_spec: dict) -> dict:
        """
        Starts a turn/job execution in the authorized session.
        """
        pass

    @abc.abstractmethod
    def steer(self, job_id: str, message: str) -> bool:
        """
        Steers an actively running turn.
        """
        pass

    @abc.abstractmethod
    def cancel(self, job_id: str) -> bool:
        """
        Cancels/interrupts an actively running turn.
        """
        pass

    @abc.abstractmethod
    def poll_events(self, job_id: str, after_index: int = 0) -> list:
        """
        Returns normalized execution events.
        """
        pass

    @abc.abstractmethod
    def get_result(self, job_id: str) -> dict:
        """
        Returns structured result report.
        """
        pass

    @abc.abstractmethod
    def dispose(self, session_id: str) -> None:
        """
        Cleans up native session and any allocated worker processes.
        """
        pass
