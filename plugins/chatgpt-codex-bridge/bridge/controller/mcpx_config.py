# MCPX Integration Helper
# Configures and registers Executor Controller as an Upstream MCP Server in ~/.mcpx/.mcp.json.

import json
import os
import sys
from pathlib import Path


def get_mcpx_config_dir():
    home = Path.home()
    primary = home / ".mcpx"
    if primary.is_dir():
        return primary
    fallback = home / ".config" / "mcpx"
    if fallback.is_dir():
        return fallback
    # Default to ~/.mcpx
    return primary


def get_mcpx_config_path():
    cfg_dir = get_mcpx_config_dir()
    jsonc_path = cfg_dir / "mcp.jsonc"
    if jsonc_path.is_file():
        return jsonc_path
    return cfg_dir / ".mcp.json"


import shutil


def find_codex_bin():
    candidate = shutil.which("codex") or shutil.which("codex.cmd") or shutil.which("codex.exe")
    if candidate:
        return candidate
    npm_bin = Path(os.environ.get("APPDATA", "")) / "npm" / "codex.cmd"
    if npm_bin.is_file():
        return str(npm_bin)
    return ""


def register_upstream_executor_controller(
    guard_path,
    python_bin=None,
    workspace=None,
    codex_bin=None,
    server_name="executor-controller",
    target_path=None,
):
    config_path = Path(target_path) if target_path else get_mcpx_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if config_path.is_file():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            config = {}

    if "mcpServers" not in config or not isinstance(config["mcpServers"], dict):
        config["mcpServers"] = {}

    py = python_bin or sys.executable
    ws = workspace or os.getcwd()
    cmd_args = [str(guard_path), "--workspace", str(ws)]

    actual_codex = codex_bin or find_codex_bin()
    if actual_codex:
        cmd_args.extend(["--codex-bin", str(actual_codex), "--desktop-open-bin", str(actual_codex)])

    config["mcpServers"][server_name] = {
        "command": str(py),
        "args": cmd_args,
        "env": {
            "PYTHONUNBUFFERED": "1",
        },
    }

    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return {
        "config_path": str(config_path),
        "server_name": server_name,
        "registered": True,
    }

