# ZCode Execution Adapter — Tasks

Status: in progress
Order matters; keep diffs small; run guard tests after every task.

- [x] T0 Spec + ADR-0019 committed.
- [ ] T1 Verify headless materialization path (isolated `ZCODE_STORAGE_DIR`),
      record chosen option (config.json vs runtimeModel vs registry) in this
      file and ADR-0019.
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
- [ ] T7 Tests: FAKE_ZCODE + ZCode contract cases (design.md §9); keep all 60
      codex cases green.
- [ ] T8 Windows: `-Provider/-ZCodeBin` in controller, `run-guard-windows.ps1`
      args, doctor model-config check; extend `test_windows_port.ps1`
      (zcode fixture, Chinese path suite).
- [ ] T9 Docs: plugin.json version, README.md + README.zh-CN.md provider
      sections; runtime identity hash re-verified after reinstall.
- [ ] T10 End-to-end Definition of Done (brief §41) on this machine; record
      evidence in `evidence/`.
