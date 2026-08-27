# Job control, transcript, and handoff tasks

- [x] T1 Define the controller/bridge boundary and acceptance criteria.
- [x] T2 Extend durable state with public transcript and writer/handoff metadata.
- [x] T3 Make `codex-job-status` model-visible and make `codex-wait` bounded/configurable without forced polling semantics.
- [x] T4 Add per-job idempotent cancel with canonical `turn/interrupt` and verified process-tree fallback.
- [x] T5 Add same-turn `codex-job-steer` through canonical `turn/steer`.
- [x] T6 Record controller prompts/steers/cancel reasons and public Codex messages without private reasoning.
- [x] T7 Add focused contract/integration tests for wait, transcript, steer, cancel, fallback, and handoff.
- [x] T8 Update controller/MCP documentation and package mirror.
- [x] T9 Run the complete repository CI test commands and review the final diff.