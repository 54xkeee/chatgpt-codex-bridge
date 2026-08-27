# Durable Model Control Requirements

- `codex-model-list` MUST return the current App Server catalog, unique default,
  and supported/default reasoning efforts with signed pagination.
- `codex-run`, `codex-start`, and `codex-reply-async` MUST accept optional
  `model` and `reasoningEffort` and validate explicit combinations before job
  allocation.
- Explicit values MUST reach canonical `thread/start|resume` and `turn/start`.
  Unsupported combinations MUST fail closed; omitted values MUST preserve the
  prior payload.
- Public state MUST separate requested values from exact-turn values observed
  in rollout `turn_context`.

Acceptance requires focused forwarding/failure/default/schema tests and the
complete Guard suite.
