# Localhost 127.0.0.1 Approval Server & Web UI
# Enforces strict origin, loopback peer validation, anti-CSRF token verification,
# and safe state transitions without side-effects on GET.

import collections
import html
import http.server
import json
import os
import secrets
import socket
import socketserver
import threading
import urllib.parse
from pathlib import Path


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class ApprovalServer:
    def __init__(self, session_store, workspace_lock_mgr, adapter_registry=None, port=18230, host="127.0.0.1"):
        self.session_store = session_store
        self.workspace_lock_mgr = workspace_lock_mgr
        self.adapter_registry = adapter_registry or {}
        self.host = host
        self.requested_port = port
        self.actual_port = port
        self.server = None
        self.thread = None
        self._csrf_tokens = collections.deque(maxlen=100)
        self._tokens_lock = threading.Lock()
        self.runtime_version = "0.6.1+generic-v0.2"

    def _generate_csrf_token(self):
        token = secrets.token_hex(24)
        with self._tokens_lock:
            self._csrf_tokens.append(token)
        return token

    def _validate_csrf_token(self, token):
        if not token or not isinstance(token, str):
            return False
        with self._tokens_lock:
            return token in self._csrf_tokens


    def start(self):
        handler_factory = self._create_handler()
        try:
            self.server = ThreadedTCPServer((self.host, self.requested_port), handler_factory)
        except OSError:
            # Fallback to dynamic free port on 127.0.0.1
            self.server = ThreadedTCPServer((self.host, 0), handler_factory)
        self.actual_port = self.server.server_address[1]

        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self.get_url()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None

    def get_url(self):
        return f"http://{self.host}:{self.actual_port}/"

    def _create_handler(outer):
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                # Suppress noisy stdio logging
                pass

            def _send_security_headers(self, content_type="text/html; charset=utf-8"):
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; img-src 'self' data:")

            def _is_safe_peer(self):
                peer_ip = self.client_address[0]
                return peer_ip in ("127.0.0.1", "localhost", "::1", "::ffff:127.0.0.1")

            def _is_safe_host(self):
                host_hdr = self.headers.get("Host", "")
                if not host_hdr:
                    return False
                host_only = host_hdr.split(":")[0].lower()
                return host_only in ("127.0.0.1", "localhost")

            def _is_safe_origin(self):
                origin = self.headers.get("Origin")
                if not origin:
                    # Form submissions might omit origin, check Referer
                    referer = self.headers.get("Referer", "")
                    if not referer:
                        return True
                    parsed = urllib.parse.urlparse(referer)
                    return parsed.hostname in ("127.0.0.1", "localhost")
                parsed = urllib.parse.urlparse(origin)
                return parsed.hostname in ("127.0.0.1", "localhost")

            def do_GET(self):
                if not self._is_safe_peer() or not self._is_safe_host():
                    self.send_error(403, "Access denied: Host/Peer not loopback")
                    return

                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path

                if path == "/api/state":
                    # Read-only JSON state
                    pending = [s.to_dict() for s in outer.session_store.list_sessions(status="pending_approval")]
                    reauth = [s.to_dict() for s in outer.session_store.list_sessions(status="reauth_required")]
                    active = [
                        s.to_dict() for s in outer.session_store.list_sessions()
                        if s.status in ("authorized_idle", "running")
                    ]
                    payload = {
                        "pending": pending + reauth,
                        "active": active,
                        "runtime_version": outer.runtime_version,
                    }
                    data = json.dumps(payload).encode("utf-8")
                    self.send_response(200)
                    self._send_security_headers("application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return

                # Render HTML UI
                csrf_token = outer._generate_csrf_token()
                html_content = outer._render_ui(csrf_token)
                data = html_content.encode("utf-8")
                self.send_response(200)
                self._send_security_headers("text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                if not self._is_safe_peer() or not self._is_safe_host() or not self._is_safe_origin():
                    self.send_error(403, "Access denied: Security checks failed")
                    return

                content_len = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(content_len) if content_len > 0 else b""

                # Parse body (supports JSON or application/x-www-form-urlencoded)
                content_type = self.headers.get("Content-Type", "")
                params = {}
                if "application/json" in content_type:
                    try:
                        params = json.loads(raw_body.decode("utf-8"))
                    except Exception:
                        self.send_error(400, "Invalid JSON payload")
                        return
                else:
                    try:
                        parsed = urllib.parse.parse_qs(raw_body.decode("utf-8"))
                        params = {k: v[0] for k, v in parsed.items()}
                    except Exception:
                        pass

                # Anti-CSRF verification
                token = self.headers.get("X-CSRF-Token") or params.get("csrf_token")
                if not outer._validate_csrf_token(token):
                    self.send_error(403, "Invalid or missing anti-CSRF token")
                    return

                path = urllib.parse.urlparse(self.path).path
                # Routes:
                # POST /api/sessions/<session_id>/approve
                # POST /api/sessions/<session_id>/deny
                # POST /api/sessions/<session_id>/cancel_turn
                # POST /api/sessions/<session_id>/revoke
                parts = [p for p in path.split("/") if p]
                if len(parts) == 4 and parts[0] == "api" and parts[1] == "sessions":
                    session_id = parts[2]
                    action = parts[3]

                    try:
                        if action == "approve":
                            outer.session_store.allow_session(session_id)
                            res = {"status": "ok", "action": "approved", "session_id": session_id}
                        elif action == "deny":
                            outer.session_store.deny_session(session_id)
                            res = {"status": "ok", "action": "denied", "session_id": session_id}
                        elif action == "cancel_turn":
                            session = outer.session_store.get_session(session_id)
                            # Release write lock
                            if session.workspace:
                                outer.workspace_lock_mgr.release_turn_write_lock(session.workspace, session.current_job_id)
                            # Native interrupt if adapter available
                            adapter = outer.adapter_registry.get(session.executor)
                            if adapter and session.current_job_id:
                                try:
                                    adapter.cancel(session.current_job_id)
                                except Exception:
                                    pass
                            outer.session_store.cancel_turn(session_id)
                            res = {"status": "ok", "action": "turn_cancelled", "session_id": session_id}
                        elif action == "revoke":
                            session = outer.session_store.get_session(session_id)
                            # Release all locks
                            if session.workspace:
                                outer.workspace_lock_mgr.release_all_for_session(session_id)
                            # Terminate adapter native session
                            adapter = outer.adapter_registry.get(session.executor)
                            if adapter:
                                try:
                                    adapter.dispose(session_id)
                                except Exception:
                                    pass
                            outer.session_store.revoke_session(session_id)
                            res = {"status": "ok", "action": "revoked", "session_id": session_id}
                        else:
                            self.send_error(404, "Unknown session action")
                            return

                        data = json.dumps(res).encode("utf-8")
                        self.send_response(200)
                        self._send_security_headers("application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)
                        return

                    except Exception as err:
                        err_data = json.dumps({"status": "error", "message": str(err)}).encode("utf-8")
                        self.send_response(400)
                        self._send_security_headers("application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(err_data)))
                        self.end_headers()
                        self.wfile.write(err_data)
                        return

                self.send_error(404, "Not found")

        return Handler

    def _render_ui(self, csrf_token):
        pending = self.session_store.list_sessions(status="pending_approval")
        reauth = self.session_store.list_sessions(status="reauth_required")
        all_pending = pending + reauth
        active = [
            s for s in self.session_store.list_sessions()
            if s.status in ("authorized_idle", "running")
        ]

        def render_badge(profile):
            if profile.lower() == "trusted":
                return '<span style="background:#ef4444;color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold;">TRUSTED (High Privilege)</span>'
            elif profile.lower() == "build":
                return '<span style="background:#3b82f6;color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold;">BUILD</span>'
            else:
                return '<span style="background:#10b981;color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold;">SAFE (Read-Only)</span>'

        pending_rows = ""
        for s in all_pending:
            trusted_warning = ""
            if s.permission_profile == "trusted":
                trusted_warning = '<div style="color:#ef4444;margin-top:6px;font-weight:bold;">WARNING: TRUSTED permission gives unlimited system access.</div>'
            pending_rows += f"""
            <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;margin-bottom:12px;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                  <span style="font-size:1.1em;font-weight:bold;color:#f8fafc;">Executor: {html.escape(s.executor.upper())}</span>
                  &nbsp; {render_badge(s.permission_profile)}
                </div>
                <div>
                  <button onclick="postAction('{s.session_id}','approve')" style="background:#10b981;color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:bold;margin-right:8px;">Allow Session</button>
                  <button onclick="postAction('{s.session_id}','deny')" style="background:#64748b;color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;">Deny</button>
                </div>
              </div>
              <div style="margin-top:8px;color:#94a3b8;font-size:0.95em;">
                <div><strong>Workspace:</strong> <code>{html.escape(s.workspace)}</code></div>
                <div><strong>Objective:</strong> {html.escape(s.display_objective or 'None')}</div>
                <div><strong>Session ID:</strong> <code>{s.session_id}</code></div>
                {trusted_warning}
              </div>
            </div>
            """

        if not pending_rows:
            pending_rows = '<div style="color:#64748b;padding:16px;background:#1e293b;border-radius:8px;">No pending session authorization requests.</div>'

        active_rows = ""
        for s in active:
            status_color = "#10b981" if s.status == "authorized_idle" else "#eab308"
            turn_text = f"Running Turn: {s.current_job_id}" if s.current_job_id else "Idle (Waiting for turn)"
            stop_turn_btn = ""
            if s.status == "running":
                stop_turn_btn = f'<button onclick="postAction(\'{s.session_id}\',\'cancel_turn\')" style="background:#f59e0b;color:#fff;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin-right:8px;">Stop Current Turn</button>'
            active_rows += f"""
            <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;margin-bottom:12px;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                  <span style="font-size:1.1em;font-weight:bold;color:#f8fafc;">{html.escape(s.executor.upper())}</span>
                  &nbsp; {render_badge(s.permission_profile)}
                  &nbsp; <span style="color:{status_color};font-weight:bold;">[{s.status.upper()}]</span>
                </div>
                <div>
                  {stop_turn_btn}
                  <button onclick="postAction('{s.session_id}','revoke')" style="background:#ef4444;color:#fff;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;">Revoke Session</button>
                </div>
              </div>
              <div style="margin-top:8px;color:#94a3b8;font-size:0.95em;">
                <div><strong>Workspace:</strong> <code>{html.escape(s.workspace)}</code></div>
                <div><strong>Status Detail:</strong> {html.escape(turn_text)}</div>
                <div><strong>Session ID:</strong> <code>{s.session_id}</code></div>
              </div>
            </div>
            """

        if not active_rows:
            active_rows = '<div style="color:#64748b;padding:16px;background:#1e293b;border-radius:8px;">No active sessions.</div>'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Executor Controller — Local Approval Gate</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ background: #0f172a; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 24px; }}
    .container {{ max-width: 900px; margin: 0 auto; }}
    h1 {{ font-size: 1.5rem; margin-bottom: 4px; }}
    .subtitle {{ color: #94a3b8; font-size: 0.9rem; margin-bottom: 24px; }}
    h2 {{ font-size: 1.2rem; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-top: 32px; color: #e2e8f0; }}
    code {{ background: #090d16; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Executor Controller — Local Approval Gate</h1>
    <div class="subtitle">Runtime Version: {self.runtime_version} &bull; Host: 127.0.0.1:{self.actual_port}</div>

    <h2>Pending Session Requests (Local Human Approval Gate)</h2>
    <div id="pending-section">{pending_rows}</div>

    <h2>Active Authorized Sessions</h2>
    <div id="active-section">{active_rows}</div>
  </div>

  <script>
    const CSRF_TOKEN = "{csrf_token}";

    async function postAction(sessionId, action) {{
      try {{
        const res = await fetch('/api/sessions/' + sessionId + '/' + action, {{
          method: 'POST',
          headers: {{
            'Content-Type': 'application/json',
            'X-CSRF-Token': CSRF_TOKEN
          }},
          body: JSON.stringify({{ csrf_token: CSRF_TOKEN }})
        }});
        const json = await res.json();
        if (res.ok) {{
          location.reload();
        }} else {{
          alert('Action failed: ' + (json.message || 'Error'));
        }}
      }} catch (err) {{
        alert('Network error: ' + err.message);
      }}
    }}
  </script>
</body>
</html>"""
