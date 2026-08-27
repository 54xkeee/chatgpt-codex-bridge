# Durable Job Cancellation Requirements

## Scope

The bridge MUST expose `codex-job-cancel(jobId)` for durable jobs created by the
same installation. Cancellation reuses the existing `interrupted` terminal
state and MUST cancel the tracked execution rather than only editing metadata.

## Requirements

### JC-001 — Signed job boundary

Given a signed job capability from this bridge, cancellation MUST resolve only
that job's durable directory and recorded worker identity. Unknown, malformed,
or installation-foreign capabilities MUST fail closed. Process-name-wide
termination is out of scope.

### JC-002 — Atomic queued cancellation

Given a queued job, when cancellation and worker startup race, exactly one of
them MUST cross the shared lifecycle lock first. A cancellation marker written
first MUST prevent the worker from starting Codex; a worker transition written
first makes the request a running cancellation.

### JC-003 — Running cancellation

Given a running job, cancellation MUST verify the bridge-owned worker command,
job directory, execution token, and process-group identity before terminating
it. On Windows the whole worker process tree MUST stop. On POSIX the owned
process group MUST stop. The terminal state MUST be `interrupted` only after the
worker is gone.

### JC-004 — Lifecycle consistency

The worker MUST serialize its initial and final state transitions with
cancellation. After `interrupted` is persisted, that worker MUST perform no
further durable writes. A completion that wins the lifecycle lock first remains
terminal and cancellation is a no-op.

### JC-005 — Idempotency and observability

Repeated cancellation and cancellation of `completed`, `failed`, or
`interrupted` jobs MUST return the current terminal state without error.
`codex-job-open`, `codex-job-list`, and `codex-overview` MUST observe the same
terminal state.

### JC-006 — Restart and stale-worker safety

Cancellation MAY terminate a worker after bridge restart only when its durable
PID identity still matches the exact Guard path, job directory, execution
token, and process group. If identity cannot be proven, cancellation MUST leave
the process untouched and reconcile a dead worker to `interrupted`.

## Acceptance

Tests cover queued and running cancellation, process-tree termination, released
thread reuse, idempotency, completion races, job isolation, terminal no-ops,
catalog visibility, stale identity rejection, and Windows tree handling.
