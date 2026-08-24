# Windows Port Requirements

## Requirements

- **R1**: On Windows 10/11, the plugin MUST install a per-user bridge runtime from PowerShell without requiring zsh or LaunchAgent.
- **R2**: The installer MUST resolve explicit absolute paths for Python, Codex, `tunnel-client`, and an existing workspace, and MUST reject an unusable Tunnel profile.
- **R3**: The Windows service wrapper MUST run `tunnel-client run` with the same fixed Guard policy and health endpoints used on macOS.
- **R4**: The Guard MUST support Windows file locking, stdio pipes, child-process creation/revocation, environment filtering, and Codex desktop project opening while preserving existing macOS behavior.
- **R5**: `install`, `doctor`, `status`, `restart`, `stop`, and `uninstall` MUST have Windows PowerShell entry points.
- **R6**: Installation MUST preserve external Tunnel profiles, Codex login, projects, and conversation history.

## Acceptance criteria

1. Windows-focused Guard tests pass under the host Python.
2. The plugin manifest validates.
3. A `--no-start` install followed by `doctor --no-start` succeeds with fixture Tunnel tooling.
4. The installed Guard completes an MCP `initialize` and `tools/list` exchange with the local Codex MCP server.
5. With a real profile and official `tunnel-client`, live `status` reports both local readiness and a recent control-plane poll.

## Non-goals

- Replacing the OpenAI Tunnel client or creating ChatGPT account/profile credentials.
- Changing the public Guard tool contract or the two policy presets.
- Refactoring the macOS LaunchAgent implementation.
