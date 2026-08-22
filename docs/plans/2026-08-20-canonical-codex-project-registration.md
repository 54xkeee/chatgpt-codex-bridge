# Canonical Codex Project Registration Plan

## Goal

Make the user-visible invariant exact: one ChatGPT-led new project creates one
filesystem directory, one saved Codex sidebar project, and one initial Codex
thread assigned to that project.

## Root cause

The previous implementation verified only `thread.cwd`. Codex therefore listed
the task but returned `projectId=null`, while `list_projects` omitted the new
directory. Exact `cwd` is not equivalent to canonical project registration.

## Implementation

1. Extend the fake App Server and write a failing contract test for desktop
   registration followed by `project/create -> thread/start(projectId) ->`
   first durable turn `-> project/list -> thread/list`.
2. Add project response validation and private `projectId` persistence to both
   Guard copies.
3. Preserve project/root/thread identity during `codex-reply-async`.
4. Fail closed when project APIs are missing, malformed, or return a mismatched
   root or thread assignment.
5. Run focused and full suites, deploy the staged Guard, restart the Tunnel,
   and perform a fresh desktop `list_projects`/`list_threads` proof.
6. Register the existing GACE root as a saved desktop project and create one
   dedicated current task beneath it. Keep the earlier bridge task as
   historical evidence instead of rewriting its immutable project identity.

## Rejected alternatives

- Codex UI automation: unnecessary and brittle now that the official protocol
  exposes project mutation.
- SQLite/session/index edits: unsupported, destructive, and capable of
  disagreeing with immutable thread metadata.
- Keep exact-`cwd` tasks unassigned: fails the user's sidebar grouping
  requirement and repeats the original defect.

## Verification and rollback

- Automated contract tests cover success, mismatch, missing API, idempotency,
  and continuation.
- Live proof requires matching project path, `projectId`, thread `cwd`, and
  visible sidebar grouping.
- Code rollback is a Git revert plus Tunnel restart. Created project roots and
  historical threads are retained; no automatic deletion occurs.
