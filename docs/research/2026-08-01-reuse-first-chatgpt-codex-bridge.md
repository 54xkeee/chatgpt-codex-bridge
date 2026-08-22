# Reuse-First Decision: ChatGPT–Codex Bridge

Date: 2026-08-01
Verdict: `adapt`

## Local Reuse

- The project contained no prior MCP, tunnel, or Codex bridge implementation.
- `/Users/example-user/.local/bin/codex` and the ChatGPT App bundled binary work and report `0.146.0-alpha.3.1`.
- `/opt/homebrew/bin/codex` fails with `ENOENT` because its packaged native binary is missing.
- `tunnel-client` is absent.
- Local MetaFusion, project-memory, PDF, planning, and reuse-research skills were reused for governance and evidence capture.

Conclusion: reuse an explicit working official Codex binary; do not build a local code agent.

## GitHub

Queries:

- `gh search repos 'tunnel-client user:openai'`
- `gh repo view openai/codex`
- `gh search code '"codex-reply" repo:openai/codex'`
- `gh issue list -R openai/codex --search 'mcp-server cwd workspace-write'`

Findings:

- [openai/codex](https://github.com/openai/codex) is actively maintained and Apache-2.0 licensed.
- [openai/tunnel-client](https://github.com/openai/tunnel-client) is actively maintained and Apache-2.0 licensed.
- The official Codex source contains the MCP server and `codex-reply` implementation.
- [openai/codex#18243](https://github.com/openai/codex/issues/18243) reports an open macOS failure where restricted sandbox modes fail through `mcp-server` while `danger-full-access` works. This is a test gate, not permission to use the unsafe mode.

GitHub status: success, independently queried through authenticated `gh`.

## X Grok

Preferred route:

- `x-grok-local --health` returned `status=ok`, `busy=false`.
- Two live Grok queries exited successfully but returned empty stdout, so Grok evidence was rejected.

Fallback route:

- `agent-reach` / `bird search` returned live X results.
- Practitioner posts show successful Codex-as-MCP setups from other MCP clients and describe Secure MCP Tunnel local-agent patterns.
- A recent first-hand report claims `cwd`/`workspace-write` failure in `codex mcp-server`, consistent with the upstream GitHub risk and therefore useful only as a warning signal.

Representative links:

- [Codex MCP setup example](https://x.com/flosstray/status/2074934778478944664)
- [Codex MCP command example](https://x.com/filligerr/status/2072483913352560669)
- [Reported workspace-write problem](https://x.com/soramame_256/status/2081954833066811619)
- [Secure Tunnel local-agent pattern](https://x.com/weacodi/status/2082161180760568168)

X status: Grok route failed with empty stdout twice; `agent-reach` fallback succeeded. Community posts are not treated as product guarantees.

## External Success Source

The supplied PDF, `CodeX额度不够？我让ChatGPT网页版接管电脑，连续干活67分钟`, is a 14-page N=1 case:

- it shows ChatGPT web using MCP to drive CanEngine for local download, installation, compilation, startup, and debugging;
- it shows a reported 67-minute continuous tool loop;
- it does not show Codex, `threadId`, `codex-reply`, a separate code-agent lifecycle, or asynchronous reverse wake-up.

Transferable pattern: a normal ChatGPT web conversation can be the supervisor when it has an MCP app. Non-transferable claim: the case does not prove ChatGPT-to-Codex orchestration.

## Official / Vendor

- [Developer mode and MCP apps](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt-beta): support varies by product plan and rollout, so the runtime proof remains capability-first.
- [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels): outbound HTTPS, separate Platform and ChatGPT permissions, stdio/HTTP support, health and doctor workflow.
- [Codex MCP Server](https://learn.chatgpt.com/docs/mcp-server): official `codex`, `codex-reply`, and `structuredContent.threadId` contract.
- [Codex App Server](https://learn.chatgpt.com/docs/app-server): separate rich-client JSON-RPC surface for threads, turns, streaming events, steer, interrupt, approvals, and reviews.

## Candidate Score

Scores are 0-5; higher is better except adaptation/maintenance burden, where higher means lower burden.

| Candidate | Fit | Adaptation | Maintenance | Evidence | Security fit | Total |
|---|---:|---:|---:|---:|---:|---:|
| Official Codex MCP + Tunnel, isolated proof | 5 | 5 | 4 | 4 | 3 | 21/25 |
| CanEngine-first | 2 | 4 | 3 | 2 | 2 | 13/25 |
| Custom MCP facade over App Server | 5 | 1 | 1 | 3 | 4 | 14/25 |
| Workspace Agent + custom relay first | 3 | 1 | 1 | 2 | 3 | 10/25 |

## Decision

Adapt the official Codex MCP + Secure MCP Tunnel path for an isolated proof. Do not build a replacement executor, relay, or event system. Add only the minimum policy-enforcement adapter required before real-repository use.

Main risks:

- account/workspace eligibility;
- tunnel workspace/organization association;
- raw unsafe tool arguments;
- macOS restricted-sandbox reliability;
- synchronous request lifetime and lack of reverse wake-up.

## Eligibility update — 2026-08-02

The target proof used a consumer workspace, and the CanEngine case described a non-enterprise flow. The PDF shows a `Plugins/Apps -> create plugin -> Server URL -> MCP authorization` path and reports real local mutation and command execution, but it does not establish permission metadata.

The PDF does not display the author's exact plan or MCP action metadata, so it cannot identify why the flow works. Plausible explanations include a published/allowlisted CanEngine app, a legacy or gray-rollout plugin surface, a current entitlement discrepancy, or side-effecting tools declared as read/fetch. The last case would be a safety failure, not a supported workaround.

Immediate next step: inspect the tested workspace UI and, only after separate authorization, capture tool discovery and declared permissions. Prefer direct Codex MCP if legitimately exposed; otherwise evaluate CanEngine as a bounded bridge to Codex. Do not infer permission from account labels or from one successful CanEngine run alone.

### Live UI evidence

A read-only inspection on 2026-08-02 confirmed that the tested consumer workspace has:

- a Plugins directory and installed-plugin settings;
- a Developer Mode link and switch;
- a high-risk warning that unverified connectors may permanently modify or delete data.

This was followed by an explicitly authorized live probe. Developer Mode was enabled; the create-app form exposed Server URL and Secure Tunnel; an OpenAI-hosted read-only MCP app was created and authorized; five tools were discovered and labelled `读取`; and `search_openai_docs` completed from a fresh ChatGPT conversation. This proves the tested custom read-only path. It does not prove that `codex` and `codex-reply` action tools will be accepted through a tunnel or that custom write is available.

## Metadata compatibility update — 2026-08-02

A same-day live comparison narrowed the failure:

- the successful OpenAI Docs MCP tools expose `readOnlyHint=true` and `destructiveHint=false`;
- the tested official `codex mcp-server` exposes `annotations: null` for both `codex` and `codex-reply`;
- OpenAI's current plugin reference says tool definitions need accurate safety annotations and lists `readOnlyHint`, `destructiveHint`, and `openWorldHint` as required fields.

This is a concrete compatibility defect in the raw Codex-as-ChatGPT-plugin path, although it is not yet causal proof of the silent persistence failure.

Reuse scan:

- MetaMCP supports tool overrides and annotations, but introduces Docker, a control plane, aggregation, and substantially more attack surface than this two-tool local proof needs.
- `mcp-chain` supports proxy transforms, but adds a third-party Python dependency and a more general middleware abstraction.
- the MCP Inspector bridges transports for inspection; it is not a policy-enforcing metadata transform.
- GitHub produced the options above; the focused X search produced no usable implementation evidence and is recorded separately rather than merged into the GitHub result.

Build-vs-buy decision: propose a dependency-free local stdio guard of minimal scope. It will preserve the official Codex agent, expose only the two known tools, add truthful conservative annotations, narrow their public schemas, inject fixed safe arguments, filter the child environment, and fail closed on drift. This is smaller and more auditable than deploying a general MCP gateway. Implementation remains pending the repo-required confirmation before code edits.
