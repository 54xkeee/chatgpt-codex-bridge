# ADR 0018: Recover Windows Tunnel exits inside the owned command loop

## Status

Accepted

## Context

The Windows Startup entry launches one generated `run-tunnel.cmd` process. That
script previously executed `tunnel-client run` once and then exited. A transient
control-plane or local proxy failure could therefore leave a stale PID and health
URL file while the bridge stopped serving requests. The Startup entry runs only
at user logon, so it does not repair an exit during the session.

## Decision

Keep the existing single Windows process tree and generate a bounded retry loop
around the `tunnel-client run` command. After an exit, the command waits five
seconds and invokes the same command again. The controller continues recording
the loop's parent PID, and its existing ownership check plus `taskkill /T /F`
path remains the only stop mechanism.

## Consequences

- A transient Tunnel exit is recovered without a second supervisor process or a
  new dependency.
- The loop preserves the existing log paths and health-file behavior.
- Explicit stop, restart, and uninstall terminate the loop and its descendants.
- Persistent profile or executable failures retry every five seconds and remain
  visible in the existing logs, so `doctor` and `status` still report readiness
  separately.
