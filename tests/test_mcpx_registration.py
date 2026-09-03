# Test Suite for MCPX Upstream Configuration Registration

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, os.path.abspath("plugins/chatgpt-codex-bridge/bridge"))

from controller.mcpx_config import register_upstream_executor_controller


class McpxConfigTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="mcpx-test-"))
        self.config_path = self.temp_dir / ".mcp.json"

    def tearDown(self):
        shutil.rmtree(str(self.temp_dir), ignore_errors=True)

    def test_register_upstream_executor_controller(self):
        res = register_upstream_executor_controller(
            guard_path="D:\\cumcm\\chatgpt-codex-bridge\\plugins\\chatgpt-codex-bridge\\bridge\\codex-mcp-guard.py",
            python_bin="C:\\Python314\\python.exe",
            workspace="D:\\cumcm",
            target_path=str(self.config_path),
        )
        self.assertTrue(res["registered"])
        self.assertTrue(self.config_path.is_file())

        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertIn("mcpServers", data)
        self.assertIn("executor-controller", data["mcpServers"])
        server_cfg = data["mcpServers"]["executor-controller"]
        self.assertEqual(server_cfg["command"], "C:\\Python314\\python.exe")
        self.assertIn("codex-mcp-guard.py", server_cfg["args"][0])


if __name__ == "__main__":
    unittest.main()
