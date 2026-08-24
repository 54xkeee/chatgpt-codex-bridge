# Global Codex Catalog Design

## Catalog boundary

The configured workspace is the catalog root. Known project roots are the root
itself plus existing direct child directories. Git repositories are the known
roots containing a `.git` entry. Codex threads are requested from App Server
with the exact known-root list as the `cwd` filter.

This provides a useful device catalog without recursive filesystem traversal.

## Public tools

- `codex-overview()` returns counts, active jobs, recent repositories, recent threads, runtime identity, and degraded components.
- `codex-project-list(limit?, cursor?)` returns cwd-derived Codex project entries.
- `codex-repository-list(limit?, cursor?)` returns bounded Git metadata.
- `codex-thread-list(projectId?, query?, limit?, cursor?)` returns thread metadata and signed thread capabilities.
- `codex-thread-read(threadId, limit?, cursor?)` returns metadata plus one page from `thread/turns/list`.
- `codex-job-list(status?, limit?, cursor?)` returns durable job summaries.

All list page sizes default to 20 and are capped at 100. Public cursors are
signed capabilities with a separate audience per tool.

## App Server adapter

Each catalog call creates a short-lived App Server client with a bounded
deadline, initializes it, performs only the required read calls, and closes it.
Project entries are derived from canonical thread cwd values and bounded known
roots; the implementation does not depend on experimental `project/*` methods.
`thread/turns/list` with a summary item view is the normal history path, with
`thread/read(includeTurns=true)` as the bounded compatibility path.

Thread turns and items are reduced to a stable public shape. User and agent messages keep
bounded text. Commands keep command, cwd, status, exit code, duration, and a
bounded output tail. File-change entries keep paths and change kinds. Tool calls
keep server/tool/status and omit large argument/result bodies. Reasoning content
is omitted.

## Progress and reports

Internal App Server notifications update:

- `phase`: queued, starting, discovering, executing, checking, finalizing, terminal;
- `activity`: a concise user-visible description;
- `lastEventAt`: Unix timestamp;
- `failureStage`: empty unless a stage fails;
- `nextAction`: wait, review, continue, repair, or none.

Completed item events also accumulate bounded command and file-change summaries.
The final public `report` is derived from those records plus the final Codex
message. The final message remains data and never changes controller policy.

## Windows lifecycle

PowerShell path validation uses `GetFullPath` plus rooted-path checks compatible
with Windows PowerShell 5.1. The Guard main loop treats client stdin EOF as a
normal shutdown, closes downstream stdin, and uses a bounded child wait before
tree cleanup. Atomic JSON replacement retains the Windows contention retry and
has a dedicated regression test.

## Runtime identity

The manifest version and Guard SHA-256 are staged in generated configuration.
`doctor` reports source/runtime match as a boolean and prints hashes only when
explicit JSON output is requested.

## Rollback

Remove the new public tool descriptors and catalog handler, revert the output
schema additions, and reinstall the previous plugin version. Existing job files
remain readable because all added state fields are optional during reads.
