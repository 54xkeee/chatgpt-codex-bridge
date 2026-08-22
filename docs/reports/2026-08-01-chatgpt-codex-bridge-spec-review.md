# ChatGPT–Codex Bridge Spec Review

Date: 2026-08-01
Review target: planning package only
Runtime status: `PARTIAL_PASS_CUSTOM_READ_MCP_CONFIRMED` (updated 2026-08-02)

## Score

| Dimension | Score | Evidence |
|---|---:|---|
| Requirements coverage | 25/25 | Testable functional, safety, reliability, non-goal, and promotion gates are present. |
| Evidence accuracy | 19/20 | PDF, local CLI, official docs, GitHub, and X fallback evidence are separated; account UI remains unverified. |
| Security containment | 24/25 | Raw MCP is confined to an isolated proof, unsafe relaxation is prohibited, and real-repo promotion requires enforcement. OS-profile cleanliness still includes an operator attestation. |
| Implementation readiness | 19/20 | Ordered tasks, files, commands, expected results, stop conditions, and commits are defined. Actual ChatGPT UI labels may drift during beta. |
| Maintainability | 9/10 | Official components are reused and optional layers are deferred. The app-bundled versus standalone Codex binary decision remains open. |
| **Total** | **96/100** | Planning package is ready for user validation; the system itself has not been installed or proven. |

## Independent review findings resolved

- Corrected `codex-reply` schema semantics: only `prompt` is schema-required in the tested build; new calls still require the bridge to supply `threadId`.
- Replaced an impossible claim of automatically proving all profile secrets absent with bounded checks plus explicit operator attestation.
- Separated raw-MCP preflight checks from future server-side enforcement-adapter guarantees.
- Corrected draft-app tool scanning to occur before opening the test conversation.
- Allowed future additional MCP tools while requiring separate review.
- Marked unsafe-string search as a manual review queue, not an automated assertion.

## Gate update — 2026-08-02

- The target proof used a consumer workspace.
- The user also confirmed the supplied CanEngine case used a non-enterprise account; the PDF shows the plugin creation and MCP authorization flow but not the exact plan or tool metadata.
- At the time of the proof, official documentation limited full custom MCP write support by product plan, creating an evidence conflict rather than proving the observed route impossible.
- Read-only UI and tool-metadata discovery may proceed; no installation, connector authorization, or side-effecting call proceeds without separate authorization.
- A same-turn read-only inspection confirmed Plugins settings and a high-risk Developer Mode switch on the tested consumer workspace.
- After explicit authorization, the switch was enabled; Server URL and Secure Tunnel creation appeared; an OpenAI-hosted read-only MCP probe was created, authorized, scanned as five read tools, and invoked successfully.
- Local MCP discovery independently confirmed exactly `codex` and `codex-reply`; they have not yet been exposed through ChatGPT.

## Open gates

- Restore access to the Platform tunnel console; the ChatGPT tunnel picker currently has no available tunnels.
- Classify the CanEngine connection and its declared tool permissions.
- Confirm Platform-to-ChatGPT tunnel association and scan the target Codex tools.
- Install and verify `tunnel-client` only after authorization.
- Reproduce the macOS `workspace-write` behavior without relaxing permissions.

## Decision

The planning package remains valid with a corrected capability-first gate. Custom read-only MCP and local Codex tool discovery passed independently; the combined Tunnel path is not yet proven. The direct Tunnel path remains preferred, with CanEngine retained as a bounded fallback rather than dismissed by plan tier alone.
