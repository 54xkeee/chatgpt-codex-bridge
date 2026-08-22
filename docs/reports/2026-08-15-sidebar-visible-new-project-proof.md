# Sidebar-Visible New Project Proof

Date: 2026-08-15
Scope: T-409
Result: PASS

## Contract proven

- `codex-start(prompt, projectName?)` creates one collision-safe direct child
  of `/Users/example-user/codex-workspace`; ChatGPT cannot provide `cwd`.
- The durable worker uses Codex App Server `thread/start` and `turn/start`, not
  `codex exec`, with `danger-full-access` and `approvalPolicy=never` fixed
  locally.
- The first turn carries the installed `workspace-new-project` Skill as an
  explicit Skill input and invokes `$workspace-new-project --here` in text.
- A nominally completed turn is rejected unless all required scaffold markers
  exist.
- `codex-reply-async` resolves the original private project root, resumes the
  exact thread, and does not attach or invoke the new-project Skill again.

## Fresh automated evidence

- Python compilation passed for the reviewed and packaged Guard copies.
- The two Guard copies were byte-identical.
- All 29 Guard contract tests passed, including App Server lifecycle, exact
  root, explicit Skill input, missing-Skill/scaffold failure, non-sidebar
  source failure, wrong-root failure, and legacy continuation.
- Every bridge boundary/preflight/service/Tunnel test passed.
- Portable macOS install/uninstall and plugin-package checks passed for plugin
  version `0.3.0`.

## Fresh live evidence

- The launchd service restarted with the staged reviewed Guard and reported
  `status=ready`, HTTP health/readiness 200, and Control Plane connected.
- `tunnel-client doctor` passed without retaining profile or Tunnel identifiers
  in this report.
- A real `codex-start` call created
  `/Users/example-user/codex-workspace/ChatGPT-新项目链路验证`.
- The project contained `AGENTS.md`, `README.md`, `.gitignore`,
  `.project-memory/`, `docs/specs/`, `docs/adr/`, and `src/`; it did not contain
  a same-name nested project directory.
- The first job completed with a persistent thread. A real
  `codex-reply-async` job completed on the same thread and returned the exact
  read-only marker `SAME_PROJECT_ROOT_OK`.
- Codex App task listing returned that task with exact title and exact project
  root `cwd`. Reading it through the App returned two turns and retained the
  explicit Skill/`--here` input plus the continuation marker.
- A separate non-mutating App Server handoff task for the existing GACE project
  appears in the Codex task list as `GACE 项目交接` with exact
  `/Users/example-user/codex-workspace/gace` `cwd`.

## Evidence boundary

The supported App Server `thread/start` schema has no `projectId` or saved
project registration field, and no project-registry mutation method was found
in the generated protocol schema. The verified contract is therefore an
actual sidebar task rooted at and titled for each project directory. It does
not claim that the folder is separately registered in Codex's optional Saved
Projects registry. No Codex session, index, SQLite, or historical task metadata
was edited.

## Score

T-409 tranche: 97/100.

- Requirements coverage: 25/25
- Architecture and failure handling: 19/20
- Correctness and tests: 20/20
- User workflow: 18/20
- Maintainability and portability: 15/15

The remaining three points are the unsupported Saved Projects registry and the
still-required fresh ChatGPT web invocation after the app refresh. Neither
invalidates local task visibility, Skill execution, or same-thread continuity.
