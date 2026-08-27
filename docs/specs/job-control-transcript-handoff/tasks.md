# Job control, transcript, and handoff tasks

- [x] T1 Define the controller/bridge boundary and acceptance criteria.
- [ ] T2 Extend durable state with public transcript and writer/handoff metadata.
- [ ] T3 Make `codex-job-status` model-visible and make `codex-wait` bounded/configurable without forced polling semantics.
- [ ] T4 Add per-job idempotent cancel with canonical `turn/interrupt` and verified process-tree fallback.
- [ ] T5 Add same-turn `codex-job-steer` through canonical `turn/steer`.
- [ ] T6 Record controller prompts/steers/cancel reasons and public Codex messages without private reasoning.
- [ ] T7 Add focused contract/integration tests for wait, transcript, steer, cancel, fallback, and handoff.
- [ ] T8 Update controller/MCP documentation and package mirror.
- [ ] T9 Run the complete repository CI test commands and review the final diff.