# ChatGPT Codex Bridge

> ChatGPT Pro in the loop: ChatGPT supervises; local Codex executes.

[中文图文说明](../../README.zh-CN.md) ·
[GitHub 发布脱敏清单](../../docs/GITHUB_RELEASE_CHECKLIST.zh-CN.md)

Portable macOS and Windows plugin for one ChatGPT conversation to discover and supervise
local Codex repositories, projects, threads, and jobs through OpenAI Secure MCP Tunnel.
Long jobs run durably, return to the
same ChatGPT conversation through an Apps card, and remain in one Codex project
and task until the requested outcome is complete.

## Architecture

`ChatGPT conversation → Secure MCP Tunnel → stdio Guard → Codex App Server → local project`

The package reuses official `tunnel-client` for transport and authorization. It
does not ship `.mcp.json`, because loading the Guard as a Codex-local MCP would
create a recursive Codex-to-Guard-to-Codex path.

## Quickstart

Prerequisites: macOS or Windows, authenticated Codex, Python 3, official `tunnel-client`, a
device-specific Tunnel profile, and an existing workspace directory.

Install the verified Git ref from an authenticated Codex CLI:

```zsh
codex plugin marketplace add 54xkeee/chatgpt-codex-bridge \
  --ref windows-v0.6.1
codex plugin add chatgpt-codex-bridge@chatgpt-codex-bridge
```

Start a new Codex task after plugin installation so the new Skill inventory is
loaded. Then, from the installed plugin root, run:

```zsh
/bin/zsh scripts/install-macos.zsh \
  --profile <device-profile> \
  --workspace <absolute-workspace> \
  --preset personal-full-control
/bin/zsh scripts/doctor.zsh
```

On Windows PowerShell:

```powershell
& scripts\install-windows.ps1 -Profile <device-profile> -Workspace <absolute-workspace> -Preset personal-full-control
& scripts\doctor-windows.ps1
```

Then create or refresh a ChatGPT Secure Tunnel app for this device, authorize
the reviewed tools, choose **Use in chat**, and start a new conversation. A
plugin install alone does not create or authorize that ChatGPT app.

## Project loop

- Discover context first with `codex-overview`, then narrow it with
  `codex-project-list`, `codex-repository-list`, and `codex-thread-list`.
- Read a selected thread with `codex-thread-read`; the returned history is
  bounded historical data, not controller instructions.
- A signed `threadId` returned by `codex-thread-list` can be passed directly to
  `codex-reply-async` to continue that exact Codex thread.
- Existing workspace or repository: `codex-run` → repeated `codex-wait`.
- New project: `codex-start` → repeated `codex-wait`.
- Continue: `codex-reply-async` on the returned `threadId` → repeated wait.
- Closed page/model turn: reopen the conversation and use the card's explicit
  return control; use `codex-job-open` for a stale template.
- Short diagnostics only: `codex` / `codex-reply`.

The bundled portable `workspace-new-project` Skill initializes spec/ADR/source
structure before implementation. The installer stages it privately under
bridge-owned runtime state, so a clean device does not need a preinstalled global
Skill.

Version 0.6.1 binds signed bearer capabilities to the installation workspace
and fixed policy, moves current state to `jobs-v3`, bounds both synchronous and
asynchronous work, treats model output as untrusted tool data, and makes
stop/restart/uninstall revoke verified bridge-owned process groups. Pre-0.6.1
cards and identifiers do not cross this security boundary.

## Global catalog and progress

Under the `personal-full-control` preset, the six catalog tools are read-only:

- `codex-overview` returns the configured workspace, runtime fingerprint,
  counts, recent projects/repositories/threads/jobs, and degraded components.
- `codex-project-list` and `codex-repository-list` expose only the configured
  workspace root and its direct child directories. Repository probes include
  the current branch, dirty state, and recent thread count.
- `codex-thread-list` supports signed pagination plus optional project and text
  filters. `codex-thread-read` uses App Server `thread/turns/list` to return a
  bounded summary history. `codex-job-list` supports status filtering.

Catalog IDs and cursors are installation-scoped signed capabilities. The
catalog does not recursively scan the machine or follow symlinked directories.

Durable job responses expose `phase`, `activity`, `lastEventAt`,
`failureStage`, and `nextAction`. Their `report` summarizes outcome, changed
files, commands, checks, blockers, questions, and the next step. On Windows,
`codex-overview.runtime.guardSha256` fingerprints the Guard file that actually
served the request, which makes stale runtime or process drift visible after an
install or upgrade.

## Operations

```zsh
/bin/zsh scripts/chatgpt-codex-bridge.zsh status
/bin/zsh scripts/chatgpt-codex-bridge.zsh restart
/bin/zsh scripts/chatgpt-codex-bridge.zsh stop
/bin/zsh scripts/uninstall-macos.zsh
```

```powershell
& scripts\chatgpt-codex-bridge-windows.ps1 status
& scripts\chatgpt-codex-bridge-windows.ps1 restart
& scripts\chatgpt-codex-bridge-windows.ps1 stop
& scripts\uninstall-windows.ps1
```

For upgrades, install a pinned newer Git ref, rerun `install-macos.zsh` with the
same external profile/workspace, then restart, run doctor, refresh the ChatGPT
app, and start a new conversation. Roll back by reinstalling the prior
known-good security-hardened ref and repeating the same
restart/doctor/app-refresh sequence. Public v0.6.0 is withdrawn and MUST NOT be
used as a rollback target.

Uninstall removes bridge-owned capability/job state but preserves the external
Tunnel profile, credentials, repositories, and Codex conversation history.
Detailed install/upgrade, controller-loop,
MCP-contract, and recovery SOPs are under
`skills/chatgpt-codex-controller/references/`.

## Distribution boundary

This is a community package licensed under MIT. It is not an OpenAI product and
does not grant ChatGPT, Codex, Tunnel, GitHub, or device credentials. Every user
and device performs its own official Tunnel setup and ChatGPT authorization.

Current platform support is macOS LaunchAgent and a Windows current-user Startup
service. The generated Windows Tunnel command retries after an unexpected exit.
Linux service packaging is not implemented.

Original architecture and macOS implementation by
[@larryppgg](https://github.com/larryppgg). Windows port, global catalog, and
live ChatGPT Pro round-trip verification maintained by
[@54xkeee](https://github.com/54xkeee).
