# ADR

Add an ADR when you make a significant decision (library, architecture, irreversible change).
Use a simple format: Context / Decision / Consequences.

Latest decision: ADR-0020 shelves the ZCode execution-provider port
(ADR-0019) on the dormant `zcode-port` branch — do not use; `main` returns
to the Codex-only state. Before that, ADR-0019 had added ZCode as an
execution backend behind a provider seam (client class + six orchestration
hooks) in the single guard, keeping transport, security, durable jobs, and
the Windows tunnel lifecycle provider-independent.
