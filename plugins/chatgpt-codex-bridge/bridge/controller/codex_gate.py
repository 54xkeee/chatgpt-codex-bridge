# P0 Codex Legacy Session Gate
# Intercepts codex, codex-run, codex-start, codex-reply, codex-reply-async.
# Enforces that no execution can occur without an authorized session.

import os


LEGACY_START_TOOLS = frozenset({
    "codex",
    "codex-run",
    "codex-start",
    "codex-reply",
    "codex-reply-async",
})


class CodexSessionGate:
    def __init__(self, session_store, capability_codec, approval_server, default_workspace=""):
        self.session_store = session_store
        self.capability_codec = capability_codec
        self.approval_server = approval_server
        self.default_workspace = default_workspace

    def check_or_gate(self, tool_name, arguments, workspace=None):
        """
        If tool_name is in LEGACY_START_TOOLS:
        Verifies whether an AUTHORIZED session for Codex in this workspace exists.
        If yes: returns (True, authorized_session)
        If no: creates a pending session request, blocks launch, and returns (False, gate_response)
        """
        if tool_name not in LEGACY_START_TOOLS:
            return True, None

        target_ws = workspace or self.default_workspace or os.getcwd()
        if isinstance(arguments, dict) and "workspace" in arguments and arguments["workspace"]:
            target_ws = arguments["workspace"]

        canonical_ws = os.path.realpath(str(target_ws)) if os.path.exists(str(target_ws)) else str(target_ws)

        # Look for existing authorized session
        session = self.session_store.find_authorized_session(
            executor="codex",
            workspace=canonical_ws,
        )

        if session is not None:
            return True, session

        # No authorized session! Block launch and create pending request
        objective = "Legacy Codex tool invocation: " + tool_name
        if isinstance(arguments, dict):
            prompt = arguments.get("prompt") or arguments.get("message") or ""
            if prompt:
                objective = prompt[:200]

        pending_session = self.session_store.prepare_session(
            executor="codex",
            workspace=canonical_ws,
            permission_profile="build",
            objective=objective,
        )

        signed_req_id = self.capability_codec.encode("session-request", pending_session.session_id)
        approval_url = self.approval_server.get_url() if self.approval_server else "http://127.0.0.1:18230/"

        gate_response = {
            "status": "pending_approval",
            "error": "approval_required",
            "message": (
                f"Codex tool '{tool_name}' requires an authorized Executor Session. "
                f"A session request has been created. Please authorize it at the Approval UI: {approval_url}"
            ),
            "session_request_id": signed_req_id,
            "approval_url": approval_url,
            "workspace": canonical_ws,
            "executor": "codex",
        }
        return False, gate_response
