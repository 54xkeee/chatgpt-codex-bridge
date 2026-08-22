# Durable Codex Web Return Proof

Date: 2026-08-10
Scope: ChatGPT web -> Secure MCP Tunnel -> durable local Codex -> same ChatGPT conversation
Result: PASS with one explicit return click

## What was proven

1. A fresh ChatGPT web conversation with the visible `Codex MCP Guard` pill
   called `codex-start` rather than the synchronous `codex` tool.
2. The MCP call returned quickly with a durable job handle and ChatGPT's model
   turn ended while local Codex continued running.
3. The local job reached `completed`, persisted a Codex thread identity, and
   contained the exact requested marker. No project file read or write was
   requested by the smoke prompt.
4. The MCP Apps component polled the private `codex-job-status` tool and showed
   the terminal result after the original ChatGPT turn had ended.
5. Clicking `把结果发给 ChatGPT 审查` called the host follow-up API, created a
   new turn in the originating conversation, and ChatGPT replied with the exact
   Codex marker.
6. The Tunnel LaunchAgent remained locally ready and connected to the control
   plane after the updated Guard was installed.

Durable evidence intentionally records only status and identifier presence.
Job IDs, Codex thread IDs, Tunnel identifiers, request identifiers, endpoint
values, and credentials are omitted.

## Corrected platform boundary

The first component revision attempted `sendFollowUpMessage` automatically
after observing a terminal job. In the live ChatGPT web client, that Promise
resolved and the component displayed a success message, but the conversation
did not gain a new turn. Reloading the conversation confirmed that no message
had been stored.

The final component requires one explicit user click. With that user gesture,
the same documented API created the new ChatGPT turn and the assistant reviewed
the exact Codex result. Therefore this project claims:

- durable local Codex execution after the ChatGPT model turn ends;
- restart-safe local status and result recovery;
- same-conversation result return with one click;
- deferred recovery after reopening the conversation.

It does not claim zero-click reverse wake-up while consumer ChatGPT is inactive.

## Compatibility repair

The first live component load returned `Failed to fetch template`. ChatGPT's
resource request included standard transport metadata, while the Guard required
an exact one-field request. The Guard now accepts optional `_meta` on
`resources/list` and `resources/read` while retaining strict URI and type
validation. After the repair and app refresh, ChatGPT discovered the versioned
component and loaded it successfully.

## Verification

- 21 Guard contract tests passed.
- Portable plugin package validation passed.
- Packaged and personal Guard sources matched byte-for-byte.
- Direct MCP discovery exposed the five intended tools and the Apps resource.
- Live ChatGPT web start, detached local completion, component status read,
  explicit follow-up, and exact same-conversation assistant response passed.

## T-407 delivery score

Focused tranche score: **95/100**.

| Dimension | Score | Evidence / remaining gap |
|---|---:|---|
| Requirements coverage | 29/30 | Durable start, storage, status, thread identity, return, and inactive-page recovery are covered; zero-click consumer wake-up is explicitly out of scope. |
| Correctness and tests | 24/25 | Contract and live start/return paths passed; async same-thread reply is contract-tested but not part of this live marker run. |
| UX and workflow | 17/20 | ChatGPT no longer waits for Codex; the host still requires one return click. |
| Maintainability | 15/15 | Reuses the existing Guard, official component API, versioned resource, and self-contained plugin. |
| Runtime and operations evidence | 10/10 | Installed source match, LaunchAgent readiness, control-plane connection, and live web proof passed. |

The remaining five points require a different product capability, such as a
supported external trigger, if zero-click wake-up is ever made a requirement.
