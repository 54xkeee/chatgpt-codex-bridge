# ZCode Execution Adapter — Tasks

Status: SHELVED (2026-08-28, ADR-0020) — do not use; end-to-end DoD (T10)
was never executed. Kept as an archive on the dormant `zcode-port` branch.
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
- [x] T2 Guard: `--provider`/`--zcode-bin`/`--zcode-cjs` config plumbing +
      validation + preset matrix.
- [x] T3 Guard: `ZcodeAppServerClient` (spawn/envelope/server-request
      answering/permission queue) + unit coverage.
- [x] T4 Guard: orchestration hooks in `run_job` + `record_event` mapping for
      ZCode events (turn/message/part/tool/patch/reasoning filter).
- [x] T5 Guard: steer/cancel path through `process_worker_controls`
      (`session/send` / `session/stop`) with overlay semantics unchanged.
- [x] T6 Guard: tool-prefix parameterization → `zcode-*` surface; Windows
      sync→async redirect keyed on provider; catalog over `session/*`.
- [x] T7 Tests: FAKE_ZCODE + 12 ZCode contract cases
      (tests/bridge/test-zcode-mcp-guard.py, wired into CI) — all green;
      60 Codex cases still green.
- [x] T8 Windows: `-Provider/-ZCodeBin` in controller, `run-guard-windows.ps1`
      args, doctor checks; extend `test_windows_port.ps1`
      (zcode fixture, Chinese path suite).
- [x] T8b Model provider bootstrap: installer `-ZCodeModelBaseUrl/-ZCodeModel/
      -ZCodeApiKeyEnv` writes `zcode-model.json`; worker upserts the provider
      (env-referenced key) and creates with `model`; doctor fails closed when
      the env var is unset; Stop-Tunnel taskkill made race-tolerant.
- [x] T9 Docs: plugin.json version, README.md + README.zh-CN.md provider
      sections; runtime identity hash re-verified after reinstall.
      (docs done; hash re-verify never run).
- [ ] T10 End-to-end Definition of Done (brief §41) on this machine; record
      evidence in `evidence/`.
