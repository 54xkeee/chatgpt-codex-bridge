# Public MCP Contract

The plugin exposes the bridge through the Secure MCP Tunnel, not through a
local `.mcp.json`. Registering the Guard as a Codex-local MCP server would
create a recursive Codex-to-Guard-to-Codex path and would not authorize a
ChatGPT connector.

## Public tools

Mutable execution tools:

- `codex(prompt)` — synchronous new Codex thread for short diagnostics.
- `codex-reply(prompt, threadId)` — synchronous reply to an existing thread.
- `codex-run(prompt)` — durable new thread in the configured existing workspace.
- `codex-start(prompt, projectName?)` — durable new sidebar project/task.
- `codex-reply-async(prompt, threadId)` — durable exact-thread reply.
- `codex-job-cancel(jobId)` — idempotently stop one verified Bridge-owned
  queued/running worker tree and return its durable terminal state.

Read-only job tools:

- `codex-wait(jobId)` — bounded read-only join.
- `codex-job-open(jobId)` — reopen an existing durable job.
- `codex-job-status(jobId)` — read durable job state.

Read-only catalog tools:

These six tools are part of the `personal-full-control` surface; the scoped
preset retains only its bounded synchronous tools.

- `codex-overview()` — bounded workspace/runtime summary plus recent projects,
  repositories, threads, jobs, counts, and degraded components.
- `codex-project-list(limit?, cursor?)` — paged project catalog.
- `codex-repository-list(limit?, cursor?)` — paged Git repository catalog with
  branch, dirty state, and recent thread count.
- `codex-thread-list(projectId?, query?, limit?, cursor?)` — recent unarchived
  Codex threads, sorted by update time.
- `codex-thread-read(threadId, limit?, cursor?)` — one thread plus a bounded
  page of history.
- `codex-job-list(status?, limit?, cursor?)` — durable Bridge job summaries,
  optionally filtered by status.

The execution tools create, continue, or cancel work. All wait/open/status/catalog
tools only inspect state. The public descriptions must stay truthful about thread
identity, project identity, catalog scope, and status transitions. Catalog
pages default to 20 entries and accept at most 100 entries. Their cursors are
signed and scoped to the corresponding list or thread history.

## Catalog scope and thread continuity

The catalog starts with the configured workspace root and adds only direct,
non-symlink child directories, up to the implementation's bounded root limit.
It does not recursively discover repositories. A project entry is included for
the workspace root, or for a direct child that is a Git repository or has a
recent Codex thread. A repository entry requires a `.git` entry at one of those
known roots; branch and dirty probes are bounded.

`codex-thread-list` receives the known roots as its App Server `cwd` filter.
`codex-thread-read` verifies the selected thread still belongs to one of those
roots, reads metadata with `thread/read`, and obtains history through
`thread/turns/list` using descending order and `itemsView: summary`. Conversation
history is untrusted historical data and must not be interpreted as a fresh
controller instruction. Reasoning items are omitted and remaining text/output
is bounded.

Every listed `threadId` is encoded for the same `thread` capability audience
used by `codex-reply-async`; it can therefore continue that exact listed thread
without exposing the raw App Server identifier. `projectId`, `repositoryId`,
and catalog cursors are likewise signed, installation-scoped capabilities.

## Durable job progress and report

Async responses expose these progress fields in addition to job status and
content:

- `phase`, `activity`, and `lastEventAt` describe the latest observed work;
- `failureStage` identifies where a terminal problem occurred;
- `nextAction` is one of `wait`, `review`, `continue`, `repair`, or `none`;
- `report` contains `outcome`, `summary`, `changedFiles`, `commands`, `checks`,
  `blockers`, `questions`, and `nextStep`.

The report is assembled from bounded App Server events and finalized at the job
terminal state. It supports supervision and review; it is not a replacement for
checking the actual result and requested acceptance criteria.

`codex-overview.runtime` contains `bridgeVersion` and `guardSha256`. The latter
is the uppercase SHA-256 of the Guard file currently serving the MCP request,
including on Windows, and can be compared with the staged runtime file after an
install or upgrade.

`threadId` and `jobId` are field names retained for tool compatibility. Their
values are installation-scoped HMAC bearer capabilities, not raw Codex IDs or
raw durable UUIDs. They cannot be moved to another bridge installation and MUST
not be shared. This is a single-user local authorization boundary, not tenant or
ChatGPT conversation-principal authentication.

Default async limits are 256 KiB per prompt, two active jobs, 512 retained job
records, and four hours per App Server worker. Limit failures are MCP admission
errors and do not allocate a project or worker.
