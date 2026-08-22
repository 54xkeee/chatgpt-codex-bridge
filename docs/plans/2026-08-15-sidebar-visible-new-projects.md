# Sidebar-Visible New Projects Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make every ChatGPT-led new project start in its own Codex-visible directory and invoke the existing `workspace-new-project` Skill before implementation.

**Architecture:** Adapt the existing durable `codex-start` path rather than adding another service or public path selector. Allocate the child directory locally, run a one-job Codex App Server client, create an interactive task rooted at that directory, pass the real Skill as an explicit `turn/start` input, enforce the scaffold on completion, and reuse the root and thread for async replies.

**Tech Stack:** Python 3 standard library, MCP JSON-RPC, Codex App Server JSONL, unittest, launchd-managed Secure MCP Tunnel.

---

### Task 1: Lock the project-root contract in tests

**Files:**
- Modify: `tests/bridge/test-codex-mcp-guard.py`

1. Extend the fake Codex executable to implement the App Server JSONL
   lifecycle, record requests, and create the required scaffold only when it
   receives the explicit Skill input.
2. Add a failing test asserting `codex-start` accepts an optional display-only
   `projectName`, creates one child root, uses that root in `thread/start` and
   `turn/start`, and includes the explicit `workspace-new-project` Skill plus
   `$workspace-new-project --here` before the user task.
3. Add failing cases for missing, Unicode, duplicate, and traversal-shaped
   names; every resolved root must remain a real direct child of the configured
   container.
4. Run the focused tests and confirm they fail against the current bridge.

### Task 2: Implement project allocation and bootstrap enforcement

**Files:**
- Modify: `scripts/bridge/codex-mcp-guard.py`
- Modify: `plugins/chatgpt-codex-bridge/bridge/codex-mcp-guard.py`

1. Add a display-name normalizer and atomic unique child-directory allocator.
2. Change `codex-start` to accept `prompt` with optional `projectName`, allocate
   the child root, and store that root only in private job request state.
3. Resolve the installed `workspace-new-project/SKILL.md`, pass it as an App
   Server Skill input, and prepend text that invokes
   `$workspace-new-project --here` while forbidding a nested root.
4. Start new Codex work with App Server `thread/start` and `turn/start`, then
   validate the documented scaffold before marking the job complete.
5. Apply the identical implementation to the portable plugin mirror and run
   the focused tests until green.

### Task 3: Preserve project root on continuation

**Files:**
- Modify: `tests/bridge/test-codex-mcp-guard.py`
- Modify: `scripts/bridge/codex-mcp-guard.py`
- Modify: `plugins/chatgpt-codex-bridge/bridge/codex-mcp-guard.py`

1. Add a failing test that starts a project, captures its thread ID, sends
   `codex-reply-async`, and proves no second directory is created.
2. Resolve the latest matching private project root from durable completed job
   state and validate it remains under the configured container.
3. Use App Server `thread/resume` plus `turn/start` at the same root; retain the
   existing workspace-container fallback for legacy threads.
4. Run the focused and complete Guard suites.

### Task 4: Update the operator and plugin contract

**Files:**
- Modify: `docs/runbooks/codex-mcp-guard.md`
- Modify: `README.md`
- Modify: `plugins/chatgpt-codex-bridge/skills/chatgpt-codex-controller/SKILL.md`

1. Document that `codex-start` means new project, `projectName` is not a path,
   and the first Codex action is the existing Skill.
2. Document partial-directory recovery and same-root continuation.
3. Run plugin validation, portable install tests, secret scans, Python compile,
   and `git diff --check`.

### Task 5: Install and prove the behavior

1. Restart the existing launchd Tunnel service so it stages the new Guard.
2. Verify launchd, Tunnel health/readiness, a recent Control Plane poll, and
   `tunnel-client doctor` independently.
3. Create a new user-owned Codex handoff task with
   `/Users/example-user/codex-workspace/gace` as its `cwd` and a read-only first prompt;
   confirm the task is visible under the GACE project without changing prior
   task history.
4. Mark T-409 complete only after fresh tests and the live task-root proof.
5. Record project-memory evidence, commit the milestone, and push the branch.
