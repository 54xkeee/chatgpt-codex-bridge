# ADR 0015: Add a Windows per-user bridge adapter

## Context

The portable plugin previously depended on zsh, LaunchAgent, `fcntl`, POSIX
process groups, and selector-compatible pipes. Those assumptions prevent the
same Guard and Tunnel topology from running on Windows.

## Decision

Keep one MCP Guard contract and add bounded OS adapters for locking, pipe
multiplexing, worker-tree revocation, environment filtering, and Codex desktop
opening. Package PowerShell lifecycle commands and use the current user's
Startup folder for logon restart. Keep the official OpenAI `tunnel-client` as
the transport and profile owner.

## Consequences

- macOS keeps its existing LaunchAgent behavior.
- Windows uses generated files below `%LOCALAPPDATA%\chatgpt-codex-bridge`.
- Service shutdown verifies the recorded Guard/job command before invoking
  `taskkill /T /F` on the owned worker tree.
- Tunnel identity and runtime keys stay outside the plugin and remain a
  per-device setup prerequisite.
