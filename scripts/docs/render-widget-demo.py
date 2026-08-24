#!/usr/bin/env python3
"""Render the shipped MCP Apps widget with synthetic README demo data."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


STATES = {
    "running": {
        "jobId": "demo-job-0001",
        "status": "running",
        "content": "",
    },
    "completed": {
        "jobId": "demo-job-0002",
        "status": "completed",
        "content": "演示项目已完成。测试 24/24 通过；未执行部署。",
    },
    "interrupted": {
        "jobId": "demo-job-0003",
        "status": "interrupted",
        "content": "演示任务已中断；结果仍保存在本机，可从原 Job 恢复。",
    },
}


def load_widget_html(repo_root: Path) -> str:
    guard_path = repo_root / "scripts" / "bridge" / "codex-mcp-guard.py"
    tree = ast.parse(guard_path.read_text(encoding="utf-8"), filename=str(guard_path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "WIDGET_HTML" for target in node.targets):
            value = ast.literal_eval(node.value)
            if isinstance(value, str):
                return value
    raise RuntimeError(f"WIDGET_HTML not found in {guard_path}")


def render(widget_html: str, state: dict[str, str]) -> str:
    host = {
        "toolOutput": state,
        "toolResponseMetadata": {},
        "widgetState": {},
    }
    bootstrap = f"""
  <script>
    window.openai = {json.dumps(host, ensure_ascii=False)};
    window.openai.setWidgetState = () => {{}};
    window.openai.sendFollowUpMessage = async () => {{}};
    window.openai.callTool = async () => window.openai.toolOutput;
  </script>
"""
    badge = """
  <div class="demo-badge" aria-label="Synthetic demonstration data">
    DEMO · SYNTHETIC DATA
  </div>
"""
    demo_style = """
  <style>
    html { background: #f4f4f2; }
    body { max-width: 720px; margin: 0 auto; padding: 44px 28px 34px; }
    .demo-badge {
      display: inline-block; margin: 0 0 12px 2px; padding: 5px 9px;
      border-radius: 999px; background: #e6f4ed; color: #17633a;
      font: 700 11px/1.2 -apple-system, BlinkMacSystemFont, sans-serif;
      letter-spacing: .08em;
    }
    .card { background: #fff; box-shadow: 0 10px 32px rgba(0,0,0,.07); }
    @media (prefers-color-scheme: dark) {
      html { background: #191918; }
      .card { background: #242422; }
    }
  </style>
"""
    return (
        widget_html.replace("</head>", demo_style + "</head>")
        .replace("<body>", "<body>" + badge + bootstrap, 1)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", choices=sorted(STATES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    html = render(load_widget_html(repo_root), STATES[args.state])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
