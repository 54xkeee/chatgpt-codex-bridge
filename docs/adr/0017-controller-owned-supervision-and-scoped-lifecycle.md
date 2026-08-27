# ADR 0017: Controller-owned supervision with scoped Codex lifecycle control

## Status

Accepted

## Context

The bridge began as a transport and safety boundary but its durable-job tool descriptions increasingly dictated the controller loop. At the same time, the user could not interrupt or steer one running Codex turn, inspect the exact prompt/reply exchange from ChatGPT, or know when a Codex Desktop thread writer had been released.

Codex App Server already owns the canonical turn lifecycle. The bridge also already owns durable job identity, signed capability scope, and verified worker-process ownership.

## Decision

ChatGPT owns planning, review, and supervision policy. The bridge owns transport, durable execution, observation, and scoped lifecycle primitives.

The bridge will expose bounded wait/status, exact public transcript, same-turn steer, per-job cancel, and writer/handoff state. Running controls target the exact App Server thread/turn. Process-tree termination is only a bounded fallback after canonical interruption and only after existing bridge ownership checks pass.

The bridge will not add autonomous scheduling, DAG execution, task decomposition, retry planning, or concurrent writers to a Codex thread.

## Consequences

- ChatGPT can supervise without being forced into a tight polling loop.
- Users can audit what ChatGPT actually sent and what Codex publicly returned.
- A user can deliberately hand a thread back to Codex Desktop after the bridge releases its writer.
- Cancellation is scoped and idempotent instead of relying on service-wide restart/stop.
- The durable state format gains optional backwards-compatible fields and a small per-job control record.
- GUI and bridge are never treated as simultaneous writers to one thread.