# ChatGPT Codex Bridge

[中文图文说明与避坑指南](README.zh-CN.md) ·
[GitHub 发布脱敏清单](docs/GITHUB_RELEASE_CHECKLIST.zh-CN.md)

Spec-driven project. Start by writing or updating specs under docs/specs before implementation.

Version 0.6.1 is the security-hardened release of the parameterized
macOS bridge. `codex-start` creates a unique child project root, registers it
with the Codex desktop app, creates a canonical App Server project/task, and
passes the bundled `workspace-new-project` Skill explicitly before
implementation. `codex-wait` joins long-running work while an Apps card remains
the explicit interrupted-turn recovery path.

The repo marketplace is `.agents/plugins/marketplace.json`; the plugin includes a controller Skill, reviewed Guard, parameterized login service, and install/doctor/uninstall commands. Device-specific Tunnel identity, capability signing key, raw thread IDs, request IDs, and credentials stay outside Git.

The `personal-full-control` preset exposes `codex-start(prompt, projectName?)` for new projects, `codex-reply-async(prompt, threadId)` for same-project continuation, model-visible `codex-wait(jobId)` for bounded same-turn joins, `codex-job-open(jobId)` to reopen an existing job card without starting another Codex run, and an app-only `codex-job-status(jobId)` polling tool. Public `threadId` and `jobId` values are installation-scoped signed bearer capabilities, not raw local IDs. Async admission defaults to a 256 KiB prompt, two active jobs, 512 retained records, and a four-hour worker deadline. `projectName` becomes both the sidebar display name and a sanitized unique directory stem; callers cannot supply an arbitrary filesystem path. Short synchronous `codex` and `codex-reply` remain available for diagnostics. The portable installer defaults to `personal-full-control` (`danger-full-access` + `never`) and also supports the locally fixed `workspace-safe` preset; the caller cannot select policy values.

Install, restart, diagnose, or uninstall the service through the parameterized plugin commands in `docs/runbooks/portable-plugin.md`. In ChatGPT web, select `Codex MCP Guard` from `+` and verify its pill is visible before sending the task; merely seeing the app elsewhere does not attach its tools to that conversation. The Guard binds signed capabilities to the installation workspace and policy, bounds sync and async resource use, and treats Codex result text as untrusted tool data. `stop`, reinstall, and uninstall revoke verified bridge-owned process groups; uninstall also removes bridge-owned capability/job state while preserving Codex conversation history and the external Tunnel profile. While a response remains active, ChatGPT repeatedly calls `codex-wait`; if the browser or model turn closes, reopen the component and click the explicit return control. This is not unsolicited reverse push.
