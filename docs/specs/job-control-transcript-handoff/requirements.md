# Job control, transcript, and handoff requirements

## Scope

The bridge remains a transport and durable-execution boundary. ChatGPT owns task planning and supervision; the bridge MUST NOT become a scheduler, DAG engine, autonomous retry planner, or second orchestrator.

## Requirements

### R1 — Bounded wait without forced foreground polling

Given a durable job, `codex-wait` MUST support a caller-selected bounded wait interval up to the bridge-safe request limit and MUST return the current durable state when that interval expires. Tool semantics MUST NOT require the controller to poll continuously; the controller MAY inspect status, steer, cancel, answer the user, or return later while the durable job remains recoverable.

Acceptance criteria:
- the default wait is longer than the previous 45-second default without exceeding the request-safe maximum;
- `timeoutSeconds` is optional and validated;
- an active job returns its current state after the bounded interval.

### R2 — Scoped, idempotent cancellation

Given a signed `jobId`, `codex-job-cancel` MUST affect only that bridge-owned job.

- A queued job MUST become `interrupted` and MUST NOT begin Codex work.
- A running job MUST first request canonical App Server `turn/interrupt` for the exact active thread and turn.
- If the canonical interrupt does not reach a terminal state within a short bounded grace period, the bridge MAY terminate only the verified bridge-owned worker process tree for that job.
- Repeating cancellation on a terminal job MUST be a no-op that returns the terminal state.
- Cancellation MUST NOT stop the Tunnel/bridge service or kill processes by fuzzy process name.

### R3 — In-flight steering

Given a running job with an active turn, `codex-job-steer(jobId, prompt)` MUST send the additional instruction through canonical App Server `turn/steer` for that exact thread/turn. Queued or terminal jobs MUST reject steering clearly. Steering MUST remain part of the same Codex thread and turn rather than creating a second writer or hidden follow-up thread.

### R4 — Auditable conversation surface

Every durable job MUST expose a bounded public transcript containing:
- the exact controller prompt submitted by ChatGPT before bridge-only wrapper text;
- subsequent controller steer instructions and cancel reasons;
- Codex agent/plan messages observed for the root turn, including the final answer when present.

Private reasoning items MUST NOT be exposed. Existing structured command/check/file-change reporting MUST remain available.

### R5 — Explicit writer ownership and handoff

Durable job state MUST expose whether the bridge currently owns the active Codex writer and whether the thread is available for Codex Desktop/GUI takeover.

- While the worker App Server owns an active thread, the state MUST report bridge ownership.
- After terminal completion, interruption, cancellation fallback, or worker shutdown, the bridge MUST close its App Server and report the thread as available when a thread exists.
- The bridge MUST NOT attempt concurrent bridge + GUI writes to the same Codex thread.

### R6 — Immediate status inspection

`codex-job-status` MUST be model-visible and return immediately without joining the job. It MUST include the durable lifecycle state, transcript, structured report, signed thread capability when available, and writer/handoff state. It MUST NOT expose raw capability internals, private reasoning, secrets, or unscoped process identifiers.

### R7 — Persistence and security

Control commands and job state MUST remain installation/workspace/policy scoped by the existing signed capability boundary. New durable control records MUST be included in safe cleanup/purge behavior. Existing fail-closed ownership checks MUST remain intact.

## Non-goals

- concurrent multi-writer access to one Codex thread;
- arbitrary OS process termination;
- workflow scheduling or autonomous orchestration;
- exposing chain-of-thought/private reasoning;
- unsolicited push delivery while ChatGPT is inactive.

## Failure modes

- unsupported/invalid `jobId` → invalid-argument response;
- steer before an active turn → clear rejection;
- canonical interrupt failure → bounded verified worker fallback;
- stale worker → reconcile to `interrupted` and release handoff state;
- malformed control state → fail closed.

## Rollback

The feature is additive to the MCP surface. Rolling back removes the new tools and fields; existing durable job records without transcript/control fields MUST continue to be readable with safe defaults.