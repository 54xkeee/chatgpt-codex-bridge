# Portable ChatGPT–Codex Plugin Kit Plan

Task: `T-406`
Spec: `chatgpt-codex-bridge`

## Architecture

Adapt the existing Guard and T-405 LaunchAgent checks into a self-contained plugin. Keep OpenAI's `tunnel-client` as the only Tunnel implementation. Render user/device paths and the local execution preset during installation; keep the external profile and credentials untouched.

## Implementation sequence

1. Add failing package and installer contract tests.
2. Scaffold `plugins/chatgpt-codex-bridge` and the repo marketplace.
3. Add the controller/setup Skill and validated plugin manifest.
4. Parameterize Guard policy so the installer can fix either `personal-full-control` or `workspace-safe` without exposing a public selector.
5. Implement the macOS service command and thin install/doctor/uninstall wrappers.
6. Render a user LaunchAgent and runtime wrapper from non-secret configuration.
7. Validate the plugin, Skill, marketplace, dry-run installation, generated plist, Guard preset propagation, and every existing bridge test.
8. Verify the currently installed personal service remains ready.
9. Install/test the repository marketplace in an isolated Codex home, then update docs/tasks/memory and push the milestone.

## Rollback

- The portable installer's `stop` unloads only its exact label.
- `uninstall` removes only its generated LaunchAgent, runtime copy, state, and logs; it leaves the Tunnel profile, credentials, Codex sessions, and repository untouched.
- T-406 does not replace the already-running `com.example.chatgpt-codex-bridge` job.
