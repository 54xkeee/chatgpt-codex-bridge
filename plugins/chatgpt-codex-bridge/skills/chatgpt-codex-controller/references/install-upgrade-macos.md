# macOS Install, Upgrade, and Rollback

Install the plugin with the official `tunnel-client`, a device-specific Tunnel
profile, a workspace path, and the desired preset.

```zsh
/bin/zsh scripts/install-macos.zsh \
  --profile <device-profile> \
  --workspace <absolute-workspace> \
  --preset personal-full-control
```

Then run `scripts/doctor.zsh` and refresh the ChatGPT Secure Tunnel app for the
device. A plugin install does not automatically create or authorize the ChatGPT
app attachment.

For upgrades, install the newer Git ref, rerun `install-macos.zsh` with the same
external profile/workspace, restart, run doctor again, and refresh the app.
Rollback by reinstalling the prior known-good ref and repeating the same
restart/doctor/app refresh sequence.

Version 0.6.1 intentionally starts a new context-bound `jobs-v3` store.
Finish older jobs before upgrading. Old cards and capabilities are not accepted
by the new Guard. The public v0.6.0 release is withdrawn; finish old work before
upgrading, or use the private authoritative archive for forensic recovery only.
