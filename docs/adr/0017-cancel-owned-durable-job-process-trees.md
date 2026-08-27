# ADR 0017: Cancel owned durable job process trees

## Status

Accepted

## Decision

Use the durable job capability and a per-launch execution token as the process
ownership boundary. Serialize queued startup, cancellation intent, and terminal
commit through the existing job-store lock. Terminate only a verified worker's
process group/tree, then persist the existing `interrupted` terminal state.

## Consequences

- Cancellation releases the App Server and its thread/session lock promptly.
- Repeated cancellation naturally returns the existing terminal state.
- Restarted Guard processes can cancel a surviving worker only while its full
  durable identity remains verifiable; PID-only cancellation is rejected.
- No new runtime dependency or expanded job status is introduced.
