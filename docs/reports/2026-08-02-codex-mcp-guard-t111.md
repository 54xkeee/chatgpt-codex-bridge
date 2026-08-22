# T-111 Codex MCP Guard Verification

Date: 2026-08-02
Classification: `PASS_LOCAL_CONTRACT`
Scope: T-111 only

## Outcome

The local dependency-free stdio guard is implemented and verified against FR-011. It exposes only `codex` and `codex-reply` with truthful action annotations, replaces the raw caller-controlled schemas, injects the exact workspace plus `approval-policy=on-request`, defaults to read-only, requires a local flag for write mode, allowlists thread IDs, filters the child environment, and fails closed on protocol or schema drift.

This result does not close T-112, T-200, or any real Codex execution gate. No `codex` or `codex-reply` tool call ran.

## TDD evidence

The initial black-box suite failed because the production guard did not exist. After the first implementation, nine tests passed. Independent security review then produced three successive hardening cycles:

1. additive downstream input controls and unsolicited approval responses were reproduced, added as failing tests, and blocked;
2. duplicate client request IDs were added as a failing correlation test and blocked;
3. a child approval request reusing an in-flight client tool-call ID was reproduced, added as a failing cross-direction collision test, and blocked.

The final suite contains twelve black-box tests using a real guard subprocess and a fake Codex MCP child. It does not call a real Codex tool.

## Fresh evidence by layer

### Static and local contract

- macOS system Python 3.9 executes the guard and tests;
- twelve black-box tests pass with `ResourceWarning` promoted to an error;
- every emitted test protocol line is parsed as JSON;
- all pre-existing bridge zsh tests pass;
- Python compilation and `git diff --check` pass.

### Real local Codex MCP schema

A bounded local compatibility probe passed through the guard to `/Users/example-user/.local/bin/codex mcp-server` using only:

- `initialize`;
- `notifications/initialized`;
- `tools/list`.

The guard accepted the current downstream schema and returned exactly `codex` plus `codex-reply` with truthful action annotations and narrow public inputs. `tools/call` was not sent.

### Tunnel and ChatGPT

Not run in T-111. Pointing the existing Tunnel profile at the guard and rescanning the draft app is T-112.

### Real Codex task and filesystem

Not run. The configured local account still fails T-200, so there is no task, approval, thread-continuity, or write evidence.

## Independent review

The security reviewer initially returned `NO-SHIP` twice and supplied minimal reproductions for approval/schema and cross-direction ID-correlation weaknesses. After the regression fixes, the third review returned `SHIP` and could no longer reproduce a blocking bypass.

Residual non-blocking debt: child stderr is discarded to protect JSON-RPC stdout and avoid copying local identifiers into Tunnel logs. This reduces downstream diagnostics and may later be replaced with a structured redacted diagnostic channel.

## Score

T-111 score: **96/100**.

| Dimension | Score | Evidence |
|---|---:|---|
| Requirements coverage | 25/25 | FR-011 acceptance points have black-box coverage |
| Design/reference fidelity | 15/15 | official Codex remains downstream; public facade matches ADR 0002 |
| Correctness and tests | 25/25 | twelve tests, full existing suite, real downstream schema probe |
| Operator workflow | 9/10 | explicit CLI and runbook; Tunnel profile switch remains T-112 |
| Maintainability | 14/15 | Python stdlib only and complete schema pin; drift requires an intentional update |
| Runtime/operations evidence | 8/10 | real local `tools/list` passed; Tunnel/ChatGPT and Codex execution deliberately not run |

The remaining four points are outside the local T-111 contract or are low-risk observability debt. They must not be converted into a claim that the full ChatGPT-to-Codex chain is complete.
