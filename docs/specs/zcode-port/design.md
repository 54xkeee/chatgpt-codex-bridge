# ZCode Execution Adapter — Design

Status: draft
Companion: requirements.md, ADR-0019

## 1. Verified protocol facts (ZCode CLI 0.16.5 / desktop 3.10.1)

Spawn (confirmed from the desktop's own spawn code + live probes):

```
command: ZCode.exe          (Electron host, e.g. D:\ZCode\ZCode.exe)
args:    [zcode.cjs, "app-server", "--stdio"]
cwd:     <workspace path>
env:     ELECTRON_RUN_AS_NODE=1   (+ inherited)
```

Wire format: NDJSON. Requests `{id, method, params}` — no `jsonrpc` member.
Responses `{id, result}` / `{id, error}`. The server also issues requests to
the client (same envelope); the client MUST answer them.

Method surface (from the method tables present in both app.asar and zcode.cjs):

- session: create, list, read, messages, events, subscribe, send, stop,
  cancelBackgroundTask, fork, compact, goal, close, setModel, setThoughtLevel,
  updateRuntimeModelConfig, setMode, subagents
- workspace: readState, upsertModelProvider, removeModelProvider,
  setDefaultModel, setDefaultMode, generateText, …

Key schemas (zod, `.strict()`):

- `session/create`: `{sessionId?, workspace{workspaceKey,workspacePath},
  parentSessionId?, mode: build|edit|plan|yolo, model?{providerId,modelId},
  runtimeModel?, persistence?, titleGenerationEnabled?, mcpServers[],
  toolAllowlist[], toolDenylist[], importedHistory?}`
- `session/send`: `{sessionId, content, inputId?, queryId?, attachments?,
  expectedRevision?, runtimeModel?, automationId?…}`
- `session/messages`: `{sessionId, afterSeq?, limit?}`
- `session/events` (subscribe): `{sessionId, deliveryKind, afterSeq?,
  includeSnapshot?}` → `{sessionId, eventSeq, events[], snapshot?}`
- prefs reply (`session/requestRuntimePreferences`): `{nativeSearchEnhancementsEnabled:
  boolean, memoryEnabled?=false, askUserQuestionAutoResolutionEnabled?=true,
  integratedTerminalShell?, modelContextBudgetStrategy?="preflight-v1"}`
- session status enum: `idle|running|waiting|paused|completed|error`

Event union (each event carries `sequenceNumber`):

```
session.created | session.resumed | session.updated | session.titleUpdated
session.closed
turn.started | turn.steerQueued | turn.steerDrained | turn.completed | turn.failed
message.upserted | message.removed
part.started | part.delta | part.upserted | part.removed
model.streaming | tool.updated
permission.requested | permission.resolved
userInput.requested | userInput.resolved
checkpoint.created | rewind.triggered | streamRecovery.updated
```

Message part types: `text | reasoning | file | tool | step-start | step-finish
| snapshot | patch | compaction …`. `reasoning` is the private chain-of-thought
and is filtered exactly where Codex reasoning items are filtered today.

## 2. Seam in the guard (single-file, no provider framework)

New code lives in `codex-mcp-guard.py` (both mirrors stay byte-identical):

1. `ZcodeAppServerClient` — same interface as `AppServerClient`
   (spawn/send/read/request/notify/close). Differences:
   - spawn per §1, plus a reader that also routes server→client requests;
   - envelope without `jsonrpc`;
   - auto-answers `session/requestRuntimePreferences` from a policy object;
     queues `permission.requested`/`userInput.requested` for the worker loop
     (deny-by-default under workspace-safe; auto-approve under yolo);
     fails closed on unknown server request methods.
2. Six orchestration hooks replace the inline Codex calls in `run_job`,
   `CodexCatalog`, and `process_worker_controls`:

```
provider_start_session(client, job, ...)     # thread/start | session/create
provider_send_turn(client, thread/session)   # turn/start | session/send
provider_steer(client, ids, prompt)          # turn/steer | session/send
provider_interrupt(client, ids)              # turn/interrupt | session/stop
provider_history(client, ids, paging)        # thread/turns/list | messages/events
provider_close(client)                       # close app server
```

   Codex keeps its current bodies; ZCode implements the right column. All
   other call sites dispatch on `config.provider`.
3. Event mapping in `record_event`: ZCode events → the same internal
   `state.lastEvent` / `update_report_from_item` / transcript primitives:
   - `message.upserted` (text part, final) → agentMessage transcript entry
   - `part.delta/upserted` (text) → bounded activity; `reasoning` parts → ignored
   - `patch` parts → `changedFiles`; `tool` parts → `commands`/`checks`
   - `turn.completed`/`turn.failed` → terminal (mirrors turn.status handling)
   - `turn.steerQueued/steerDrained` → steer transcript `delivery` transitions
4. Tool naming: `build_public_tools(prefix, …)`; every literal `codex…` tool
   name/description becomes `f"{prefix}…"`. Windows sync→async redirect keys
   off the prefix.
5. Config plumbing: `--provider`, `--zcode-bin`, `--zcode-cjs`;
   `parse_configuration` validates provider/paths/preset matrix
   (zcode+yolo, zcode+build only).

Out of scope / untouched: JobStore, CapabilityCodec (cgb2), controls.json
mailbox + overlay, cancel fallback + `terminate_verified_job_worker`,
`_worker_command_matches`, resource limits, widget, catalog filesystem
discovery, Windows tunnel lifecycle.

## 3. Model/runtime configuration (VERIFIED, fail closed)

Verified end-to-end twice: first against a local openai-compatible mock with
isolated `USERPROFILE` (probe_h/probe_i), then against the real BigModel
endpoint shape on the real workspace (probe_upsert_noconfig).

Established facts:
- The desktop GUI injects its provider config into its own app-server
  processes at runtime and does NOT persist it to shared storage — a
  bridge-spawned instance sees `providers=[]` and fails `model_config_missing`
  (the shipped `resources/model-providers` catalog is not loaded headless
  either; both builtin coding-plan ids fail with "missing baseURL").
- There is no official standalone CLI distribution (install docs ship only
  the Electron desktop app).
- The verified headless path needs NO config.json: the worker calls
  `workspace/upsertModelProvider {workspace, provider}` with
  `{providerId, kind: "anthropic", baseURL, apiKey: {source: "env", name},
  models: [{modelId, …}]}` and then passes `model: {providerId, modelId}` in
  `session/create`. The API key is read from the environment at request time;
  the bridge never persists it.

Wiring: the installer writes `runtime\zcode-model.json`
(`{providerId, label, baseURL, apiKeyEnv, model}`) from
`-ZCodeModelBaseUrl/-ZCodeModel/-ZCodeApiKeyEnv` and records it as
`zcode_provider_config`; the worker validates and loads it
(`load_zcode_provider_config`), upserts, and creates. Doctor fails closed
when the named environment variable is unset. The legacy fallback (an
   existing `~/.zcode/cli/config.json`) remains supported. Jobs that still fail
   materialization map to `failureStage: "zcode_model_config"`,
   `nextAction: "repair"`.

Other verified protocol facts (probe_h/probe_i):
- `session/create` returns the runtime snapshot at `result.session.sessionId`;
  the create `mode` param is ignored, so the worker calls
  `session/setMode {sessionId, mode}` after create.
- Terminal: `turn.completed` payload carries `response` (final answer) and
  `resultType`; `turn.failed` carries `error`. `session/stop` ends the active
  turn promptly (observed `turn.failed` with a provider-abort error).
- Steer: `session/send` while running → `turn.steerQueued {targetTurnId}`;
  drain happens at the next model request within the turn
  (`turn.steerDrained`). No optimistic-concurrency token is needed.
- Server→client requests other than `session/requestRuntimePreferences`
  (e.g. `interaction/requestOfficialMcpAuthHeaders`) are declined with a
  JSON-RPC error reply; the session proceeds. Notification channels
  (`state.updated`, `v4/telemetry/event`, `computer-use/operation-event`,
  `process/mcpTelemetry`) are informational; `state.updated` status/reason
  feeds activity/lastEvent.

## 4. Preset mapping

| Bridge preset | ZCode | Bridge-side behavior |
|---|---|---|
| personal-full-control | `mode: "yolo"` | auto-approve nothing (none requested); full tool surface |
| workspace-safe | `mode: "build"` + `toolDenylist` kept empty | deny-by-default on `permission.requested`; sync pair only |

## 5. Catalog mapping

`CodexCatalog` app-server calls swap to a ZCode connection:
`session/list` filtered by `require_known_catalog_roots` (workspaceKey/path
match), `session/read`, `session/messages`. Git probe, cursors, bounding,
signing unchanged. Sessions outside catalog roots are invisible (fail closed,
same as Codex cwd filtering). `register_desktop_project` becomes a no-op for
zcode (requirements R22).

## 6. Sync pair on Windows

`zcode`/`zcode-reply`: one dedicated short-lived app-server connection per
call (`SYNC_MAX_IN_FLIGHT=1` preserved), `session/create` + `session/send` +
terminal event, threadId capability returned for `zcode-reply`. No use of the
unverified `--prompt` headless mode.

## 7. Files touched

- `plugins/chatgpt-codex-bridge/bridge/codex-mcp-guard.py` (+ `scripts/bridge/` mirror)
- `plugins/chatgpt-codex-bridge/scripts/chatgpt-codex-bridge-windows.ps1`
  (`-Provider`, `-ZCodeBin`), `run-guard-windows.ps1` (extra args)
- `tests/bridge/test-codex-mcp-guard.py` (FAKE_ZCODE + cases)
- `tests/windows/test_windows_port.ps1` (provider=zcode fixture)
- `.codex-plugin/plugin.json` (version), both READMEs, zh-CN README

## 8. Risks / implementation-order verifications

- V1: materialization path (§3 a/b/c) — verify on day 1, isolated storage.
- V2: `session/stop` = canonical cancel semantics (grace + fallback already
  protects correctness even if stop is weak).
- V3: `expectedRevision` conflict behavior for steer (optimistic concurrency).
- V4: todo/plan event channel visibility (R19 degrade if absent).
- V5: resume semantics of `session/create(sessionId)` for `zcode-reply-async`.

## 9. ZCode test plan (adds to the 60 existing cases)

Fake: `FAKE_ZCODE_SOURCE` implementing the app-server subset above in one
file (modeled on FAKE_CODEX): create/subscribe/send/stop/messages + scripted
event streams + fault switches (malformed, slow, fail, foreign session,
model_config_missing, permission loop).

Cases: five job states; bounded wait incl. hard max; status immediacy +
private-field absence; steer accepted only while running, overlay shows
`queued` then dedupes on consumption; cancel on running uses `session/stop`
then verified fallback, terminal idempotence, tunnel untouched; transcript
contains controller prompt/steer/cancel + ZCode text, never `reasoning`,
secrets, raw ids, absolute workspace paths; handoff
pending→bridge-owned→available; legacy job records without controls/transcript
read safely; tools list truthful annotations under `zcode-*`; preset matrix
(zcode+workspace-write rejected, yolo/build accepted).
