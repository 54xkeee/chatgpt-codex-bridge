# Secure Tunnel Consumer-Workspace Action Gate

Date: 2026-08-02

Scope: explicitly authorized installation of the official OpenAI Tunnel Client, creation and association of one Secure Tunnel, ChatGPT draft-app discovery, and a bounded attempt to reach the Codex MCP tools. No raw account, workspace, organization, project, tunnel, API-key, request, plugin, chat, or Codex thread identifiers are recorded.

## Outcome

The transport path reached the local Codex MCP server, but the requested end-to-end write loop did not pass.

- Official Tunnel Client installation: `PASS`
- Tunnel creation and Personal workspace association: `PASS`
- Runtime key with restricted Tunnel Read + Use permissions: `PASS`
- `tunnel-client doctor --explain`: `PASS`
- Local tunnel health, readiness, and UI: `PASS` (`HTTP 200` for all three)
- ChatGPT Tunnel picker: `PASS`; the created tunnel was selectable
- ChatGPT draft-app scan transport: `PASS`; each attempt delivered two RPC requests to the local MCP server. Payload capture was disabled, so identifying them as the usual MCP `initialize` and `tools/list` pair is an inference from the visible Scan/Create workflow, not direct payload evidence.
- Saving the Codex draft app on the tested consumer workspace: `FAIL_CLOSED`; three bounded attempts returned the form to an enabled state without creating an installed draft or showing a user-visible error
- First `codex()` call: `NOT_RUN`
- `codex-reply()` continuity: `NOT_RUN`
- Workspace write: `NOT_RUN`
- Tunnel stop/local revocation: `PARTIAL_PASS`; the local readiness endpoint became unreachable after stopping the daemon, but the required post-stop remote tool-call failure could not be tested because no draft app persisted

## Installation and integrity evidence

- Release source: official `openai/tunnel-client` GitHub release metadata.
- Installed release: stable `v0.0.10`, Darwin arm64.
- Archive integrity: the matching official `SHA256SUMS.txt` entry passed before extraction.
- Archive shape: exactly one `tunnel-client` executable was accepted.
- Install location: user-owned `/Users/example-user/.local/bin/tunnel-client`; no `sudo` was used.
- Reported version: `0.0.10`.

The generated local profile points to the explicitly verified `/Users/example-user/.local/bin/codex mcp-server`. The profile is outside the repository and is not committed.

## Tunnel and ChatGPT evidence

The Platform UI accepted a tunnel scoped to a consumer ChatGPT workspace. A restricted runtime key was created for the proof, transferred through a mode-`0600` one-time file, inherited only by the foreground daemon, then removed from the host and clipboard. No secret was printed or committed.

`doctor --json --explain` passed configuration loading, tunnel identifier format, runtime-key reference, MCP command availability, loopback health binding, and UI checks. Stdio reachability and OAuth metadata were correctly skipped. The optional Codex Tunnel plugin was not required for this stdio profile.

The foreground daemon started `codex mcp-server`, exposed a loopback-only health UI, and recovered from a short series of control-plane `EOF` failures. ChatGPT's create-app form then listed the tunnel. With Tunnel selected and target authentication set to unauthenticated, each create attempt caused two requests to reach the local dispatcher, consistent with MCP initialization and tool discovery. Raw payload capture remained disabled, so the report does not claim direct method-level evidence. The app was never persisted to the installed-app list.

## Capability and isolation decision

Three evidence and isolation gates prevent a safe write claim, but account tier is not diagnosed as the cause:

1. The supplied external case demonstrates a ChatGPT web -> MCP -> local-executor loop that performed local writes and commands. The PDF export does not display MCP tool metadata, so the case is compatibility evidence rather than permission evidence.
2. On the tested consumer workspace, a separate five-tool read-only MCP probe worked, while the Codex draft app reached the local dispatcher but did not persist. That difference remains undiagnosed. Plausible explanations include incomplete tool metadata, product-specific validation, connector classification, rollout behavior, or a transient UI defect.
3. The original test plan required an isolated host boundary before the first Codex agent tool call. That gate was not satisfied in this proof, so no agent call was attempted.

A later same-day metadata comparison produced a stronger compatibility hypothesis: the successful OpenAI Docs tools declare read-only and non-destructive annotations, while both raw Codex tools return `annotations: null`. OpenAI's plugin reference lists accurate read-only, destructive, and open-world annotations as required tool metadata. This defect is confirmed; whether it caused the silent draft failure remains unverified.

Therefore the observed `tools/list` transport is not counted as a successful ChatGPT Codex connector, and no Codex tool was invoked. The failed draft-app persistence is a target-specific unresolved result, not a general entitlement conclusion.

## Residual external state

- The Platform tunnel resource remains created and associated.
- The restricted runtime API-key object remains listed in Platform, but its secret was not persisted locally after the daemon stopped.
- The local Tunnel Client binary and redacted profile remain installed for a future guarded-connector retry.
- No ChatGPT Codex draft app was created.

Deleting the Platform tunnel or API-key object is intentionally left as a separate explicit destructive action.

## Next safe route

Do not change account tier before resolving the connector difference. Continue in this order:

1. after the repo-required confirmation, implement and contract-test the proposed narrow stdio guard that adds truthful conservative action annotations, removes unsafe public parameters, and injects fixed local policy;
2. point the existing Tunnel profile at that verified guard and rescan the draft app without invoking a tool; record whether ChatGPT persists the honestly annotated actions;
3. CanEngine remains unclassified because it is outside this package; if later
   authorized, inspect its visible tool names and declared read/action labels
   without executing another write;
4. if the guarded direct route still fails and CanEngine honestly exposes side-effecting actions, evaluate a bounded CanEngine -> Codex bridge inside the same isolation and approval requirements; do not mislabel writes as reads;
5. separately authorize and provision a sterile non-admin macOS account or disposable VM/profile before the first Codex agent call; and
6. once a connector legitimately exposes the Codex tools, rerun read-only, approval, bounded write, `codex-reply`, and revocation gates in order.

A Business or Enterprise/Edu workspace remains a documented fallback, not a prerequisite established by this run.

## Official references

- [Developer mode and MCP apps in ChatGPT](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt-beta)
- [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [OpenAI Tunnel Client releases](https://github.com/openai/tunnel-client/releases)
- [Tunnel Client onboarding](https://github.com/openai/tunnel-client/blob/master/docs/onboarding.md)
