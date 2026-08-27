# Durable Job Cancellation Design

`JobStore.cancel` decodes the signed `jobId`, then uses the existing
`admission.lock` as a lifecycle lock. Active cancellation validates the durable
request and recorded worker identity, then writes a private `cancel.json`
intent before termination. Workers take the same lock before changing `queued`
to `running` and before their final write. This gives cancellation and
completion a single ordering point.

Each launch has a random execution token stored in `request.json` and
`worker.json` and passed on the worker command line. Termination reuses the
existing owned-worker checks and adds exact token matching. Windows uses
`taskkill /PID <owned-pid> /T /F`; POSIX signals only the verified process
group. The state changes to `interrupted` after the process tree exits.

The MCP handler returns the normal asynchronous job shape. Terminal jobs are
read-only no-ops. A live worker whose identity fails verification produces an
MCP error without signalling it; a dead active worker is reconciled safely.
