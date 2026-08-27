# ADR-0018: App Server-authoritative durable model control

## Decision

Use live App Server `model/list` as the authority and carry explicit selections
through the existing durable worker. Disable provider fallback for explicit new
thread models. Use exact-turn rollout `turn_context` as actual-value evidence.

## Consequences

No effort list is hard-coded. Catalog failure rejects override requests before
allocation, while calls omitting both fields retain prior behavior. Missing
rollout evidence remains null rather than being inferred.
