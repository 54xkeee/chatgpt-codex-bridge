# Portable Skill, MCP, and SOP Kit Plan

## Goal

Turn the proven private ChatGPT-to-Codex bridge into a self-contained macOS
plugin that another authorized device or collaborator can install and operate
without relying on a publisher device's global Skills or repository-root documentation.

## Reuse decision

Adapt the existing plugin, Guard, Apps component, installer, and tests. Do not
build another relay or MCP server. Keep official `tunnel-client` responsible for
transport and authorization. Keep `.mcp.json` absent to avoid a recursive local
Codex control path.

## Tranches

1. Add failing package/installer/Guard tests for a bundled staged
   `workspace-new-project` Skill, documentation surfaces, and UI metadata.
2. Stage the portable Skill in bridge-owned runtime state and pass its exact
   validated path from config to Guard worker.
3. Add the standalone README and progressive SOP/MCP references; repair stale
   version/ref documentation.
4. Bump the plugin version and verify source/package identity, isolated install,
   Guard contracts, and the broader bridge suite.
5. Independently review, score, commit, and push the milestone branch.

## Failure and rollback

- Installer failure leaves the external Tunnel profile and credentials intact.
- Reinstall restages only bridge-owned runtime files.
- Uninstall removes exact generated paths and preserves Codex history.
- Rollback pins the prior Git ref, reinstalls the plugin, restarts the service,
  reruns doctor, refreshes the ChatGPT app, and starts a new conversation.

## Acceptance

- Empty temporary HOME passes install and doctor without global Skills.
- The staged Skill/script are validated and removed on uninstall.
- Skill/plugin validators and all relevant tests pass fresh.
- A real remote ref contains the exact manifest version and documentation.
