# Tunnel LaunchAgent Reuse Decision

Date: 2026-08-05
Decision: `adapt`

## Local Reuse

- Existing profile `example-profile` passes `tunnel-client doctor --explain` and already points to the reviewed Guard and `/Users/example-user/.local/bin/codex`.
- Existing user services such as `com.remodex.bridge` demonstrate the local `RunAtLoad`, `KeepAlive`, absolute `ProgramArguments`, and stable log-path pattern.
- The old Tunnel runtime had no LaunchAgent; its final record was an operational poller recovery followed by process disappearance.
- A first LaunchAgent smoke with `WorkingDirectory=~/Documents/chatgpt-code` blocked in `getcwd` before opening files or sockets. The adapted design uses its non-protected Application Support directory and absolute target paths.
- A real connector call then showed the Guard's Python process blocking in `open` on the source file under `~/Documents`. An Application Support runtime copy removed TCC but exposed Tunnel's space-tokenization behavior (`exit status 2`). The final adaptation stages the Guard under `~/.local/share/chatgpt-codex-bridge/` and overrides only `--mcp.command`, preserving the existing profile and secrets.
- Reuse the existing profile and native `launchd`; do not build another daemon or copy credentials.

## GitHub

- Query: `"SuccessfulExit" "RunAtLoad" language:XML`.
- Datadog Agent and CodeAbra's MCP daemon templates use normal LaunchAgent plists with explicit arguments and persistent process semantics.
- References:
  - https://github.com/DataDog/datadog-agent/blob/daf42da470291f772ff22accfc509f547cbcbb2c/cmd/ai_prompt_logger/com.datadoghq.ai-usage-agent.desktop-monitor.plist.example
  - https://github.com/CodeAbra/iai-personal-memory-engine/blob/9758046c4616b77ea1a5ad7f4f1410080aa6afc4/scripts/com.iai-mcp.daemon.plist.template
- Result: adapt the standard plist pattern; no external package is needed.

## X Grok

- Local bridge health returned `status=ok`, `busy=false`.
- Two Grok queries returned only generated search terms rather than post evidence after the built-in continuation path.
- `bird search` then failed to read Safari cookies with `EPERM`, reported no Twitter cookies, and returned no posts.
- Result: X evidence unavailable this turn; this failure is separate from successful GitHub and official-source checks.

## External Success Source

- The Mac already runs `com.remodex.bridge` successfully as a user LaunchAgent with `RunAtLoad`, restart-on-failure behavior, absolute paths, and persistent stdout/stderr files.
- This directly matches the same-machine lifecycle needed by a long-running local CLI bridge.

## Official / Vendor

- OpenAI documents `tunnel-client run --profile <name>` and says app discovery/tool calls depend on keeping that process healthy: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- Apple documents user LaunchAgents under `~/Library/LaunchAgents`, unique `Label`, tokenized `ProgramArguments`, `KeepAlive`, and log paths: https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html
- The installed Tunnel client documents `--health.listen-addr` and `--health.url-file`. The live install showed profile values can override environment values, so the LaunchAgent uses explicit CLI arguments for a stable loopback health pointer without a fixed port.

## Decision

- Verdict: `adapt`.
- Use one native user LaunchAgent around the official run command.
- Keep credentials only in the existing profile/key file and keep the plist free of Tunnel identifiers.
- Validate with static plist tests, live `launchctl` state, health/readiness, and a forced-restart PID change.
