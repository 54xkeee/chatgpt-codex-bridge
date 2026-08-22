# T-303 Timeout Adaptation

Date: 2026-08-03
Classification: `PASS`

## Outcome

The first end-to-end synchronous call reached the local tool but the
intermediary response window closed before a thread identity returned. The
repository baseline remained unchanged.

Local reproduction established that the Guard protocol was not the failure
source: both ordinary and reduced prompts completed locally, but duration was
variable and progress notifications did not extend the Tunnel command
deadline. Exact host timings are intentionally omitted because they are not a
portable SLA.

Per-call model tuning reduced some runs but did not make duration deterministic.
The durable async facade is therefore the supported long-work adaptation. Raw
thread identities were held only in runtime state and were not written to Git,
reports, or project memory.

## Follow-up cached-app compatibility finding

A second retry failed closed before Codex execution with `Downstream tool
contract has not been verified`. The repository baseline and transport health
remained unchanged.

The retry established a distinct lifecycle gap: after Tunnel restarted the stdio child, ChatGPT reused its cached app schema and issued `tools/call` without first sending a client-side `tools/list`. T-114 now sends the downstream initialized notification and validates an internal raw `tools/list` before returning the first client initialization response. A contract mismatch still rejects initialization and terminates fail-closed.

## Final remote proof

After committing T-114, a fresh mode-600 T-202 baseline captured the clean commit, branch, empty Git status, all 35 tracked entries, and their aggregate manifest. The Tunnel was restarted and passed process, health, readiness, and control-plane polling checks.

A fresh attached ChatGPT conversation then called `Codex MCP Guard` once in
read-only mode. Codex returned the requested bounded summary, and ChatGPT
reported only that a thread identity existed. No duration is retained or
treated as a guarantee.

The post-call comparison matched Git HEAD, branch, status, every one of the 35 tracked entries, and the aggregate SHA-256 manifest. Tunnel health and readiness remained green, and the Guard plus Codex MCP child were still live. No approval was requested or surfaced. The prompt prohibited network access, but this run did not include independent network telemetry, so the report does not elevate that requested constraint into a separately observed fact.

## Blocker research

### Local Reuse

- Reused the existing Guard's server-side fixed-argument injection rather than changing global Codex configuration or exposing raw config to ChatGPT.
- Rejected prompt shortening as the primary fix because a minimal prompt could
  still exceed the intermediary response window.
- Rejected increasing `mcp.connection-max-ttl`; it bounds transport connection lifetime and does not override a control-plane response deadline.

### GitHub

- The official [Tunnel protocol](https://github.com/openai/tunnel-client/blob/master/docs/protocol.md#response-timeout) defines `response_timeout` as a per-command lifecycle deadline anchored at poll receipt. It explicitly states that progress notifications do not restart the deadline and that the client must cancel MCP work when it expires.
- Searches of the official repository found no issue documenting a client-side flag to extend this control-plane deadline. The local `run --help` surface likewise exposes no per-command response-timeout override.

### X Grok

- The local Grok bridge was healthy. Its first response was only a search expression, so the required retry was run and returned a usable evidence brief.
- Public practitioner patterns favor async start/status polling for long MCP work and lowering reasoning effort for latency-sensitive Codex tasks. Representative posts included an [async connector wrapper](https://x.com/Hriday_xbt/status/2083431685295915347), a [polling-based long-work pattern](https://x.com/ColdShalamov/status/2082221878119481512), and [reasoning effort as a latency tradeoff](https://x.com/9vjxc7cypd/status/2078571699058975159).
- No X post was found that documents a supported way to raise the Secure Tunnel control-plane deadline.

### External success source

- OpenAI's [Codex MCP Agents SDK example](https://github.com/openai/openai-cookbook/blob/main/examples/codex/codex_mcp_agents_sdk/building_consistent_workflows_codex_cli_agents_sdk.ipynb) uses a very large MCP client session timeout, confirming that Codex MCP work may legitimately outlive ordinary synchronous tool windows when the host permits it.

### Official / Vendor

- The current Codex manual documents per-call `model` and `config` overrides, recommends `gpt-5.6-terra` for faster read-heavy scans, lists `model_reasoning_effort=low` for straightforward latency-sensitive tasks, and warns that higher effort increases response time.
- The official Tunnel protocol makes the response deadline a control-plane input, not a local profile option.

### Decision

Verdict: `adapt`.

For bounded read-only scans, inject Terra + low and validate the downstream tool contract during initialization. This is the smallest reversible combination that passed a real no-client-list Codex smoke test while preserving the operator's configured model and reasoning for workspace-write threads. An asynchronous start/status facade is the correct later design for genuinely long work, but it is outside this first read-only proof and would require new tool schemas, persistence, cancellation, and polling tests.

## Verification

- Focused tests were observed failing before implementation for the missing read-only model override and the unverified immediate first call.
- Focused tests passed after the two minimal adaptations.
- Full Guard suite: 13/13 passed.
- Guarded bounded call without a client `tools/list`: success, thread identity
  present, no approval request, Guard alive through response.
- Final ChatGPT -> Tunnel -> Guard -> Codex call: success, requested summary
  returned, thread identity presence confirmed without value disclosure.
- Final T-202 comparison: HEAD, branch, status, 35/35 tracked entries, and aggregate manifest all matched.
- Post-call runtime: Tunnel process, health, readiness, Guard process, and Codex MCP process all passed.
