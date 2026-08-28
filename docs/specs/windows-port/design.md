# Windows Port Design

## Design

- Keep one Guard implementation and isolate OS differences behind small helpers.
- Use `msvcrt.locking` for the admission lock on Windows and `fcntl.flock` elsewhere.
- Use reader threads plus a queue for Windows pipe multiplexing; retain selectors on POSIX.
- Create workers with a new Windows process group and revoke the verified process tree with `taskkill /T /F`.
- Open projects with `codex app <workspace>` on Windows and retain `open -b com.openai.codex` on macOS.
- Store generated Windows state below `%LOCALAPPDATA%\chatgpt-codex-bridge` and use the current user's Startup folder for restart-at-logon.
- Generate JSON configuration and a PowerShell runtime wrapper; keep secrets in the external Tunnel profile.
- Generate `run-tunnel.cmd` as one bridge-owned loop: run `tunnel-client`, wait five seconds after an exit, and retry. Keep the recorded parent PID unchanged so the existing process-tree stop path still controls the loop.

## Failure behavior

- Path, profile, executable, ownership, and health checks fail closed.
- A service stop/restart first stops Tunnel and then revokes only workers whose recorded command line matches the Guard/job pair.
- Missing `tunnel-client` or profile prevents live installation but still permits fixture-based packaging verification.
- A transient Tunnel exit is recovered by the generated command loop; repeated startup failures remain visible in the existing stdout/stderr logs and are separated by the bounded delay.

## Rollback

Run `scripts/uninstall-windows.ps1`; it removes generated runtime/task/state owned by the bridge and leaves external identities and workspaces intact.
