# Install or Upgrade on Windows

## Prerequisites

- Windows 10 or 11 with Windows PowerShell 5.1 or PowerShell 7.
- A working Codex CLI login, Python 3, the official `tunnel-client`, a device-local Tunnel profile, and an existing workspace container.

## Install

From the plugin root:

```powershell
& scripts\install-windows.ps1 `
  -Profile <device-profile> `
  -Workspace <absolute-workspace-directory> `
  -Preset personal-full-control

& scripts\doctor-windows.ps1
```

The installer stages the Guard below `%LOCALAPPDATA%\chatgpt-codex-bridge`,
adds a current-user Startup entry, starts Tunnel without a visible console, and
waits for local health plus a recent control-plane poll.

Use `-CodexBin`, `-TunnelClientBin`, or `-PythonBin` only when command discovery
does not select the intended installation. Use `-NoStart` only for isolated
packaging tests.

After ChatGPT has refreshed the app schema, call `codex-overview`. Its
`runtime.guardSha256` identifies the exact Guard file that served the request.
Compare it with the staged Windows runtime file:

```powershell
(Get-FileHash -LiteralPath `
  "$env:LOCALAPPDATA\chatgpt-codex-bridge\runtime\codex-mcp-guard.py" `
  -Algorithm SHA256).Hash
```

The two uppercase hashes should match. A mismatch isolates runtime drift from
Tunnel connectivity or Codex App Server behavior.

## Upgrade

Reinstall the plugin version, start a new Codex task so its Skill inventory is
refreshed, and rerun `install-windows.ps1` with the same profile, workspace, and
preset. The installer stops the previous Tunnel process and revokes verified
bridge-owned workers before replacing runtime files.

After restart and doctor, refresh the ChatGPT app so it loads the current tool
schema, start a new ChatGPT conversation, call `codex-overview`, and repeat the
runtime hash comparison above. The overview should also show the expected
workspace and an empty `degraded` list before live catalog or execution checks.

## Operations

```powershell
& scripts\chatgpt-codex-bridge-windows.ps1 status
& scripts\chatgpt-codex-bridge-windows.ps1 restart
& scripts\chatgpt-codex-bridge-windows.ps1 stop
& scripts\uninstall-windows.ps1
```

Removal preserves the external Tunnel profile, Codex login, project roots, and
conversation history.
