# T-112 consumer ChatGPT guarded Codex connector

Status: `PASS`
Date: 2026-08-02
Task: `T-112`

## Outcome

The full discovery and connection path now works:

```text
consumer ChatGPT
  -> connected Codex MCP Guard app
  -> OpenAI Secure Tunnel
  -> tunnel-client
  -> local Codex MCP guard
  -> official codex mcp-server
```

ChatGPT created, connected, and refreshed the app. It persists exactly two tools: `codex` and `codex-reply`. Both are truthfully shown as public-write, open-world, and mutable. Their public schemas expose only the narrow prompt/mode and prompt/threadId inputs.

## Defect found and fixed

ChatGPT multiplexes repeated MCP `initialize` requests onto the same long-lived stdio child. The official Codex MCP server accepts initialization only once, so the second request returned `initialize called more than once` and the app save failed.

The guard now forwards the first initialization, caches a successful result, replays it using each caller's request ID, and forwards `notifications/initialized` only once. A regression fake child rejects any second downstream initialization, proving the replay occurs in the guard.

## Verification

- Guard contract suite: 13 tests passed.
- ChatGPT UI: app created, connected, refreshed, and shows a connection timestamp.
- Tool discovery: exactly `codex` and `codex-reply`; no additional tools.
- Tool metadata: both public-write, open-world, mutable, and public visibility.
- Tunnel runtime: process running; liveness `live`; readiness `ready`; successful control-plane poll observed.
- Credential handling: restricted Tunnel Read + Use runtime key stored in macOS Keychain; no raw key or connector identifier stored in Git or project memory.

## Single-user operating mode

The accepted single-user preset favors convenience-first execution on the configured local host. The active profile enables project `workspace-write`; the guard still fixes the exact project path and does not expose unrelated raw permission/configuration controls.

## Not claimed

T-112 intentionally made no `codex`, `codex-reply`, approval, or filesystem-write tool call. T-202 baseline capture followed by T-303 is next: one real read-only Codex call through the connected ChatGPT app, followed by integrity verification.
