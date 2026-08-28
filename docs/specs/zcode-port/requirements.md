# ZCode Execution Adapter — Requirements

Status: draft
Baseline: main @ 8c7a404 (guard 5069 lines, 60 contract tests green)
Companion: design.md (protocol facts, seam design), ADR-0019 (why)

## 1. Goal

Allow ChatGPT to supervise **ZCode** through the existing bridge with the same
controller experience it has for Codex: durable jobs, public transcript,
bounded wait, same-turn steer, scoped cancel, signed capabilities, and the
Windows tunnel lifecycle. The bridge remains transport/security/durable
execution only; ChatGPT keeps planning; ZCode executes.

Non-goals: scheduler/DAG/orchestrator features; multi-provider fan-out in one
installation; recursive ZCode→bridge→ZCode paths; emulating capabilities the
backend does not have.

## 2. Provider Selection

R1 The guard MUST accept `--provider {codex,zcode}` and MUST reject any other
value at configuration time (fail closed).
R2 One installed bridge serves exactly one provider; the public tool prefix
MUST equal the provider name (`codex-*` or `zcode-*`).
R3 When `--provider zcode` is selected, the guard MUST NOT spawn or require
any Codex binary, and vice versa.
R4 Adding a future provider (e.g. `dsh`) MUST require only: one new client
class, event-mapping functions, preset mapping, test fake, and CLI/plumbing —
no changes to JobStore, capability codec, controls overlay, cancel fallback,
process ownership, or tunnel lifecycle.

## 3. ZCode Execution Lifecycle

R5 The worker MUST spawn the ZCode App Server as
`[zcode_exe, zcode_cjs, "app-server", "--stdio"]` with env
`ELECTRON_RUN_AS_NODE=1` and cwd = job workspace. The exact binary pair MUST
come from validated absolute-path configuration (no `PATH` fallback beyond
what `require_real_absolute_path` enforces).
R6 The guard MUST speak the ZCode Protocol envelope: request `{id, method,
params}` (no `jsonrpc` member), responses `{id, result|error}`; it MUST answer
server→client requests (`session/requestRuntimePreferences` with
`{nativeSearchEnhancementsEnabled: false}` minimum; `permission.requested` /
`userInput.requested` per preset policy) and MUST fail closed on unknown
server request kinds.
R7 The worker MUST map job lifecycle as: new session → `session/create`;
turn → `session/send`; steer → `session/send` on the same session while a turn
is running; cancel → `session/stop`, then the existing verified worker
fallback after the same grace period.
R8 The worker MUST consume `session/event` notifications (turn.started,
turn.steerQueued, turn.steerDrained, turn.completed, turn.failed,
message.upserted, part.*, tool.updated, permission.*, session.closed) and MUST
terminate the job on `turn.completed`/`turn.failed` or on the synchronous
`session/send` response status, whichever arrives first.
R9 If the ZCode App Server fails to materialize a runtime (e.g.
`model_config_missing`), the job MUST fail with `failureStage` naming the ZCode
configuration problem and `nextAction: repair`; the guard MUST NOT fabricate a
model provider or read credential stores itself.

## 4. Public Surface

R10 Tool names MUST be: `zcode`, `zcode-reply`, `zcode-run`, `zcode-start`,
`zcode-reply-async`, `zcode-wait`, `zcode-job-open`, `zcode-job-status`,
`zcode-job-steer`, `zcode-job-cancel`, `zcode-overview`,
`zcode-project-list`, `zcode-repository-list`, `zcode-thread-list`,
`zcode-thread-read`, `zcode-job-list` — mirroring the Codex surface.
R11 `zcode-wait` MUST keep the 52s default / 55s hard maximum; `zcode-job-status`
MUST return immediately without joining the worker.
R12 On Windows + full-control preset, `zcode`/`zcode-reply` MUST redirect to
the durable path (same as the Codex behavior today); the sync pair for ZCode
MUST be implemented as a short-lived app-server session, not via the unverified
headless `--prompt` mode.

## 5. Presets (real mapping, no string games)

R13 `personal-full-control` MUST map to ZCode `mode: "yolo"`.
R14 `workspace-safe` MUST map to ZCode `mode: "build"` plus a deny-by-default
answer to `permission.requested` (the bridge answers permissions itself; there
is no interactive user), and MUST expose only the sync pair.
R15 Unsupported preset/policy combinations MUST fail configuration.

## 6. Transcript, Report, Handoff (unchanged contracts)

R16 The transcript MUST contain: controller initial `userPrompt`, steers, cancel
reason, and ZCode public output (`text` parts / final answer); it MUST NOT
contain `reasoning` parts, secrets, raw ids, absolute workspace paths.
R17 The report schema (outcome/summary/changedFiles/commands/checks/blockers/
questions/nextStep) MUST be preserved; `patch` parts feed `changedFiles`, `tool`
parts feed `commands`.
R18 `writerActive`/`threadHandoff` MUST keep their existing semantics;
`available` requires a real resumable session (`sessionId` present and worker
closed).
R19 Native ZCode plan/todo items, when observable in events, SHOULD map to the
`plan` transcript kind; if not observable, the bridge MUST NOT synthesize plan
entries (honest degradation).

## 7. Catalog

R20 `zcode-thread-list`/`zcode-thread-read` MUST be backed by
`session/list` (filtered by configured catalog roots) and `session/read` /
`session/messages` of a dedicated catalog app-server connection.
R21 Catalog discovery MUST stay bounded (workspace root + first-level
directories, CATALOG_MAX_ROOTS); no recursion beyond today's behavior.
R22 There is no desktop-project registration call in ZCode; the bridge MUST
NOT fail a `zcode-start` job for registration (remove that failure mode) but
MUST still verify the session is listable before accepting the job as started.

## 8. Windows Installation

R23 Install MUST accept `-ZCodeBin` (ZCode.exe) and resolve the bundled CLI
(`resources\glm\zcode.cjs`) relative to it; both MUST be validated absolute
paths.
R24 config.json MUST gain `provider`, `zcode_bin`, `zcode_cjs`; run-guard MUST
pass `--provider`/`--zcode-bin`/`--zcode-cjs`.
R25 Doctor MUST verify: ZCode.exe present, zcode.cjs present, and — for the
zcode provider — a resolvable model config (`~/.zcode/cli/config.json` or an
explicitly configured model provider), failing closed with a repair hint.
R26 Stop/restart/uninstall MUST keep the exact Codex-era safety ordering
(stop tunnel → verify ownership → revoke jobs → interrupt), reusing the
existing worker.json verification unchanged.
R27 All Windows tests MUST pass in a path containing Chinese characters.

## 9. Acceptance

- 60 existing guard contract tests stay green for the codex provider.
- New ZCode provider contract tests (see test plan in design.md §9) pass.
- `tests/windows/test_windows_port.ps1` passes with provider=zcode fixtures.
- Definition of Done from the porting brief §41: durable job round-trip,
  transcript visibility, steer/cancel on a live ZCode turn, tunnel survives
  cancel, restart recovery, `runtime_guard_match=true`.
