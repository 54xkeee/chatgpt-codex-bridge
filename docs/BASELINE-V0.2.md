# Baseline Report — ChatGPT Computer Runtime V0.2

- Date: 2026-09-04
- Host OS: Windows (x64)
- Shell: Windows PowerShell / PowerShell Core
- Python Runtime: C:\\Python314\\python.exe (Python 3.14.0a4)
- Node Runtime: C:\\Program Files\\nodejs\\node.exe

## Git & Repository Baseline
- Repository: D:\\cumcm\\chatgpt-codex-bridge
- Branch: feat/generic-executor-controller
- Base commit (main): 86b215f591e1574d8e6aef2a13f35058d5a8aa58
- Model-control commit: e5bc366686749057025a4aceff2d9d31f36ebb2c
- Merged HEAD: Current HEAD of feat/generic-executor-controller

## Live Runtime Baseline
- Live Tunnel PID: 34088 (tunnel-client.exe v0.0.12)
- State Directory: C:\\Users\\虚空之神\\AppData\\Local\\chatgpt-codex-bridge
- Runtime Guard Path: C:\\Users\\虚空之神\\AppData\\Local\\chatgpt-codex-bridge\\runtime\\codex-mcp-guard.py
- Installed Plugin Version in Config: 0.6.1+codex.20260828073040
- Source Plugin Manifest Version: 0.6.1+codex.20260828073040
- Runtime Guard SHA256: 970CC48061859DD454728705EF2E63C9BAAA38302619C2BA531A1EC694896071
- Source Guard SHA256: 970CC48061859DD454728705EF2E63C9BAAA38302619C2BA531A1EC694896071 (Identical match with live runtime)
- Active Workspace: D:\\cumcm
- Active Preset: personal-full-control (sandbox: danger-full-access, approval_policy: never)
- Existing Job Store: C:\\Users\\虚空之神\\AppData\\Local\\chatgpt-codex-bridge\\jobs-v3

## Installed Toolchain & Executors
1. **Codex**:
   - Binary: C:\\Users\\虚空之神\\AppData\\Roaming\\npm\\codex.cmd
   - Version: codex-cli 0.147.0
   - Mode: App Server / stdio
2. **Pi**:
   - Binary: C:\\Users\\虚空之神\\AppData\\Roaming\\npm\\pi.cmd
   - Version: @earendil-works/pi-coding-agent@0.84.4
   - Mode: pi --mode rpc
   - Model Discovery: pi --list-models functional
3. **Antigravity**:
   - Binary: C:\\Users\\虚空之神\\AppData\\Local\\agy\\bin\\agy.exe
   - Version: 1.1.22
   - Mode: headless agy.exe -p --output-format stream-json --input-format stream-json
   - Flags verified: --output-format, --input-format, --conversation, --continue, --add-dir, --model, --effort, --dangerously-skip-permissions
4. **MCPX**:
   - Package: @kwonye/mcpx available for upstream MCP registration via ~/.mcpx/.mcp.json
