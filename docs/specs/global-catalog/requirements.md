# Global Codex Catalog Requirements

## Requirements

- **GC-R1**: In the `personal-full-control` preset, the Guard MUST expose read-only tools for an overview, Codex projects, Git repositories, Codex threads, paginated thread items, and durable jobs.
- **GC-R2**: Discovery MUST stay within the configured bridge workspace and its direct child directories. It MUST NOT recursively scan unrelated filesystem roots.
- **GC-R3**: Thread discovery MUST use Codex App Server `thread/list`; thread metadata MUST use `thread/read`; conversation history MUST prefer `thread/turns/list` with bounded page sizes and opaque signed cursors, with `thread/read(includeTurns=true)` as the bounded compatibility path.
- **GC-R4**: Raw Codex thread identifiers and App Server cursors MUST remain internal. Every public identifier or cursor MUST be an installation-scoped signed capability bound to the workspace and policy context.
- **GC-R5**: Repository entries MUST report a canonical root, display name, current branch when available, dirty state when available, and the number of matching recent Codex threads. Git probes MUST have bounded execution time.
- **GC-R6**: Durable job state MUST expose a stable phase, concise activity, last activity timestamp, failure stage, and next action in addition to terminal status and content.
- **GC-R7**: Async Codex prompts MUST include a fixed task-return contract. Terminal job results MUST expose a structured report containing outcome, summary, changed files, commands, checks, blockers, questions, and next step when those values are known.
- **GC-R8**: Catalog tools MUST be read-only, bounded, and absent from unsupported policy presets.
- **GC-R9**: The Windows controller MUST run on Windows PowerShell 5.1 and PowerShell 7, and the Guard MUST exit promptly after its MCP stdin reaches EOF.
- **GC-R10**: The installed plugin cache, staged runtime, and repository source MUST expose enough version/hash information for `doctor` to identify runtime drift.

## Acceptance criteria

1. Guard contract tests discover the new read-only tools and verify their annotations and schemas.
2. Fixture App Server tests cover thread list, metadata read, turn pagination, signed cursor rejection, and workspace filtering.
3. Job tests cover progress fields and the terminal structured report.
4. Windows tests cover PowerShell 5.1 path validation, Guard EOF shutdown, and transient `status.json` replacement contention.
5. Plugin package tests keep repository and packaged Guard copies byte-identical.
6. A live Windows proof lists the current repository and at least one Codex thread, reads a bounded item page, runs a same-workspace job, and returns its terminal report.

## Non-goals

- Whole-disk repository discovery.
- Importing identities or runtime state from another bridge installation.
- Returning hidden reasoning content.
- Replacing the official Tunnel client or Codex App Server.
