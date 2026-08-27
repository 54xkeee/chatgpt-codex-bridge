# Durable Model Control Design

The Guard reads bounded live `model/list`, normalizes it, and uses the existing
capability codec for pagination. Explicit selections resolve before the
existing `JobStore.enqueue`. The single durable worker adds model to
`thread/start|resume` and `turn/start`, effort to `turn/start`, and disables
provider fallback for an explicit new-thread model.

Admission persists requested fields. After the root turn, the worker accepts
only an App Server-returned rollout path under `$CODEX_HOME/sessions`, matches
the exact turn ID, and publishes actual model/effort from `turn_context`.
