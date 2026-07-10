#!/usr/bin/env python3
"""Tests for vault schema version detection and migration."""

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


class VaultMigrationTests(unittest.TestCase):
    def run_teach_me(self, env: dict[str, str], *args: str, input_data: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(TEACH_ME_SCRIPT), *args],
            capture_output=True,
            text=True,
            env=env,
            input=input_data,
            timeout=30,
        )

    def make_env(self, tmp: str, state: dict | None = None, initialized: bool = True) -> dict[str, str]:
        home = Path(tmp) / "teach_me_home"
        home.mkdir()
        vault = home / "vault"
        vault.mkdir()
        (vault / ".teach-me").mkdir(parents=True)

        config = {
            "version": 2,
            "current_user": "default",
            "users": {
                "default": {
                    "name": "Default User",
                    "github": None,
                    "vault_path": str(vault),
                    "language": "zh",
                    "max_notes_per_phase": 3,
                    "git_sync": {"enabled": False, "remote": "", "branch": "main", "auto_sync": False},
                    "initialized": initialized,
                }
            },
        }
        (home / "config.json").write_text(json.dumps(config))

        if state is not None:
            (vault / ".teach-me" / "learning-state.json").write_text(json.dumps(state))

        env = os.environ.copy()
        env["TEACH_ME_HOME"] = str(home)
        return env

    def test_vault_version_reports_missing_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state=None)
            result = self.run_teach_me(env, "vault-version")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertIsNone(data["vault_schema_version"])
            self.assertFalse(data["needs_migration"])

    def test_vault_version_detects_legacy_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, {"version": 1, "concepts": {}})
            result = self.run_teach_me(env, "vault-version")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["vault_schema_version"], 1)
            self.assertTrue(data["needs_migration"])

    def test_migrate_adds_schema_version_and_rewrites_system_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, {"version": 1, "concepts": {}})
            result = self.run_teach_me(env, "migrate")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data["migrated"])
            self.assertEqual(data["from_version"], 1)
            self.assertEqual(data["to_version"], 1)

            state_path = Path(tmp) / "teach_me_home" / "vault" / ".teach-me" / "learning-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["vault_schema_version"], 1)

            index_path = Path(tmp) / "teach_me_home" / "vault" / "00_Index.md"
            self.assertTrue(index_path.exists())

    def test_migrate_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, {"version": 1, "concepts": {}})
            result = self.run_teach_me(env, "migrate", "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data["migrated"])
            self.assertTrue(data["dry_run"])

            state_path = Path(tmp) / "teach_me_home" / "vault" / ".teach-me" / "learning-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertNotIn("vault_schema_version", state)

    def test_migrate_already_current(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, {"version": 1, "vault_schema_version": 1, "concepts": {}})
            result = self.run_teach_me(env, "migrate")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertFalse(data["migrated"])
            self.assertEqual(data["from_version"], 1)

    def test_migrate_requires_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state=None, initialized=False)
            result = self.run_teach_me(env, "migrate")
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
