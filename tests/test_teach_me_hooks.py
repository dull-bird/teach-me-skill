#!/usr/bin/env python3
"""Tests for the Teach Me hooks enable/disable command."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
TEACH_ME_SCRIPT = REPO_ROOT / "skills" / "teach-me" / "scripts" / "teach_me.py"


class TeachMeHooksTests(unittest.TestCase):
    def run_teach_me(self, env: dict[str, str], *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(TEACH_ME_SCRIPT), *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

    def make_env(self, tmp: str) -> dict[str, str]:
        home = Path(tmp) / "home"
        home.mkdir()
        teach_me_home = Path(tmp) / "teach_me_home"
        teach_me_home.mkdir()

        env = os.environ.copy()
        env["HOME"] = str(home)
        env["TEACH_ME_HOME"] = str(teach_me_home)
        return env

    def test_hooks_no_flag_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp)
            result = self.run_teach_me(env, "hooks")
            self.assertEqual(result.returncode, 1)
            self.assertIn("--enable or --disable", result.stderr)

    def test_hooks_enable_reports_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp)
            home = Path(tmp) / "home"
            # Create agent home dirs so they are detected.
            (home / ".claude").mkdir()
            (home / ".codex").mkdir()
            (home / ".kimi").mkdir()

            result = self.run_teach_me(env, "hooks", "--enable", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data["enabled"])
            agents = {r["agent"]: r for r in data["results"]}
            self.assertIn("claude-code", agents)
            self.assertIn("codex", agents)
            self.assertIn("kimi", agents)
            self.assertIn("openclaw", agents)

            # The real installers should have created/modified config files.
            self.assertTrue((home / ".claude" / "settings.json").exists())
            self.assertTrue((home / ".codex" / "config.toml").exists())
            self.assertTrue((home / ".kimi" / "config.toml").exists())

            settings = json.loads((home / ".claude" / "settings.json").read_text())
            self.assertIn("teach-me/scripts/teach_me_hook.py", json.dumps(settings))

    def test_hooks_disable_uninstalls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp)
            home = Path(tmp) / "home"
            (home / ".claude").mkdir()
            (home / ".codex").mkdir()
            (home / ".kimi").mkdir()

            # Enable first.
            self.run_teach_me(env, "hooks", "--enable")
            # Then disable.
            result = self.run_teach_me(env, "hooks", "--disable", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertFalse(data["enabled"])

            # Claude Code settings should no longer contain the hook.
            settings = json.loads((home / ".claude" / "settings.json").read_text())
            self.assertNotIn("teach-me/scripts/teach_me_hook.py", json.dumps(settings))


if __name__ == "__main__":
    unittest.main()
