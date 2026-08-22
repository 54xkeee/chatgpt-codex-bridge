# Personal Full-Control Adaptation Decision

Date: 2026-08-03
Task: `T-115`

## Reuse scan

- Local: the existing dependency-free Guard already supplies the two required public tools, Tunnel initialization replay, downstream schema validation, environment filtering, and JSON-RPC forwarding. Only its policy facade and tests need adaptation.
- GitHub: the existing research baseline uses OpenAI's official `tunnel-client` protocol and its response-deadline behavior; no replacement transport is needed.
- X/community: the existing T-303 research found examples of remote Codex/MCP control and long-running tool loops. They support the interaction pattern but add no primitive beyond the official thread tools.
- External implementation: OpenAI's Cookbook demonstrates multi-agent workflows using the Codex MCP server; adapting the installed official server remains lower risk than introducing a new controller.
- Official: Codex documents `danger-full-access` as removing filesystem/network sandbox boundaries and `never` as disabling approval prompts. `codex` and `codex-reply` are the required start/continue primitives.

## Build versus adapt

Adapt the current Guard. Building a new relay, mapping database, approval service, Workspace Agent, CanEngine chain, or App Server wrapper would add state and failure modes without improving the requested one-conversation/one-thread interaction.

## Selected design

Public `codex(prompt)` starts the conversation's Codex thread with fixed full local access and no approvals. ChatGPT writes the returned value as `Codex thread: <threadId>` in its response, and public `codex-reply(prompt, threadId)` continues it on later turns. Contract validation and secret filtering remain invisible implementation details.

Sources: [Codex security](https://learn.chatgpt.com/docs/security), [Codex MCP server](https://learn.chatgpt.com/docs/mcp-server), [Tunnel protocol](https://github.com/openai/tunnel-client/blob/master/docs/protocol.md#response-timeout), [OpenAI Cookbook Codex MCP workflow](https://github.com/openai/openai-cookbook/blob/main/examples/codex/codex_mcp_agents_sdk/building_consistent_workflows_codex_cli_agents_sdk.ipynb), and the GitHub/X references recorded in `docs/reports/2026-08-03-t303-timeout-adaptation.md`.

## Implementation and live evidence

- Public discovery through the real local Codex child returned only prompt-only `codex` and strict `codex-reply` with truthful action annotations.
- Thirteen Guard black-box tests passed after an observed red phase against the old mode/read-only implementation.
- The active Tunnel profile no longer contains `--allow-workspace-write`; `/healthz`, `/readyz`, and `doctor` passed after restart.
- The ChatGPT-specific `Codex MCP Guard` permission was set to `full_access` and read back as full access with no inherited/default override.
- A controlled connector call created a named disposable file outside the
  configured repository, returned a thread identity, and did not pause for an
  approval prompt.
- The continuation call reused that identity and appended the expected second
  line. Exact duration and host paths are deliberately omitted.
- A separate longer initial call completed its exact filesystem write but returned a tool error before its thread ID arrived. This is evidence that full permissions work and that synchronous result latency remains a separate limitation.
- All bridge shell suites, Python compilation, and `git diff --check` passed.

### ChatGPT web evidence

- The installed consumer developer-mode app was refreshed and visibly changed from the old `prompt + mode` schema to prompt-only `codex` plus strict `codex-reply`.
- A fresh web conversation invoked prompt-only `codex`, wrote exact disposable
  proof content, and reported thread-ID presence.
- The next web turn could not call `codex-reply` because the test had required the first response to hide the value; ChatGPT stated that it had not retained the ID.
- The bridge was therefore adapted to require one compact visible `Codex thread: <threadId>` line. The web app was refreshed again and visibly showed that exact start/continue contract.
- T-308 isolated that failure to the ChatGPT conversation: its composer lacked the `Codex MCP Guard` attachment while Tunnel, Guard, plugin-specific `full_access`, and a fresh direct backend call all passed. The selected model was 5.6 Sol at the time of inspection, so the earlier Mini notice was not causal evidence.
- Reopening the app detail and choosing `在聊天中试用` created a fresh
  conversation with the app pill visibly attached. Web `codex` created the
  first proof line and emitted a visible thread tag; `codex-reply` appended the
  second line. Both tags were non-empty and identical.

No raw thread, tunnel, workspace, or credential identifiers were written to the repository or project memory.

## Delivery score

| Dimension | Score | Evidence |
|---|---:|---|
| Required interaction | 20/20 | attached web conversation completed start and same-thread reply |
| Architecture simplicity | 20/20 | two public tools; no new service or state store |
| Policy correctness | 20/20 | Codex full access/no approval plus ChatGPT plugin full access verified |
| Tests and protocol integrity | 20/20 | all suites, schema refresh, visible tag, and identity equality pass |
| Runtime evidence | 19/20 | connector and web write/reply pass; three-run repeatability remains open |
| **Total** | **99/100** | T-308 is closed; repeatability remains the only score gap |
