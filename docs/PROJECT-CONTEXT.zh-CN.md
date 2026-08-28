# 项目背景速览（给新会话 / ChatGPT）

> 本文件是给新对话快速对齐用的。细节以 `docs/specs/` 与 `docs/adr/` 为准，此处只讲现状。

## 这是什么项目

`chatgpt-codex-bridge`：让 **ChatGPT Pro 当主管、本机 AI CLI 当执行者**的桥。
链路：ChatGPT 对话 → OpenAI Secure MCP Tunnel → 本机 Guard（stdio MCP）→ 执行后端 → 仓库/命令/测试。

分工铁律（不可违反）：
- **ChatGPT**：理解目标、发现仓库/历史会话、分派任务、steer/cancel、审查结果。规划权只在 ChatGPT。
- **Bridge/Guard**：只做传输边界、安全边界（HMAC 能力签名）、持久任务（durable job）、观察面（transcript/report）、受限生命周期控制。**不得**变成第二个自主 agent / 调度器 / 工作流引擎。
- **执行后端**：真正读改代码、跑命令跑测试、返回结果。

核心机制：durable job（request/status/controls/worker 四文件、single-writer）、有界 wait（默认 52s/上限 55s）、同回合 steer、按 job 取消（canonical 中断 → 短 grace → 已验证归属才杀进程树，宁可失败不误杀）、签名 capability（`cgb2.*`）、Windows Tunnel 生命周期（install/doctor/status/restart/stop/uninstall，含退出自愈重试，ADR-0018）。

## 当前状态（2026-08-28）

**ZCode 执行后端移植已完成**（版本 `0.7.0+zcode.20260828234419`）：

- 安装器 `-Provider {codex,zcode}`，一次安装只服务一个后端，工具名带前缀（`codex-*` / `zcode-*`）。
- zcode 后端驱动 ZCode 桌面 CLI 自带的 `app-server --stdio` 协议（`ZCode.exe resources\glm\zcode.cjs`，`ELECTRON_RUN_AS_NODE=1`）——与 Codex 的 app-server 同构，协议到协议适配，没有套壳。
- steer = 运行中 `session/send`（ZCode 原生同回合输入，有 `turn.steerQueued/Drained` 事件）；cancel = `session/stop` → 短 grace → 既有已验证 worker 兜底。
- 预设真实映射：`personal-full-control` = yolo；`workspace-safe` = build + Bridge 一律拒绝权限请求（无人在侧，默认拒绝）。
- 同步短任务工具（`zcode`/`zcode-reply`）= app-server 短生命周期会话实现；不使用未验证的 `--prompt` headless 模式。
- 测试：Codex 契约 60 项 + ZCode 契约 12 项（FAKE_ZCODE 模拟协议）全绿，均已接入 CI；Windows PowerShell 5.1 套件（含中文路径、zcode 安装正/负路径）通过。

## 关键决策（详见 docs/adr/）

- **ADR-0018**：Windows Tunnel 意外退出后 5 秒有界重试，单一 bridge-owned 进程树，不引入第二个监督进程。
- **ADR-0019**：provider 接缝——provider 只存在于 1 个 client 类 + 6 个编排函数 + preset 映射 + 测试 fake + CLI 参数；JobStore/签名/controls/取消兜底/进程归属/Tunnel 生命周期全部后端无关。未来加新执行后端（如 dsh）只需新增这些点，前提是有可编程执行接口；能力缺失就诚实降级，不伪造。

## 唯一待办

**真实凭证端到端验证**：headless 运行需要 `~/.zcode/cli/config.json`（ZCode CLI 登录产物；桌面端不受影响）。步骤：
1. 完成 ZCode CLI 登录，生成该文件；
2. `install -Provider zcode -ZCodeBin D:\ZCode\ZCode.exe ...`（安装器会校验该文件，缺失即 fail closed）；
3. 从 ChatGPT 对话发 `zcode-run` 任务，按 `docs/specs/zcode-port/requirements.md` §9 验收。

## 去哪看

- 移植规格（需求/设计/任务清单）：`docs/specs/zcode-port/`
- 协议事实与验证记录：`docs/specs/zcode-port/design.md` §1、§3
- ZCode 测试：`tests/bridge/test-zcode-mcp-guard.py`；CI：`.github/workflows/ci.yml`
- 关键提交：`aaa3cb2`（适配器核心）、`944340e`（测试）、`123cb99`（Windows 安装）
