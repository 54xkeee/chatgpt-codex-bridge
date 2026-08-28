# ZCode Execution Adapter — Tasks

Status: in progress
Order matters; keep diffs small; run guard tests after every task.

- [x] T0 Spec + ADR-0019 committed.
- [x] T1 Headless materialization verified end-to-end against a local
      openai-compatible mock (probe_h/probe_i, isolated USERPROFILE):
      `~/.zcode/cli/config.json` = `{"model":{"main":"provider/model"}}`;
      provider definitions injected via `workspace/upsertModelProvider`
      (`apiKey: {source:"env", name}`); `session/create` materializes and
      returns `result.session.sessionId`; create's `mode` param does NOT stick
      — worker MUST call `session/setMode` after create; `session/send`
      returns `{accepted:true}` and drives `turn.started` → `model.streaming`
      → `turn.completed{resultType,response}` (or `turn.failed`);
      steer while running = `turn.steerQueued{targetTurnId}` (drain event
      pending until next model request); `session/stop` terminates the turn
      promptly (`turn.failed` on abort); unknown server requests
      (`interaction/requestOfficialMcpAuthHeaders`) may be declined with an
      error reply; extra notification channels (v4/telemetry, state.updated,
      computer-use/*, process/*) are informational and ignored.
- [ ] T2 Guard: `--provider`/`--zcode-bin`/`--zcode-cjs` config plumbing +
      validation + preset matrix.
- [ ] T3 Guard: `ZcodeAppServerClient` (spawn/envelope/server-request
      answering/permission queue) + unit coverage.
- [ ] T4 Guard: orchestration hooks in `run_job` + `record_event` mapping for
      ZCode events (turn/message/part/tool/patch/reasoning filter).
- [ ] T5 Guard: steer/cancel path through `process_worker_controls`
      (`session/send` / `session/stop`) with overlay semantics unchanged.
- [ ] T6 Guard: tool-prefix parameterization → `zcode-*` surface; Windows
      sync→async redirect keyed on provider; catalog over `session/*`.
- [x] T7 Tests: FAKE_ZCODE + 12 ZCode contract cases
      (tests/bridge/test-zcode-mcp-guard.py, wired into CI) — all green;
      60 Codex cases still green.
- [ ] T8 Windows: `-Provider/-ZCodeBin` in controller, `run-guard-windows.ps1`
      args, doctor model-config check; extend `test_windows_port.ps1`
      (zcode fixture, Chinese path suite).
- [ ] T9 Docs: plugin.json version, README.md + README.zh-CN.md provider
      sections; runtime identity hash re-verified after reinstall.
- [ ] T10 End-to-end Definition of Done (brief §41) on this machine; record
      evidence in `evidence/`.
