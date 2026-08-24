# ADR 0016: Add a bounded global Codex catalog

## Context

The bridge can start and continue durable Codex work, but ChatGPT currently sees
only a job capability and terminal prose. It lacks a device-level view of known
repositories, Codex projects, historical threads, and current activity. That
makes thread selection and recovery depend on details retained in one ChatGPT
conversation.

## Decision

Expose a read-only catalog backed by Codex App Server thread list/read/turn APIs and a bounded
workspace-root repository probe. Keep raw identifiers internal and return signed
capabilities. Add paginated thread-history reading, structured job progress, and a
stable task/report contract. Keep discovery limited to the configured workspace
and its direct child directories.

## Consequences

- ChatGPT can inspect known work before starting or continuing a task.
- Historical conversation reading uses official Codex history rather than job
  prose or filesystem rollout parsing.
- No recursive device scan is added.
- Catalog calls briefly start App Server and therefore use strict deadlines and
  page limits.
- Output schemas grow additively; older durable job records remain readable.
