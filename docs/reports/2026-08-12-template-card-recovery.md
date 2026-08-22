# T-408 ChatGPT template-card recovery

Date: 2026-08-12
Result: implementation and app discovery passed; one user-originated recovery
call remains for final conversation-level acceptance.

## Observed failure

The ChatGPT web tool call returned a durable job handle and the local worker
continued running, while the rendered result card showed:

```text
Failed to fetch template
```

Local service health, control-plane connectivity, and the detached Codex worker
were all present. The visible failure therefore did not mean that `codex-start`
failed or that the job needed to be submitted again.

## Root cause

The affected ChatGPT message retained an older developer-app/template snapshot.
Refreshing the installed app caused new `resources/read` requests to reach the
Guard and successfully discovered the current versioned component. Retrying the
historical red card produced no new resource request, including after a page
reload. That card cannot be upgraded in place.

## Repair

- Added `codex-job-open(jobId)`, a model-visible read-only tool that reads the
  existing durable job and renders the current component.
- The recovery tool never enqueues a worker and cannot create a duplicate Codex
  run.
- Retained `codex-job-status(jobId)` as app-only polling.
- Added redacted resource-method diagnostics containing only the method,
  parameter type/keys, and contract-check state.
- Refreshed the installed ChatGPT app; discovery showed the recovery tool and
  fetched the current component resource.

## Evidence boundary

No Tunnel identity, credential, request identity, Codex thread identity, job
identity, prompt, result, or local user data is retained in this report. The
remaining acceptance step is a new `codex-job-open` call from the originating
conversation. The historical failed card is expected to remain red.
