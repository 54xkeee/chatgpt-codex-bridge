# ChatGPT–Codex Bridge Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prove that an eligible ChatGPT web conversation can safely start and continue a local Codex thread through Secure MCP Tunnel in an isolated sandbox.

**Architecture:** Reuse the official Codex MCP Server and Secure MCP Tunnel. Run the raw proof only in a sterile non-admin macOS profile or disposable VM, use a non-sensitive repository, and stop at every failed permission or containment gate. Defer CanEngine, App Server integration, policy facade, and asynchronous wake-up.

**Tech Stack:** OpenAI Codex CLI/MCP Server, OpenAI Secure MCP Tunnel client, MCP Inspector, zsh, Git, SHA-256, ChatGPT web Developer Mode.

---

## Preconditions

- Current gate (updated 2026-08-02): T-108 and T-109 passed after explicit authorization. Developer Mode is enabled; Server URL and Secure Tunnel are exposed; an OpenAI-hosted read-only MCP probe was created, authorized, scanned, and invoked successfully. T-102 and T-103 also passed locally. No tunnel, write-capable connector, or Codex task has run.
- Work in a dedicated worktree on a `codex/` branch.
- Read `docs/specs/chatgpt-codex-bridge/requirements.md`, `design.md`, and ADR-0001 first.
- Obtain explicit user authorization before installing `tunnel-client`, creating an OS account/VM, changing ChatGPT/Platform configuration, or starting a write-capable remote tool.
- Never print or persist API keys, tunnel IDs, workspace IDs, tokens, private endpoints, browser cookies, or raw thread IDs.

### Task 1: Validate account and workspace eligibility

**Files:**

- Create: `docs/runbooks/chatgpt-workspace-eligibility.md`
- Create: `evidence/examples/eligibility.redacted.example.md`
- Modify: `docs/specs/chatgpt-codex-bridge/tasks.md`

**Step 1: Write the failing evidence checklist**

Keep the redacted example aligned with the tested consumer evidence while target Codex and Platform permission fields remain `UNVERIFIED`:

```markdown
plan: consumer
official_plan_supports_full_custom_mcp_write: FAIL
non_enterprise_canengine_case: USER_CONFIRMED
plugins_directory_visible: PASS
developer_mode_visible: PASS
developer_mode_enabled: YES
write_delete_risk_warning_visible: PASS
custom_app_create_visible: PASS
server_url_connection_visible: PASS
tunnel_connection_visible: PASS
available_tunnel_present: FAIL
platform_tunnel_console_reachable: FAIL
platform_tunnels_read_use: UNVERIFIED
trusted_read_probe_connected: PASS
trusted_read_probe_permissions_reviewed: PASS_READ_ONLY
trusted_read_probe_call: PASS
local_codex_tools_discovered: PASS
chatgpt_codex_tools_discovered: UNVERIFIED
declared_codex_tool_permissions_reviewed: UNVERIFIED
result: PARTIAL_PASS
```

**Step 2: Verify the checklist fails closed**

Run:

```bash
rg -n 'UNVERIFIED' evidence/examples/eligibility.redacted.example.md
```

Expected: account-specific UI fields pass, activation and tool fields remain unverified, and no connector or write task is promoted.

**Step 3: Document the manual verification path**

The runbook must instruct the operator to verify ChatGPT web plan/workspace, Developer mode, Apps/Create, Tunnel connection, and Platform tunnel permissions. It must state that read/fetch access does not satisfy the write pilot.

**Step 4: Lint for forbidden identifier shapes**

Run a narrow secret scan against versioned planning/evidence files. Expected: no API key, raw tunnel ID, raw workspace ID, or token value.

**Step 5: Commit**

```bash
git add docs/runbooks/chatgpt-workspace-eligibility.md evidence/examples/eligibility.redacted.example.md docs/specs/chatgpt-codex-bridge/tasks.md
git commit -m "docs: add ChatGPT MCP eligibility gate"
```

### Task 2: Build the local Codex resolver and preflight

**Files:**

- Create: `scripts/bridge/resolve-codex-bin.zsh`
- Create: `scripts/bridge/local-preflight.zsh`
- Create: `tests/bridge/test-resolve-codex-bin.zsh`
- Create: `tests/bridge/test-local-preflight.zsh`

**Step 1: Write failing resolver tests**

Cover:

- explicit `CODEX_BRIDGE_BIN` pointing to an executable wins;
- missing explicit binary fails;
- every candidate is accepted or rejected by `--version` plus `mcp-server --help`; the currently broken `/opt/homebrew/bin/codex` therefore fails without becoming a permanent path blacklist;
- ChatGPT App bundled binary is accepted only if `--version` and `mcp-server --help` pass;
- the selected path is printed, but environment contents are not.

**Step 2: Run tests and confirm failure**

```bash
zsh tests/bridge/test-resolve-codex-bin.zsh
```

Expected: FAIL because the resolver does not exist.

**Step 3: Implement the minimal resolver**

Use an explicit candidate list and validate each candidate by executing `--version` and `mcp-server --help`. Do not repair, reinstall, or mutate PATH.

**Step 4: Add preflight checks**

The preflight must report only:

- resolved executable path;
- Codex version;
- `mcp-server` availability;
- `tunnel-client` availability/version;
- current user admin/non-admin status;
- approved sandbox path presence;
- pass/fail status.

It must not enumerate Keychain, cookies, SSH key contents, environment values, or home-directory filenames.

It may test the existence of a fixed, documented set of forbidden indicators such as the dedicated profile's `.ssh` directory or configured browser-profile roots, without listing their contents. Pair this with a signed operator attestation that the new profile has never been used for personal or production accounts. Any uncertainty is `UNVERIFIED` and stops the pilot.

**Step 5: Run tests**

```bash
zsh tests/bridge/test-resolve-codex-bin.zsh
zsh tests/bridge/test-local-preflight.zsh
```

Expected: PASS, with the working explicit Codex path selected and absent `tunnel-client` reported as a blocking gate.

**Step 6: Commit**

```bash
git add scripts/bridge tests/bridge
git commit -m "test: add Codex bridge local preflight"
```

### Task 3: Verify the local MCP contract

**Files:**

- Create: `docs/runbooks/local-mcp-contract-proof.md`
- Create: `evidence/examples/mcp-tools.redacted.example.json`
- Modify: `docs/specs/chatgpt-codex-bridge/tasks.md`

**Step 1: Start with tool discovery only**

Run the official MCP Inspector against the resolved explicit binary:

```bash
npx @modelcontextprotocol/inspector "/absolute/verified/codex" mcp-server
```

Expected: the inspector initializes and `tools/list` shows `codex` and `codex-reply`.

**Step 2: Verify schemas**

Confirm:

- `codex.prompt` is required;
- `codex.cwd`, `sandbox`, and `approval-policy` match current official schema;
- `codex-reply.prompt` is schema-required;
- `codex-reply.threadId` is present and documented as required for new calls, while remaining schema-optional for backward compatibility;
- `conversationId` remains a deprecated compatibility alias and is not used in new automation;
- a call missing both thread identity fields fails semantically without continuing a thread.

**Step 3: Record only redacted contract evidence**

Store tool names, safe field names, Codex version, and a schema hash. Do not store a live thread ID or configuration secrets.

**Step 4: Negative tests**

Verify missing required fields produce a clear error and do not start a Codex turn.

**Step 5: Commit**

```bash
git add docs/runbooks/local-mcp-contract-proof.md evidence/examples/mcp-tools.redacted.example.json docs/specs/chatgpt-codex-bridge/tasks.md
git commit -m "docs: add local Codex MCP contract proof"
```

### Task 4: Provision the isolated proof boundary

**Files:**

- Create: `docs/runbooks/isolation-boundary.md`
- Create: `scripts/bridge/check-sandbox-repo.zsh`
- Create: `tests/bridge/test-check-sandbox-repo.zsh`

**Step 1: Write failing boundary tests**

Test rejection of:

- a path outside the configured sandbox root;
- a symlinked repository root;
- a repository on `main` when a task branch is required;
- a dirty baseline;
- obvious `.env`, private-key, or credential files inside the test repo.

Tests must use a temporary directory from `mktemp -d` and delete only that exact validated directory in a trap.

**Step 2: Run tests and confirm failure**

```bash
zsh tests/bridge/test-check-sandbox-repo.zsh
```

Expected: FAIL because the checker does not exist.

**Step 3: Implement minimal checks**

Resolve absolute paths, reject symlinks/reparse equivalents, require the approved root, require a Git repository, and scan only the repository for forbidden test fixtures.

**Step 4: Document manual OS isolation**

The runbook must require a sterile non-admin account or disposable VM before the first Codex tool call. Account creation and permission changes remain manual, explicitly authorized operations. The checker is an operator-side admission gate, not a security wrapper around raw MCP; a later enforcement adapter is responsible for rejecting unsafe remote arguments server-side.

**Step 5: Run tests and commit**

```bash
zsh tests/bridge/test-check-sandbox-repo.zsh
git add docs/runbooks/isolation-boundary.md scripts/bridge/check-sandbox-repo.zsh tests/bridge/test-check-sandbox-repo.zsh
git commit -m "test: add isolated sandbox boundary checks"
```

### Task 5: Install and validate official tunnel-client

**Files:**

- Create: `docs/runbooks/secure-mcp-tunnel.md`
- Create: `scripts/bridge/verify-tunnel-client.zsh`
- Create: `tests/bridge/test-verify-tunnel-client.zsh`

**Step 1: Require authorization**

Stop and obtain explicit user approval for the exact installation location and release before downloading or installing anything.

**Step 2: Select the latest stable official release**

Use `openai/tunnel-client`; do not hard-code a stale download URL. Inspect release metadata and choose the current stable Darwin arm64 asset.

**Step 3: Verify integrity before installation**

Download the release archive and `SHA256SUMS.txt` to a dedicated `mktemp -d` directory, verify the checksum, inspect archive paths, and then install to the user-approved location. Abort on any mismatch.

**Step 4: Test the verifier**

```bash
zsh tests/bridge/test-verify-tunnel-client.zsh
```

Expected: PASS only when the binary is official, executable, and reports a version.

**Step 5: Initialize without exposing secrets**

Before `tunnel-client init`, validate that `CONTROL_PLANE_API_KEY` is non-empty without printing it. Use an explicit MCP command pointing to the verified Codex binary. Never commit the generated profile.

**Step 6: Run doctor**

```bash
tunnel-client doctor --profile example-profile --explain
```

Expected: healthy/ready or a precise fail-closed diagnostic. Redact identifiers from stored evidence.

**Step 7: Commit only scripts and runbook**

```bash
git add docs/runbooks/secure-mcp-tunnel.md scripts/bridge/verify-tunnel-client.zsh tests/bridge/test-verify-tunnel-client.zsh
git commit -m "docs: add secure tunnel verification runbook"
```

### Task 6: Run read-only end-to-end proof

**Files:**

- Create: `docs/runbooks/chatgpt-read-only-proof.md`
- Create: `scripts/bridge/capture-repo-state.zsh`
- Create: `tests/bridge/test-capture-repo-state.zsh`
- Create: `evidence/examples/read-only-proof.redacted.example.md`

**Step 1: Write and test deterministic state capture**

Capture tracked/untracked Git status plus hashes for files inside the sandbox repository. Do not traverse outside the approved root.

```bash
zsh tests/bridge/test-capture-repo-state.zsh
```

Expected: PASS for unchanged fixtures and FAIL when a fixture mutates.

**Step 2: Start tunnel-client**

Run it interactively or under an operator-visible service for the bounded proof. Verify health/readiness before opening ChatGPT.

**Step 3: Create and scan a draft ChatGPT app before starting the test conversation**

In ChatGPT app settings, create a draft app using the verified tunnel, scan tools, and confirm that at least `codex` and `codex-reply` are present. Record and review any additional tools. Do not publish the app.

Then open a new ChatGPT web conversation and select the already-created draft app from the tools menu. Tool scanning does not happen inside the conversation.

**Step 4: Call Codex read-only**

Use the absolute sandbox `cwd`, `sandbox=read-only`, and `approval-policy=on-request`. Ask only for a project summary.

Expected:

- accurate summary;
- returned `structuredContent.threadId`;
- no repository diff or hash change.

**Step 5: Record redacted evidence and commit harness docs**

```bash
git add docs/runbooks/chatgpt-read-only-proof.md scripts/bridge/capture-repo-state.zsh tests/bridge/test-capture-repo-state.zsh evidence/examples/read-only-proof.redacted.example.md
git commit -m "test: add read-only bridge proof harness"
```

### Task 7: Prove approval, bounded write, and thread continuity

**Files:**

- Create: `docs/runbooks/chatgpt-write-and-reply-proof.md`
- Create: `evidence/examples/write-reply-proof.redacted.example.md`
- Modify: `docs/specs/chatgpt-codex-bridge/tasks.md`

**Step 1: Reconfirm clean baseline**

Run the sandbox checker and state capture. Expected: clean branch and no forbidden files.

**Step 2: Request one bounded write**

Ask the initial Codex thread to create one named harmless test file inside the repository using `workspace-write` and `on-request`.

Expected: ChatGPT surfaces the approval request. If it does not, stop and mark `FAIL_CLOSED`; never retry with `never` or `danger-full-access`.

**Step 3: Verify the exact change**

Expected: Git lists only the named file, its contents match, and no out-of-root mutation or network access occurred.

**Step 4: Continue the same thread**

Call `codex-reply` with the exact ephemeral `threadId` returned by the first call and ask for a deterministic correction to the same file.

Expected: the reply uses prior context and only the expected file changes.

**Step 5: Prove revocation**

Stop `tunnel-client`, confirm readiness is false, and verify a subsequent remote call fails closed.

**Step 6: Commit only redacted templates and runbook**

```bash
git add docs/runbooks/chatgpt-write-and-reply-proof.md evidence/examples/write-reply-proof.redacted.example.md docs/specs/chatgpt-codex-bridge/tasks.md
git commit -m "docs: add bounded write and thread continuity proof"
```

### Task 8: Repeatability, review, and promotion decision

**Files:**

- Create: `docs/reports/chatgpt-codex-bridge-pilot.md`
- Modify: `docs/specs/chatgpt-codex-bridge/tasks.md`
- Modify: `docs/specs/chatgpt-codex-bridge/requirements.md`
- Modify: `docs/adr/0001-use-official-codex-mcp-path-for-first-proof.md`

**Step 1: Run two additional fresh proofs**

Each run must use a fresh ChatGPT conversation and fresh Codex thread. Record booleans and redacted evidence only.

**Step 2: Exercise failure recovery**

Test:

- tunnel stopped before call;
- Codex process unavailable;
- stale ChatGPT tool snapshot;
- invalid thread ID;
- approval decline;
- macOS `workspace-write` failure.

Expected: each condition fails closed with a documented recovery path.

**Step 3: Independent verification**

Use a test verifier to reproduce the proof result and a reviewer to audit scope, secret handling, evidence separation, and non-goals.

**Step 4: Score out of 100**

Use:

- requirements coverage: 25;
- correctness and repeatability: 25;
- security containment: 25;
- observability/recovery: 15;
- maintainability: 10.

Do not promote below 95/100. If the raw MCP interface cannot be made safe for a real repository, write a new spec for a narrow enforcement adapter rather than weakening the pilot requirements.

**Step 5: Final verification and commit**

```bash
git diff --check
rg -n 'danger-full-access|approval-policy=never' docs scripts tests evidence
git status --short
git add docs/reports/chatgpt-codex-bridge-pilot.md docs/specs/chatgpt-codex-bridge docs/adr/0001-use-official-codex-mcp-path-for-first-proof.md
git commit -m "docs: record ChatGPT Codex bridge pilot decision"
```

Expected: treat the `rg` output as a manual review queue, not an automated assertion. Inspect every match and confirm it is an explicit prohibition or negative-test context. All automated tests pass, and the report states `PASS`, `FAIL_CLOSED`, or `UNVERIFIED` per evidence layer.

## Execution handoff

T-108, T-109, T-102, and T-103 are complete. Do not install `tunnel-client`, create tunnel resources, invoke local Codex, or perform write actions until their remaining approval and isolation gates are satisfied. T-106 and T-107 remain distinct: CanEngine classification is still unknown, and the actual Codex tools have not been scanned through ChatGPT. Continue one gate at a time; if the direct action path fails, write the bounded CanEngine-to-Codex fallback decision before implementation.
