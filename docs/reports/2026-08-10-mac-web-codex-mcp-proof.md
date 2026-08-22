# Mac Web ChatGPT -> Local Codex MCP Proof

Status: PASS (T-400 proof 1/2)
Date: 2026-08-10
Timezone: local timezone

## Objective

Prove that one ordinary ChatGPT web conversation can attach `Codex MCP Guard`, create one real local Codex thread through `codex`, retain its returned identity, and continue the same thread through `codex-reply` on the configured host.

This proof intentionally requested no file reads, file writes, shell commands, dependency changes, or repository mutation from the delegated Codex task.

## Preconditions

- The macOS user LaunchAgent reported `status=ready`.
- Local health and readiness endpoints returned HTTP 200.
- The Secure Tunnel control plane reported connected.
- `tunnel-client doctor` passed for the configured profile.
- The selected local Codex executable reported a working CLI version and exposed `mcp-server`.
- A fresh ChatGPT web conversation visibly contained the `Codex MCP Guard` pill before the first prompt was sent.

## Execution and evidence

| Gate | Expected | Observed | Result |
| --- | --- | --- | --- |
| Initial call | ChatGPT invokes Guard `codex` | Exact marker `T400_MAC_WEB_START_OK` returned | PASS |
| Thread creation | Initial result contains a usable thread identity | Assistant emitted `Codex thread: <threadId>`; value withheld here | PASS |
| Continuation | Same conversation invokes `codex-reply` | Exact marker `T400_MAC_WEB_REPLY_OK` returned | PASS |
| Local dispatch | Tunnel receives new work from ChatGPT | New redacted dispatcher-forward entries appeared for initial and reply turns | PASS |
| Service continuity | Tunnel remains live throughout | Health, readiness, and control-plane state remained ready | PASS |
| Repository safety | Test causes no repository mutation | Git worktree remained clean before documentation work began | PASS |

## Diagnosis and repair

The local Tunnel and Codex MCP server were already healthy. The failing ChatGPT conversation did not have the Developer MCP app attached to its composer. The repair was to create a fresh ChatGPT web conversation, select `Codex MCP Guard`, and verify the visible app pill before sending the prompt. No Tunnel restart or architecture change was required.

## Evidence boundary

- This report proves the Mac web entry surface and the local start/continue loop once on 2026-08-10.
- It does not disclose Tunnel IDs, request IDs, plugin IDs, credentials, or the Codex thread value.
- It does not prove every ChatGPT mobile client, model, or existing conversation can execute Developer MCP merely because the app is displayed.
- It does not establish a reliability benchmark or asynchronous reverse wake-up.
- T-400 remains open until one more fresh end-to-end proof passes.
