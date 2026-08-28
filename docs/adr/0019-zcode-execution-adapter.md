# 0019 — ZCode execution adapter behind a provider seam

Date: 2026-08-28
Status: Accepted

## Context

The bridge must let ChatGPT supervise ZCode with the same controller
experience as Codex (durable jobs, transcript, bounded wait, same-turn steer,
scoped cancel, signed capabilities). The existing guard implements that
experience against the Codex App Server over stdio JSON-RPC, with Codex logic
inlined at ~13 RPC call sites and 2 event handlers (see zcode-port/design.md).

Investigation of the locally installed ZCode (CLI 0.16.5, desktop 3.10.1)
showed it ships an equivalent canonical lifecycle: an `app-server --stdio`
NDJSON protocol (session/create|send|stop|events…, steer and terminal events
built in, `reasoning` as an explicit private part type, resumable sequenced
event log). The desktop itself spawns this server as
`ZCode.exe zcode.cjs app-server --stdio` with `ELECTRON_RUN_AS_NODE=1` and
cwd = workspace. Headless materialization additionally requires an explicit
model provider configuration and fails closed with `model_config_missing`
otherwise.

## Decision

1. Add a provider seam inside the single guard file — one client class
   (`ZcodeAppServerClient`) plus six orchestration hooks
   (start/send/steer/interrupt/history/close) — and dispatch on a new
   `--provider {codex,zcode}`. No provider framework, no file split, no
   rename of existing behavior.
2. One installation serves one provider; public tool names take the provider
   prefix (`zcode-*`). Presets map for real: full-control → `mode:"yolo"`,
   workspace-safe → `mode:"build"` with deny-by-default permission answering.
3. Sync short-task tools for ZCode are implemented as short-lived app-server
   sessions; the headless `--prompt` one-shot mode is not used (unverified).
4. The bridge never fabricates model credentials; missing ZCode model config
   fails closed with a repair action, and install/doctor verify the config.
5. Future providers (e.g. a hypothetical `dsh`) plug in at the same seam:
   new client class + event mapping + preset mapping + test fake; core
   job/capability/cancel/ownership/tunnel code is provider-independent.

## Consequences

- The mature transport/security/durable-job surface is reused verbatim, so
  regression risk concentrates in the six hooks and event mapping.
- Truthful capability reporting is preserved: anything ZCode does not expose
  (e.g. desktop project registration) is removed rather than simulated, and
  observable-but-unverified channels (todo/plan) degrade honestly.
- The Codex path keeps its existing tests (60 cases) as the regression base;
  the ZCode path gains an equivalent contract suite behind a protocol fake.
- Day-one verification (isolated storage) selects how headless model config
  is satisfied before any worker code ships.
