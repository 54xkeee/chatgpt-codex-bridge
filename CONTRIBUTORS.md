# Contributors and project lineage

This repository intentionally preserves the upstream Git history and MIT
license so that the project lineage remains explicit.

## Original project

**Larry (`@larryppgg`)** created the original
[`chatgpt-codex-bridge`](https://github.com/larryppgg/chatgpt-codex-bridge),
including the Secure MCP Tunnel architecture, Codex MCP Guard, macOS service
controller, signed capability model, durable job workflow, and plugin layout.

## Windows edition

**`@54xkeee`** maintains this Windows port and extended edition. This edition
adds:

- a native Windows PowerShell 5.1 controller and per-user runtime;
- Windows path, UTF-8, process-tree, MCP EOF, and atomic status fixes;
- the global Codex project/repository/thread/job catalog;
- bounded thread history and signed catalog pagination;
- structured job progress and terminal return reports;
- Windows package, drift, revocation, and live end-to-end verification.

The Windows work was developed through a **ChatGPT Pro in-the-loop** workflow:
ChatGPT Pro acted as the supervising and review layer while Codex inspected,
implemented, tested, installed, and exercised the local bridge.

## Copyright and license

The upstream copyright notice remains in `LICENSE`. Contributions to this fork
are distributed under the same MIT license.
