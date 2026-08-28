# ADR

Add an ADR when you make a significant decision (library, architecture, irreversible change).
Use a simple format: Context / Decision / Consequences.

Latest decision: ADR-0019 adds ZCode as an execution backend behind a
provider seam (client class + six orchestration hooks) in the single guard,
keeping transport, security, durable jobs, and the Windows tunnel lifecycle
provider-independent.
