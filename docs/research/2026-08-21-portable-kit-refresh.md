# Portable Kit Reuse Refresh

Date: 2026-08-21

## Existing assets

- The repository already contains the working stdio MCP Guard, durable job
  store, Apps result-return component, macOS LaunchAgent installer, controller
  Skill, marketplace manifest, and contract tests.
- OpenAI's official `tunnel-client` already owns Secure Tunnel transport,
  health, profile association, and control-plane polling.

## External practice

- OpenAI plugins package reusable Skills and optional MCP/apps resources behind
  a manifest and benefit from progressive-disclosure references.
- MCP tools need stable names, precise schemas, truthful annotations, and clean
  stdio protocol output.
- The MCP Inspector provides a reusable CLI/UI verification surface; the local
  contract suite remains the deterministic release gate.

## Decision

Reuse and adapt the current plugin. A second MCP server or repository would add
identity, deployment, and recovery drift without independent value. The only
custom addition is the portable bootstrap Skill and explicit staged-path
plumbing because the proven Guard currently depends on a user-global Skill.

## Distribution boundary

The existing GitHub remote is private. It supports the owner's other devices
and invited collaborators. Public availability requires a separate repository
visibility decision and is not inferred from a push.
