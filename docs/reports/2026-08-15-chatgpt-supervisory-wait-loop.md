# ChatGPT supervisory wait-loop proof

Date: 2026-08-15
Spec: `chatgpt-codex-bridge`
Tasks: `T-408`, `T-410`, `T-411`, `T-412`

## Scope

Prove that an active ChatGPT web response can supervise one durable local
Codex task instead of ending after background submission:

`ChatGPT -> codex-start/codex-reply-async -> codex-wait -> review -> same-thread reply`

This report intentionally omits connector, Tunnel, job, request, and Codex
thread identifiers. Those values remain in private runtime state.

## Local implementation evidence

- The personal Guard exposes model-visible, read-only `codex-wait(jobId)`.
- The public wait schema accepts only `jobId`; timeout, working directory,
  model, sandbox, and approval policy remain host-controlled.
- Each call waits for a fixed interval below one minute, returns immediately on
  terminal state, and never creates a second job.
- Non-terminal results require another wait call and forbid an early user
  answer. Terminal results require review and exact-thread continuation when
  the overall request remains incomplete.
- The Apps status component remains available when the active ChatGPT response
  or browser page is interrupted.

Fresh verification passed:

- 33 Guard contract cases;
- every bridge shell suite;
- portable macOS installer and plugin-package suites;
- source/package/staged Guard byte equality;
- Python compilation and `git diff --check`;
- live local MCP discovery through the staged Guard.

The staged discovery returned the expected seven tools and classified
`codex-wait` as read-only and model-visible.

## Runtime evidence

The login LaunchAgent was restarted against the staged Guard. Its service
control reported:

- process running;
- `healthz=200`;
- `readyz=200`;
- Control Plane connected.

## ChatGPT web evidence

The existing project conversation initially retained the old five-tool schema.
Refreshing the development connector caused the management page to discover
the updated seven-tool schema, including `codex-wait` and the strengthened
start/reply descriptions.

In that same existing ChatGPT conversation:

1. ChatGPT continued the original Codex thread rather than creating a new one.
2. The first continuation was only a read-only M1 audit and was correctly
   rejected as incomplete.
3. ChatGPT issued a same-thread M1 implementation continuation.
4. After connector refresh, ChatGPT called `codex-wait` for that exact durable
   job.
5. The tool returned `running`; ChatGPT kept the response active and called the
   same wait tool again. The returned update timestamp advanced while the job
   identity and Codex thread identity stayed unchanged.
6. The ChatGPT response was forcibly ended after an extended wait and
   40 seconds. The durable Codex job continued locally; a new message in the
   same ChatGPT conversation resumed `codex-wait` without creating or replying
   to another Codex job.
7. The first M1 terminal result exposed an App Server event-scoping defect: a
   delegated provider reviewer completed before the root turn, and the Guard
   returned the child report. ChatGPT correctly rejected that partial evidence
   and did not start M2.
8. After deploying the ADR-0009 root `threadId + turnId` filter, ChatGPT issued
   an exact-thread correction, waited on its durable job, and received the
   comprehensive root report: M1 PASS, 136 tests, clean worktree, and local
   corrective commit.
9. In the same web response, ChatGPT reviewed that result and issued M2 through
   `codex-reply-async` on the exact same Codex thread. The new M2 durable job
   entered `running` state.
10. The M2 status card initially failed because the conversation-mounted iframe
    received its result globals after script startup and because template URI
    revisions are immutable per conversation snapshot. The v3 widget now accepts
    `toolOutput`, `toolResponseMetadata`, `openai:set_globals`, and MCP Apps
    `ui/notifications/tool-result`; the resource reader also retains the v2 URI
    as an alias. After deployment, retrying in the originating conversation
    rendered the card with the exact existing M2 `jobId` and `running` status.
    The local jobs directory and worker PID proved that no duplicate job started.

This proves the previously missing active-turn return path: a non-terminal
Codex result is now consumed by ChatGPT without ending the response or asking
the user to copy it back manually.

## Acceptance result

At this capture point, GACE M0 and M1 are complete and locally committed. The
ChatGPT controller consumed M1's terminal parent result, reviewed it, and
started M2 under the same Codex thread. The historical conversation also
recovered its Apps card and bound the existing M2 job after late result
hydration. T-408, T-410, T-411, and T-412 therefore pass.

This mechanism does not asynchronously wake a ChatGPT conversation after its
response has ended. The explicit Apps return control remains the portable
recovery path for that separate boundary. On the configured host, a local Codex heartbeat
also monitors the exact conversation and may perform the same-chat UI recovery;
that operator automation is not MCP reverse push and is not part of the
portable plugin.
