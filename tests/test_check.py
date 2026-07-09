#!/usr/bin/env python3
"""Tests for the Teach Me Check diagnostic skill."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
CHECK_SCRIPT = REPO_ROOT / "skills" / "check" / "scripts" / "check_me.py"
TEACH_ME_SCRIPT = REPO_ROOT / "skills" / "teach-me" / "scripts" / "teach_me.py"


class CheckSkillTests(unittest.TestCase):
    def run_check(self, env: dict[str, str], *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

    def test_report_shows_not_installed_when_no_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "teach_me_home"
            home.mkdir()
            env = os.environ.copy()
            env["TEACH_ME_HOME"] = str(home)
            # Ensure no agent home dirs are detected
            env["HOME"] = tmp

            result = self.run_check(env, "report")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("还没有安装", result.stdout)

    def test_report_with_vault_in_natural_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "teach_me_home"
            home.mkdir()
            vault = home / "vault"
            vault.mkdir()
            (vault / "02_Concepts").mkdir(parents=True)
            (vault / "02_Concepts" / "test.md").write_text("# Test")
            (vault / ".teach-me").mkdir()
            (vault / ".teach-me" / "events.jsonl").write_text(
                json.dumps({"type": "tool", "score": 3}) + "\n"
            )
            config = {
                "version": 1,
                "initialized": True,
                "vault_path": str(vault),
                "language": "zh",
                "max_notes_per_phase": 3,
                "git_sync": {
                    "enabled": False,
                    "remote": "",
                    "branch": "main",
                    "auto_sync": False,
                },
            }
            (home / "config.json").write_text(json.dumps(config))

            # Create fake hook detection targets inside temp HOME
            fake_home = Path(tmp)
            (fake_home / ".codex").mkdir()
            (fake_home / ".codex" / "config.toml").write_text("")

            env = os.environ.copy()
            env["TEACH_ME_HOME"] = str(home)
            env["HOME"] = fake_home

            result = self.run_check(env, "report")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Teach Me 状态检查", result.stdout)
            self.assertIn("概念笔记：", result.stdout)
            self.assertIn("你可以这样说", result.stdout)

    def test_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "teach_me_home"
            home.mkdir()
            config = {
                "version": 1,
                "initialized": True,
                "vault_path": str(home / "vault"),
                "language": "en",
                "max_notes_per_phase": 5,
                "git_sync": {
                    "enabled": True,
                    "remote": "git@github.com:user/repo.git",
                    "branch": "main",
                    "auto_sync": True,
                },
            }
            (home / "config.json").write_text(json.dumps(config))
            (home / "vault").mkdir()

            env = os.environ.copy()
            env["TEACH_ME_HOME"] = str(home)

            result = self.run_check(env, "report", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["config"]["raw_language"], "en")
            self.assertEqual(data["config"]["max_notes_per_phase"], 5)
            self.assertTrue(data["git_sync"]["enabled"])
            self.assertTrue(data["git_sync"]["auto_sync"])
            self.assertEqual(data["git_sync"]["remote"], "git@github.com:user/repo.git")

    def test_english_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "teach_me_home"
            home.mkdir()
            config = {
                "version": 1,
                "initialized": False,
                "vault_path": str(home / "vault"),
                "language": "en",
                "max_notes_per_phase": 3,
                "git_sync": {"enabled": False, "remote": "", "branch": "main", "auto_sync": False},
            }
            (home / "config.json").write_text(json.dumps(config))

            # Create fake hook detection targets inside temp HOME
            fake_home = Path(tmp)
            (fake_home / ".codex").mkdir()
            (fake_home / ".codex" / "config.toml").write_text("")

            env = os.environ.copy()
            env["TEACH_ME_HOME"] = str(home)
            env["HOME"] = str(fake_home)

            result = self.run_check(env, "report")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Teach Me status check", result.stdout)
            self.assertIn("Vault path", result.stdout)
            self.assertIn("You can say", result.stdout)

    def test_manual_command(self) -> None:
        env = os.environ.copy()
        result = self.run_check(env, "manual")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("操作手册", result.stdout)

    def test_profile_add_and_switch_user(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "teach_me_home"
            home.mkdir()
            config = {
                "version": 2,
                "current_user": "default",
                "users": {
                    "default": {
                        "name": "Default User",
                        "github": None,
                        "vault_path": str(home / "vault"),
                        "language": "auto",
                        "max_notes_per_phase": 3,
                        "git_sync": {"enabled": False, "remote": "", "branch": "main", "auto_sync": False},
                        "initialized": True,
                    }
                },
            }
            (home / "config.json").write_text(json.dumps(config))
            env = os.environ.copy()
            env["TEACH_ME_HOME"] = str(home)

            add = self.run_check(env, "profile", "--add", "alice", "--name", "Alice", "--github", "alice")
            self.assertEqual(add.returncode, 0, add.stderr)
            self.assertIn("Added user 'alice'", add.stdout)

            switch = self.run_check(env, "profile", "--switch", "alice")
            self.assertEqual(switch.returncode, 0, switch.stderr)
            self.assertIn("Switched to user 'alice'", switch.stdout)

            report = self.run_check(env, "report", "--json")
            data = json.loads(report.stdout)
            self.assertEqual(data["user"]["id"], "alice")
            self.assertEqual(data["user"]["name"], "Alice")
            self.assertEqual(data["user"]["github"], "alice")

    def test_style_show_and_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "teach_me_home"
            home.mkdir()
            vault = home / "vault"
            vault.mkdir()
            (vault / ".teach-me").mkdir()
            config = {
                "version": 2,
                "current_user": "default",
                "users": {
                    "default": {
                        "name": "Default User",
                        "github": None,
                        "vault_path": str(vault),
                        "language": "auto",
                        "max_notes_per_phase": 3,
                        "git_sync": {"enabled": False, "remote": "", "branch": "main", "auto_sync": False},
                        "initialized": True,
                    }
                },
            }
            (home / "config.json").write_text(json.dumps(config))
            env = os.environ.copy()
            env["TEACH_ME_HOME"] = str(home)

            set_result = self.run_check(env, "style", "--set", "speaking_style", "friendly coach")
            self.assertEqual(set_result.returncode, 0, set_result.stderr)
            self.assertIn("Updated speaking_style", set_result.stdout)

            show = self.run_check(env, "style")
            self.assertEqual(show.returncode, 0, show.stderr)
            self.assertIn("friendly coach", show.stdout)


if __name__ == "__main__":
    unittest.main()
