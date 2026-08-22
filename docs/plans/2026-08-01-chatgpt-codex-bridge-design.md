# ChatGPT–Codex Bridge Design Brief

Date: 2026-08-01
Status: Draft awaiting user validation

## Intent

Build the smallest safe proof that a normal ChatGPT web conversation can supervise a real local Codex agent. The proof must show two distinct Codex operations: an initial `codex` call that returns `structuredContent.threadId`, followed by `codex-reply` using that exact ID to correct or extend the work. A generic local command runner does not satisfy this requirement.

## Selected design

Use the official path:

```text
ChatGPT web custom MCP app
  -> OpenAI Secure MCP Tunnel
  -> tunnel-client in an isolated Mac trust boundary
  -> codex mcp-server
  -> non-sensitive sandbox repository
```

This design deliberately excludes CanEngine, Workspace Agent, a custom relay, and Codex App Server from the first proof. CanEngine remains useful for later generic desktop work. App Server remains useful for a later custom rich client that needs streaming events, steer, interrupt, review, and approval flows. Neither is required to prove the first thread-continuity loop.

The raw official MCP server is safe enough only inside a sterile non-admin profile or disposable VM because its public tool schema permits callers to choose unsafe sandbox and approval values. Prompt instructions are not enforcement. Real-repository use therefore requires a separate hardening phase with server-side argument constraints or an equivalently strong host boundary.

## Success boundary

The MVP succeeds only if account eligibility, tool discovery, read-only integrity, approval propagation, bounded workspace write, thread continuity, revocation, and three-run repeatability all pass independently. It does not claim asynchronous reverse wake-up, durable background jobs, peer-to-peer agent messaging, or production reliability.

Detailed requirements and design live in:

- `docs/specs/chatgpt-codex-bridge/requirements.md`
- `docs/specs/chatgpt-codex-bridge/design.md`
- `docs/adr/0001-use-official-codex-mcp-path-for-first-proof.md`
