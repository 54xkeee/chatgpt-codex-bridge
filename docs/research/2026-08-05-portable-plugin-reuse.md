# Portable Plugin Kit Reuse Decision

Date: 2026-08-05
Task: `T-406`

## 1. Problem

- Capability: distribute the proven ChatGPT -> Secure MCP Tunnel -> guarded Codex bridge to another macOS user or device without hard-coded `/Users/example-user`, Tunnel identity, or credentials.
- Success: a repository marketplace exposes one installable plugin; its skill drives setup and one-conversation/one-thread use; a parameterized installer renders a user LaunchAgent and preserves the current personal full-control preset.
- Non-goals: reimplement Tunnel transport, publish credentials, automate the ChatGPT connector UI, or add Windows/Linux service management in this task.

## 2. Search coverage

### Local workspace

- Reuse `scripts/bridge/codex-mcp-guard.py`, its 14-test black-box suite, Codex binary resolver, and the T-405 LaunchAgent health/control-plane checks.
- Replace only the hard-coded service packaging. Do not replace the proven Guard protocol implementation.

### Local skills and templates

- `plugin-creator` supplies the required `.codex-plugin/plugin.json`, `skills/`, and repo marketplace structure.
- `skill-creator` supplies the concise workflow and validation rules.
- The locally installed official `tunnel-client 0.0.10` can export its own `tunnel-mcp` plugin and exposes native `runtimes` commands.

### GitHub

- Query: `openai tunnel-client plugin runtimes connect`.
- `openai/tunnel-client` is Apache-2.0, active on 2026-08-05, and is the canonical Tunnel transport/runtime dependency: https://github.com/openai/tunnel-client
- `openai/plugins` demonstrates required plugin manifests and optional skill/MCP surfaces: https://github.com/openai/plugins
- The official exported `tunnel-mcp` plugin is a thin router over the binary. Its pattern is reusable; its tunnel management must not be copied into this project.

### X Grok

- Route: local Safari-backed `x-grok-local`; health returned `status=ok`, `busy=false`.
- Query: recent OpenAI/practitioner posts about Secure MCP Tunnel, local MCP to ChatGPT, and Codex plugins.
- Official announcement confirms the outbound-only private MCP pattern: https://x.com/OpenAIDevs/status/2059703536825565499
- Practitioner examples consistently keep the local MCP private and attach ChatGPT through the official Tunnel; one example explicitly connects the same local MCP to Codex and ChatGPT: https://x.com/AndreiFedorov20/status/2082919282845868177
- These posts support the packaging direction but are not used as protocol authority.

### External success source

- The installed official binary successfully exported a self-contained plugin bundle to a temporary directory. The export contained a manifest, skill, scripts, and MCP surface, and `runtimes list --json` returned a valid local state document.
- This proves binary-owned plugin export and thin-router packaging are runnable patterns on the target Mac.

### Official/vendor

- Plugin packaging: https://developers.openai.com/plugins/build/plugins
- Skill packaging: https://developers.openai.com/plugins/build/skills
- MCP plugin surface: https://developers.openai.com/plugins/build/mcp-server
- Secure MCP Tunnel: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- Official `tunnel-client` documents `init`, `doctor`, `run`, plugin export/install, and native runtime status. The repository remains the protocol and release source of truth.

## 3. Candidate comparison

| Option | Fit | Adaptation | Maintenance | Runtime evidence | Security fit | Total / 25 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Skill only | 2 | 5 | 5 | 1 | 3 | 16 |
| Copy the official Tunnel plugin | 2 | 2 | 1 | 5 | 4 | 14 |
| Adapt current Guard + official plugin conventions + parameterized installer | 5 | 4 | 4 | 5 | 5 | 23 |
| New relay/agent service | 3 | 1 | 1 | 1 | 2 | 8 |

## 4. Runnable validation

| Candidate | Command | Result |
| --- | --- | --- |
| Official Tunnel plugin export | `tunnel-client codex plugin export --dir <temp>` | PASS; manifest, skill, scripts, MCP server exported |
| Official native runtime inventory | `tunnel-client runtimes list --json` | PASS; valid empty alias inventory returned |
| Current bridge | existing Guard and T-405 test suite | PASS at baseline; current live service remains the regression target |

## 5. Decision

- Verdict: **adapt**.
- Keep the existing Guard and macOS LaunchAgent semantics, but render all user/device values at install time.
- Package the installer and controller skill as a self-contained repo plugin.
- Depend on the official `tunnel-client`; never vendor or reimplement its protocol/client.
- Keep profile identity and runtime credential references outside Git.
- Preserve `personal-full-control` as this user's default and add an explicit `workspace-safe` preset for shared use. Neither preset is selectable from the public MCP tool schema.

## 6. Hardening result

- Dependency drift: validate `tunnel-client --version`, `doctor`, Codex `mcp-server --help`, plugin manifest, and the downstream tool contract before installation.
- Rollback: stop/unload the exact generated user LaunchAgent; uninstall removes only generated service/runtime files and leaves the external Tunnel profile intact.
- Observability: require LaunchAgent process, `/healthz`, `/readyz`, and a recent successful control-plane poll.
- Blast radius: generated files stay under the current user's Library and `~/.local/share`; no sudo or system daemon.
