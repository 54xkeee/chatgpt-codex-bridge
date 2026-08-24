# Windows live proof

This document records the sanitized acceptance evidence for the Windows port.
It intentionally omits the device Tunnel ID, control-plane key, signed
capabilities, raw Codex thread/job identifiers, account details, and per-user
paths.

## Environment

| Item | Verified value |
|---|---|
| Date | 2026-08-24 |
| Platform | Windows, current-user installation |
| Controller shell | Windows PowerShell 5.1 |
| Codex CLI | 0.147.0 |
| Bridge preset | `personal-full-control` |
| Live-tested Bridge version | `0.6.1+codex.20260823235922` |
| Final packaged metadata | `0.6.1+codex.20260824010445` |
| Runtime state | `status=ready`, `runtime_guard_match=true` |

Codex CLI 0.147 does not expose the newer `project/*` App Server API. The
catalog therefore groups projects by bounded thread `cwd` and uses
`thread/list`, `thread/read`, and `thread/turns/list(itemsView=summary)`.

## Contract and Windows tests

### Guard contract

```text
Ran 55 tests in 22.244s
OK
```

Coverage includes catalog paging and filters, signed capability audiences,
bounded thread history, reasoning filtering, historical thread continuation,
progress/report fields, malformed event handling, admission limits, and
runtime policy binding.

### Windows port

The full PowerShell 5.1 test completed with exit code `0` and reported:

```text
PASS: Windows Guard MCP initialize/tools-list
PASS: Windows atomic status replacement retry
PASS: Windows verified worker-tree revocation
PASS: Windows isolated install/doctor/bootstrap
```

The suite covers PowerShell 5.1 path semantics, Unicode workspace paths,
runtime staging, fake Tunnel/Codex isolation, Guard EOF, descendant process
cleanup, and status-file replacement under Windows contention.

## Installed runtime identity

The source Guard, packaged plugin Guard, and installed runtime Guard produced
the same SHA-256:

```text
BEA26E25B85FAD17F338159BF9757523EF1119C065918DCAF7014AA729A6D5B3
```

The live-tested Codex plugin was installed and enabled at:

```text
0.6.1+codex.20260823235922
```

The final public package only changes release metadata and documentation after
that live run; its Guard bytes retain the verified hash above.

## Direct MCP acceptance

An MCP client launched the installed `run-guard.ps1`, completed
`initialize/tools-list`, and called the real local catalog. The bounded
snapshot contained:

```text
catalog tools: 6
projects:       3
repositories:   2
threads:       11
jobs:          18
```

A full acceptance call then verified:

```text
currentRepositoryFound: true
workspaceThreadFound:   true
boundedHistoryTurns:    3
historyHasNextCursor:   true
jobStatus:              completed
jobPhase:               completed
reportOutcome:          completed
reportHasSummary:       true
reportCommandCount:     1
reportHasNextStep:      true
```

## ChatGPT Pro round trip

The ChatGPT Developer connection was recreated against the current device
Tunnel. Its operation list contained all 14 public/private tools, including
`codex-run` and all six catalog tools.

ChatGPT then requested a bounded overview, repository lookup, and a read-only
Codex job. The local durable state progressed through:

```text
running / executing
running / finalizing
completed / completed
```

The final local record reported:

```text
activity:          Codex completed; waiting for ChatGPT review
failureStage:      empty
nextAction:        review
reportOutcome:     completed
reportHasSummary:  true
reportCommands:    2
reportHasNextStep: true
```

The ChatGPT-visible terminal report independently showed a later bounded
snapshot with 2 repositories, 14 threads/tasks, 21 durable jobs, and 0 active
jobs. Both requested commands returned exit code `0`; the report recorded no
Bridge-created file changes and concluded that the v2 round trip passed.

Two UI screenshots were reviewed during acceptance. They are intentionally
kept outside the repository because the raw cards contain signed Codex
thread/job capabilities. This document records the reproducible non-secret
facts instead of publishing reusable identifiers.

This proves the live path:

```text
ChatGPT Pro
→ OpenAI Secure MCP Tunnel
→ Windows Codex MCP Guard
→ local Codex App Server
→ repository commands
→ durable structured result for ChatGPT review
```

## Reproduce

Run the repository checks:

```powershell
wsl.exe -e bash -lc `
  'cd /mnt/d/path/to/chatgpt-codex-bridge && python3 -m unittest tests.bridge.test-codex-mcp-guard'

C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe `
  -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File .\tests\windows\test_windows_port.ps1

git diff --check
```

After installation, create a fresh ChatGPT Developer connection for the device
Tunnel, confirm that all 14 operations are present, attach it to a new chat,
and ask ChatGPT to call `codex-overview`, `codex-repository-list`, `codex-run`,
and `codex-wait`.
