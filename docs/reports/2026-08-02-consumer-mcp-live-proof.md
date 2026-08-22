# consumer ChatGPT MCP Live Proof

Date: 2026-08-02
Result: `PARTIAL_PASS`

## Scope

This run used the user's explicit authorization to enable ChatGPT Developer Mode, inspect connection types, add and authorize a trusted MCP Server URL, and run a harmless command. It did not create a Secure MCP Tunnel, install software, invoke local Codex, mutate a repository, or test a write-capable MCP action.

No account, workspace, organization, plugin, chat, tunnel, or credential identifiers are recorded.

## ChatGPT web evidence

- Account surface: consumer workspace.
- Developer Mode: enabled and verified from the checked switch state.
- Create-app entry: visible after activation.
- Connection choices: Server URL and Secure Tunnel.
- Authentication choices: OAuth, unauthenticated, and mixed.
- Tunnel picker: visible but reported no available tunnels.
- Platform access and Tunnel authorization are independent gates. A browser or
  unauthenticated network failure is not evidence that the local Guard failed,
  and no cookies or response tokens belong in a repository report.

## Custom MCP read proof

An OpenAI-hosted documentation MCP endpoint was used as a trusted, non-mutating probe.

- App creation: passed.
- Connector authorization: passed without OAuth.
- Tool discovery: five tools.
- UI classification: every discovered tool was labelled `读取`, `开放环境`, and public.
- Discovered tools: `fetch_openai_doc`, `get_openapi_spec`, `list_api_endpoints`, `list_openai_docs`, and `search_openai_docs`.
- Runtime proof: a fresh ChatGPT conversation explicitly selected the probe and invoked `search_openai_docs`; ChatGPT returned the first result title and displayed a tool activity record after 29 seconds.

This proves that the tested consumer rollout can create, authorize, discover, and execute a custom read-only MCP app. It does not prove custom MCP write support.

## Local Codex MCP evidence

- Selected executable: `/Users/example-user/.local/bin/codex`.
- Version: `codex-cli 0.146.0-alpha.3.1`.
- `mcp-server --help`: passed.
- MCP `initialize`: passed.
- MCP `tools/list`: passed with exactly two tools, `codex` and `codex-reply`.
- Normalized schema SHA-256: `e358b9f22c1048877ec7694037356a6970f92ea605c07e9aed8a906555303d30`.
- `codex` schema: requires `prompt`; exposes `cwd`, `sandbox`, `approval-policy`, model, instructions, and config.
- `codex-reply` schema: requires `prompt`; exposes `threadId` and the deprecated `conversationId` alias.

No Codex tool was invoked, so no thread ID or repository access was created.

## Open gates

1. Restore access to the Platform tunnel console and verify organization permissions without recording identifiers.
2. Obtain separate authorization before installing the official `tunnel-client`.
3. Create or associate a tunnel and confirm that ChatGPT discovers the local `codex` and `codex-reply` tools with honest action metadata.
4. Complete the isolation gate before any local Codex call.
5. Prove read-only behavior before considering an approval-gated bounded write.

## Verdict

`G0a custom read-only MCP = PASS` and `G1 local Codex tool discovery = PASS`.

`G0b target Codex connector`, tunnel transport, approval propagation, write behavior, and thread continuity remain `UNVERIFIED`. The overall pilot therefore remains `PARTIAL_PASS`.

## Milestone quality score

| Dimension | Score | Basis |
|---|---:|---|
| Scope and requirement coverage | 20/20 | The authorized UI, connection, authorization, discovery, runtime, and local-contract checks are all represented. |
| Evidence separation | 20/20 | ChatGPT UI/runtime, local MCP, Tunnel, and untested write claims are reported separately. |
| Safety and redaction | 20/20 | No identifier or credential is retained; no local Codex or write tool ran. |
| Verification quality | 19/20 | The read call and local schema were exercised; Platform Tunnel access is still blocked. |
| Spec and task consistency | 19/20 | Completed and open gates are reflected across requirements, design, tasks, ADR, runbook, and evidence. |
| **Milestone total** | **98/100** | The evidence milestone is complete; the system itself is not yet end-to-end. |

Independent read-only review: `PASS`; no `P0` or `P1` accuracy, consistency, or redaction issue was found.
