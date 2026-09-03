# IMPLEMENTATION REPORT — ChatGPT Computer Runtime V0.2
## 基于现有 Codex MCP Guard 泛化的本机多执行器控制系统实施总结

### A. Baseline
- **Repository**: `D:\cumcm\chatgpt-codex-bridge`
- **Branch**: `feat/generic-executor-controller`
- **Base Commit (main)**: `86b215f591e1574d8e6aef2a13f35058d5a8aa58`
- **Model-control Commit**: `e5bc366686749057025a4aceff2d9d31f36ebb2c`
- **Installed Guard version**: `0.6.1+codex.20260828073040`
- **Runtime bridgeVersion**: `0.6.1+codex.20260828073040`
- **Runtime guardSha256**: `970CC48061859DD454728705EF2E63C9BAAA38302619C2BA531A1EC694896071`
- **Existing workspace**: `D:\cumcm`
- **Existing preset**: `personal-full-control` (sandbox: `danger-full-access`, approval_policy: `never`)

---

### B. 现有 Guard 能力复用情况
| 能力模块 | 复用状态 | 说明 |
| :--- | :--- | :--- |
| **job store** | `reused directly` | 直接复用现有 `JobStore` 与 `jobs-v3` 目录持久化结构 |
| **capability** | `refactored` | 提取现有 `CapabilityCodec` 至 `controller.capability`，增加 `session` / `session-request` audience，保持 HMAC-SHA256 签名安全性与 context 绑定 |
| **process ownership** | `reused directly` | 复用现有进程树归属追踪与安全终止逻辑（`terminate_verified_job_worker`） |
| **wait** | `reused directly` | 复用基于 poll interval 与超时上限的有界等待逻辑 |
| **status** | `reused directly` | 保持 `phase` / `activity` / `report` 结构化状态输出格式 |
| **steer** | `reused directly` | Codex 适配器复用 `controls.json` / App Server 原生 turn steer 注入机制 |
| **cancel** | `reused directly` | 复用 turn interrupt 与有界优雅退出策略 |
| **recovery** | `reused directly` | 复用启动时针对 active / stale jobs 的自愈检测机制 |
| **App Server** | `reused directly` | 复用 `AppServerClient` 进行原生 thread/turn 交互 |
| **model catalog** | `reused directly` | 复用 `CodexModelCatalog` 模型与 reasoning effort 目录 |

---

### C. 新增核心模块
1. **`ExecutorSession` & `SessionStore` (`controller/session.py`)**:
   - 严格 Session 状态机：`PENDING_APPROVAL` → `AUTHORIZED_IDLE` ⇄ `RUNNING`，支持 `REVOKED` 与 `REAUTH_REQUIRED`。
   - Session 仅在首次建立、换 Executor、换 Workspace、权限升级或已被 Revoke 时需要人工批准。
2. **`ApprovalServer` (`controller/approval_server.py`)**:
   - 仅绑定 `127.0.0.1`，严格强校验 loopback peer、Host 与 Origin。
   - GET 请求纯展示，绝不产生批准/拒绝副作用；POST 请求强制校验页面一次性 anti-CSRF token。
   - CSRF token 绝不经由 MCP 泄露给客户端。
3. **`WorkspaceLockManager` (`controller/workspace_lock.py`)**:
   - Single Writer Lock 严格绑定到 **Turn**（非整个 Session）。Turn 运行期间持锁，完成后原子释放。
4. **`CodexSessionGate` (`controller/codex_gate.py`)**:
   - **P0 强制门禁**：对旧有启动工具（`codex`, `codex-run`, `codex-start`, `codex-reply`, `codex-reply-async`）统一加锁，无对应 Authorized Session 时严格阻断并生成审批引导，绝不直接启动 Codex。
5. **Generic Adapters (`controller/adapters/`)**:
   - `MockExecutorAdapter`：全状态流转与事件模拟，供自动化测试零 token 验证。
   - `CodexExecutorAdapter`：对接原生 Codex App Server 与 run_job。
   - `PiExecutorAdapter`：对接原生 `pi --mode rpc`，严格 JSONL 通信，动态探测。
   - `AntigravityExecutorAdapter`：对接原生 `agy.exe -p --output-format stream-json`，纯 headless。
6. **Unified MCP Tools (`controller/tools.py`)**:
   - 12 个通用 `executor_*` 工具全量注册与统一分发。
7. **MCPX 集成 (`controller/mcpx_config.py`)**:
   - 支持动态生成及写入 `~/.mcpx/.mcp.json`，完成 Upstream MCP 挂载。

---

### D. Codex Compatibility
- **原 `codex-*` MCP tools 是否仍工作？**
  **是**。所有 12 个旧工具有效保留，Schema 与返回结构完全向后兼容。
- **P0 安全拦截测试结果**：
  在 `tests/test_codex_session_gate.py` 中验证：未授权时调用 `codex-start` / `codex-run` 会被 100% 阻断，返回 `pending_approval`；授权后复用该 Session 执行，无需额外弹窗。

---

### E. Pi 适配器状态
- **Binary path**: `C:\Users\虚空之神\AppData\Roaming\npm\pi.cmd`
- **Installed version**: `@earendil-works/pi-coding-agent@0.84.4`
- **Integration mode**: Subprocess RPC (`pi --mode rpc`)，工作目录显式设定为 authorized workspace
- **Session persistence**: 本地 session 记录映射
- **Supported RPC**: `prompt`, `steer`, `abort`, `get_state`, `get_available_models`, `set_thinking_level`
- **模型调用**: 本轮测试中 **0 真实模型调用**。

---

### F. Antigravity 适配器状态
- **Binary path**: `C:\Users\虚空之神\AppData\Local\agy\bin\agy.exe`
- **Installed version**: `1.1.22`
- **Headless capabilities**: `--print`, `--output-format stream-json`, `--input-format stream-json`
- **Conversation support**: `--conversation <id>` 原生支持
- **Steer support**: Headless print mode 不支持原生 mid-turn steer，标记 `steer: False`，采用 fail-safe 记录
- **Permission mapping**: TRUSTED 动态探测并映射 `--dangerously-skip-permissions`
- **GUI Automation**: 严格禁止任何窗口点击、按键模拟或 OCR
- **模型调用**: 本轮测试中 **0 真实模型调用**。

---

### G. Approval Security
> **明确结论**：未经 Local Allow Session，是否存在启动 Codex / Pi / Antigravity 的路径？  
> **答案：No**。  
> 所有旧入口（P0 Gate）与新入口（`executor_turn_start`）均受底层 SessionStore 强校验。`executor_session_prepare` 仅生成数据库/内存待批准记录，不拉起任何进程；MCP 参数层不包含任何 `approved=true` 绕过字段。

---

### H. Long Task Control
> **明确结论**：授权一次以后，`status`、`wait`、`steer`、`cancel`、`follow-up turn` 是否还会要求本地批准？  
> **答案：No**。  
> 经 `tests/test_executor_security.py` (T4, T6) 及 `tests/test_generic_tools_e2e.py` 严格断言验证，整个长任务监督流程中无需新增任何人工确认。

---

### I. Session Revocation
- 在 `tests/test_executor_security.py` (T9) 中验证通过：
  - 调用 `executor_session_revoke` 立即标记 Session 为 `REVOKED`；
  - 触发 Adapter `dispose()` 终止底层所有关联进程树；
  - 原子释放持有的 Workspace Write Lock；
  - Capability 永久作废，后续 Turn 启动 fail-closed 拒绝。

---

### J. Workspace Lock
- 在 `tests/test_executor_security.py` (T10) 中验证通过：
  - 两个 Session 同时在同一 Workspace 启动 `BUILD` Turn；
  - 第一个 Turn 获得写锁正常运行；
  - 第二个 Turn 被 `WorkspaceLockedError` 拦截并阻断，精确报告持有锁的 session 与 job 标识。

---

### K. MCPX
- **Version**: `@kwonye/mcpx@0.1.104` (NPM registry available)
- **Endpoint**: Local STDIO process integration
- **Config Path**: `~/.mcpx/.mcp.json` (或项目级 `.mcp.json`)
- **Upstream Registration**: 已由 `controller/mcpx_config.py` 自动化支持，注入 `executor-controller` 工具集。

---

### L. Tests 完整汇总
| 测试套件 | 测试内容 | Passed | Failed | Skipped |
| :--- | :--- | :---: | :---: | :---: |
| `tests/test_executor_security.py` | 安全契约 T1 ~ T16 校验（含 Status/Result 终态无 Wait 自动同步解写锁） | 14 | 0 | 0 |
| `tests/test_codex_session_gate.py` | P0 Legacy Codex Session Gate 门禁校验 | 3 | 0 | 0 |
| `tests/test_approval_server.py` | Localhost 127.0.0.1 Approval UI & Anti-CSRF | 4 | 0 | 0 |
| `tests/test_adapters.py` | Mock / Codex / Pi / Antigravity 适配器单元测试 | 4 | 0 | 0 |
| `tests/test_generic_tools_e2e.py` | ChatGPT 监督全链路 E2E 仿真 | 1 | 0 | 0 |
| `tests/test_mcpx_registration.py` | MCPX Upstream 配置注入测试（含 --codex-bin 注入） | 1 | 0 | 0 |
| **总计** | **全套自动化测试** | **27** | **0** | **0** |

---

### M. Known Limitations
1. **MCPX Direct Write 与 Executor Write Lock 边界**：
   当前 MCPX 自身核心属于外部工具，未提供 per-workspace runtime write lock API。Controller 保证 Executor 之间的严格互斥锁（Single Writer），并在 Session 状态中对 ChatGPT 暴露写锁占用。如果 ChatGPT 在 Executor 处于 `RUNNING` 状态时绕过 Executor Controller 直接调用 MCPX 自带的 `edit` / `write` 工具，属于双写竞争。建议 ChatGPT Supervisor 遵循规则：在 Turn 运行期间仅使用 MCPX 只读工具。
2. **Antigravity Mid-turn Steer 限制**：
   当前 `1.1.22` 版本 headless print mode 暂不支持向正在运行的命令流直接注入转向指令，`steer` 标记为 recorded/unsupported，建议采用 `cancel` 当前 turn 并在同 session 发起矫正 follow-up turn。

---

### N. 明确未实现的功能（Non-goals 遵守声明）
1. 自动 Agent Router / 自动模型评选
2. Agent swarm / Agent DAG / 多 Agent 并发写同一目录
3. 新建文件系统 / 终端 / 截图运行时（由 MCPX 负责）
4. ZCode GUI 自动化
5. 24/7 反向推送到已关闭的 ChatGPT 会话
6. 重构或更换现有 Secure MCP Tunnel

---

### O. 下一轮建议工作
1. 首次由用户在 ChatGPT 端显式发起真实 Codex Session 测试。
2. 首次由用户在 ChatGPT 端显式发起真实 Pi Session 测试。
3. 首次由用户在 ChatGPT 端显式发起真实 Antigravity Session 测试。
4. 真实环境 ChatGPT → MCPX 链路挂载测试。
5. 真实长任务在实际网络下的 steer 与 cancel 验证。
