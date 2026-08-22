# Canonical Codex Sidebar Project Proof

Date: 2026-08-21
Scope: T-413

## Result

PASS. A fresh local `codex-start` call created a unique project directory,
registered it with the Codex desktop app, ran the explicit
`workspace-new-project --here` bootstrap, and returned the expected terminal
marker from one durable Codex task.

After the desktop registry's bounded reconciliation delay:

- `list_projects` returned the exact created root as a saved local project;
- `list_threads` returned the completed task with the same desktop project ID;
- the task `cwd` exactly matched the saved project root;
- the required spec/ADR/project-memory scaffold existed;
- no second task or parallel project directory was used for that successful
  job.

Identifiers, Tunnel identity, credentials, and raw endpoints are intentionally
omitted.

## Negative proof and correction

The first live attempt failed closed after allocating a task ID. The worker had
queried `thread/list` immediately after `thread/start`; Codex does not make a
new thread listable until its first turn has been written. The implementation
was corrected to verify project and thread listing only after the root turn is
terminal. The failed partial directory was retained for diagnosis rather than
silently deleted.

## Verification

- Guard contract suite: 34 tests passed.
- Bridge shell suites: passed.
- Portable macOS installer and plugin-package suites: passed.
- Reviewed and packaged Guard copies: byte-identical.
- Live job: completed with the exact expected marker.
- Desktop project/task/root reconciliation: passed.

## Boundary

This proof establishes project-folder visibility and task grouping on the
tested macOS Codex desktop build. It does not change the separate ChatGPT
inactive-conversation boundary: an inactive consumer ChatGPT conversation
still needs its existing Apps recovery action or an operator-side wakeup.
