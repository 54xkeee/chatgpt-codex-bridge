# ChatGPT supervisory wait loop implementation plan

Date: 2026-08-15
Spec: `chatgpt-codex-bridge`
Task: `T-410`

## Goal

Make ChatGPT consume each durable Codex result in the active model turn and
continue the same Codex thread until the user's full project acceptance target
is complete, while preserving durable recovery when the turn is interrupted.

## Evidence and choice

- Local: durable jobs, same-thread App Server continuation, status polling, and
  one-click Apps return already exist and pass tests.
- Live: background component follow-up did not create a ChatGPT turn; an
  explicit click did.
- Protocol: MCP Tasks provide the ideal durable polling primitive but require
  explicit client negotiation that the current compatibility path has not
  shown.
- Selected: adapt JobStore with a fixed bounded model-visible join.

## Work order

1. Add failing discovery and behavior tests for `codex-wait`.
2. Implement the fixed bounded JobStore wait and model-facing result contract.
3. Tighten start/reply/controller instructions so milestone completion resumes
   the supervisor rather than ending the overall project.
4. Synchronize the packaged Guard and run all bridge/package tests.
5. Restart the installed Tunnel service and verify health plus tool discovery.
6. Recover GACE M0, continue its exact thread to M1, and run a fresh web
   two-tranche supervisory-loop proof.
7. Record evidence, update T-410, commit, and push the milestone.

## Rollback

Revert the T-410 commit and restart the LaunchAgent. Existing job files,
projects, Codex tasks, and the one-click Apps return remain intact throughout.
