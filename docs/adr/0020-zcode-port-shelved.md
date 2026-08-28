# ADR-0020: Shelve the ZCode execution-provider port

Date: 2026-08-28
Status: Accepted (supersedes ADR-0019)

## Context

ADR-0019 added ZCode as a second execution backend behind a provider seam.
The adapter was implemented end to end (commits `17369a3..d406eaf`): protocol
client, durable-job orchestration, steer/cancel, catalog, Windows installer,
headless provider bootstrap, and 13 contract tests (73 total green). The
end-to-end Definition of Done (spec task T10) was never executed against a
real model endpoint, and the owner decided on 2026-08-28 to stop investing
in the port.

## Decision

- Freeze the port on the `zcode-port` branch and mark it dormant: do not
  install, do not use, do not expect fixes.
- Return `main` to the Codex-only state (commit `8c7a404`). All ZCode
  commits remain reachable on `zcode-port` only.

## Consequences

- The branch is unmaintained and will rot as `main` moves on. A future
  revival must start from `zcode-port`, rebase deliberately, and complete
  spec task T10 (end-to-end DoD) before any real use.
- `main` keeps only the Codex backend; CI on `main` runs the Codex suite.
- The protocol knowledge captured in `docs/specs/zcode-port/design.md` stays
  valid as a record, but is not a support commitment.
