# Job control, transcript, and handoff design

## Boundary

ChatGPT is the controller. The bridge provides durable execution primitives and truthful observation; it does not decide the user's task graph. A durable worker owns one App Server writer while its turn is active. Codex Desktop may inspect persisted history, but writable takeover is advertised only after that worker releases the App Server.

## Durable state additions

`status.json` gains backwards-compatible optional fields:

- `workspace` — internal durable task location; it is not projected through model-visible async job output;
- `projectName` — human-readable task/project label that may be projected publicly;
- `transcript[]` — bounded public audit entries (`controller` prompt/steer/cancel and `codex` agent/plan messages only);
- `writerActive` — whether this worker currently owns the App Server writer;
- `threadHandoff` — `pending`, `bridge-owned`, `available`, or `unavailable`;
- `internalTurnId` — worker-internal active turn linkage, never emitted publicly.

`request.json` stores both `userPrompt` and the bridge-wrapped `prompt`. The public transcript uses `userPrompt`, so bridge-only return contracts/bootstrap text are not misrepresented as user/controller intent.

A per-job `controls.json` contains bounded controller commands. It is inside the already capability-scoped job directory and is created/updated atomically. It is not a generic queue: accepted kinds are only `steer` and `cancel`.

During an active job, the controller writes only the control mailbox. The worker remains the single writer of running `status.json` and records the corresponding public transcript entry when it sends the control to App Server. This avoids controller/worker lost-update races.

## Control flow

### Steer

1. Guard validates the signed `jobId` and that the job is running with an active turn.
2. Guard atomically appends a `steer` command to `controls.json` without writing running status.
3. Worker polls control state while reading App Server events.
4. Worker sends `turn/steer` with the exact internal thread ID and `expectedTurnId`, records the public steer entry, and keeps the same durable job active.
5. No new thread or second writer is created.

### Cancel

1. Terminal job: return unchanged.
2. Queued job: if a worker process has already been allocated, first stop only that verified bridge-owned worker; then persist `interrupted`. The worker itself also refuses to start from a non-queued state.
3. Running job: append one `cancel` command to `controls.json`; the worker sends exact `turn/interrupt` for the active thread/turn and records the public cancel entry.
4. Guard waits a short canonical-interrupt grace interval. If the job does not become terminal, it invokes the existing verified worker ownership checks and terminates only that job's process tree with a short interactive fallback bound.
5. A stopped POSIX zombie worker is treated as non-executing and reaped when this bridge process owns it, avoiding false "still running" results.
6. State becomes `interrupted`, writer ownership is cleared, and handoff becomes available only when a signed thread exists and the bridge worker/App Server writer is no longer active.

This intentionally avoids repeated `turn/interrupt` calls: bridge-level cancellation is idempotent even if an upstream App Server does not tolerate repeated interruption cleanly. Service-wide `revoke-jobs` retains its separate, more conservative shutdown timing.

## Wait

`codex-wait` accepts optional `timeoutSeconds`. The default increases from 45 seconds to 52 seconds; the existing 55-second hard ceiling remains because the Secure MCP request itself is bounded. The tool returns current state after the interval. Continuous polling is a controller choice, not a transport invariant.

## Transcript

The worker records only public App Server items:
- `agentMessage` text;
- `plan` text;
- controller prompt/steer/cancel text.

`reasoning` items remain filtered. Command/file/tool activity stays in the existing structured report and in `codex-thread-read` history. Transcript entries are bounded and mark truncation when necessary. Internal control IDs are stripped from the public projection.

## Handoff

The bridge reports `threadHandoff=bridge-owned` while its worker App Server owns the thread writer. The worker closes the App Server in `finally`, then records `writerActive=false` and `threadHandoff=available` when a signed thread exists. Cancellation fallback makes the same state transition only after verified worker termination.

The design does not create a second App Server writer and does not claim that Codex Desktop can write the thread concurrently.

## Compatibility

Older job records have no transcript/handoff fields. Public projection supplies safe defaults, and existing records remain readable. Existing tool names and job capability format remain unchanged. The new controls are additive.