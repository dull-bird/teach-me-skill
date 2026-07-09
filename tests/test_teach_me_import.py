#!/usr/bin/env python3
"""Tests for the Teach Me import command."""

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


class TeachMeImportTests(unittest.TestCase):
    def run_teach_me(self, env: dict[str, str], *args: str, input_data: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(TEACH_ME_SCRIPT), *args],
            capture_output=True,
            text=True,
            env=env,
            input=input_data,
            timeout=30,
        )

    def make_env(self, tmp: str, state: dict | None = None, lang: str = "zh") -> dict[str, str]:
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
                    "language": lang,
                    "max_notes_per_phase": 3,
                    "git_sync": {"enabled": False, "remote": "", "branch": "main", "auto_sync": False},
                    "initialized": True,
                }
            },
        }
        (home / "config.json").write_text(json.dumps(config))

        if state is not None:
            (vault / ".teach-me" / "learning-state.json").write_text(json.dumps(state))

        env = os.environ.copy()
        env["TEACH_ME_HOME"] = str(home)
        return env

    def test_import_text_creates_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, {"version": 1})
            text_file = Path(tmp) / "article.md"
            text_file.write_text("# Event Sourcing\n\nStores state as a sequence of events.", encoding="utf-8")

            result = self.run_teach_me(
                env,
                "import",
                "--source", "text",
                "--path", str(text_file),
                "--project", "Blog",
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            data = json.loads(result.stdout)
            self.assertEqual(data["source_type"], "text")
            self.assertEqual(data["project"], "Blog")
            self.assertEqual(data["status"], "ok")
            self.assertGreater(data["extracted_length"], 0)

            state = json.loads((Path(tmp) / "teach_me_home" / "vault" / ".teach-me" / "learning-state.json").read_text())
            self.assertEqual(len(state["imports"]), 1)
            self.assertEqual(state["imports"][0]["source_type"], "text")

    def test_import_stdin_creates_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, {"version": 1})
            result = self.run_teach_me(
                env,
                "import",
                "--source", "stdin",
                "--project", "Chat",
                "--json",
                input_data="CQRS separates read and write models.",
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            data = json.loads(result.stdout)
            self.assertEqual(data["source_type"], "stdin")
            self.assertEqual(data["status"], "ok")

            state = json.loads((Path(tmp) / "teach_me_home" / "vault" / ".teach-me" / "learning-state.json").read_text())
            self.assertEqual(len(state["imports"]), 1)

    def test_import_missing_path_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, {"version": 1})
            result = self.run_teach_me(
                env,
                "import",
                "--source", "text",
                "--json",
            )
            self.assertEqual(result.returncode, 1, result.stderr)

    def test_import_unreadable_records_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, {"version": 1})
            result = self.run_teach_me(
                env,
                "import",
                "--source", "text",
                "--path", "/nonexistent/file.pdf",
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            data = json.loads(result.stdout)
            self.assertEqual(data["status"], "unreadable")

            state = json.loads((Path(tmp) / "teach_me_home" / "vault" / ".teach-me" / "learning-state.json").read_text())
            self.assertEqual(state["imports"][0]["status"], "unreadable")

    def test_import_auto_detects_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, {"version": 1})
            text_file = Path(tmp) / "notes.txt"
            text_file.write_text("Some notes about agents.", encoding="utf-8")

            result = self.run_teach_me(
                env,
                "import",
                "--source", "auto",
                "--path", str(text_file),
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["detected_type"], "text")
            self.assertEqual(data["status"], "ok")

    def test_import_obsidian_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, {"version": 1})
            obsidian = Path(tmp) / "obsidian-vault"
            (obsidian / "Projects").mkdir(parents=True)
            (obsidian / "Projects" / "web-ui.md").write_text("# Web UI\n\nReactive state lifts UI updates.", encoding="utf-8")
            (obsidian / "Readings").mkdir(parents=True)
            (obsidian / "Readings" / "event-sourcing.md").write_text("# Event Sourcing\n\nStores state as events.", encoding="utf-8")

            result = self.run_teach_me(
                env,
                "import",
                "--source", "obsidian",
                "--path", str(obsidian),
                "--project", "My Obsidian",
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["source_type"], "obsidian")
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["note_count"], 2)
            self.assertIn("Projects/web-ui.md", data["note_paths"])
            self.assertGreater(data["extracted_length"], 0)

            state = json.loads((Path(tmp) / "teach_me_home" / "vault" / ".teach-me" / "learning-state.json").read_text())
            self.assertEqual(len(state["imports"]), 1)
            self.assertEqual(state["imports"][0]["source_type"], "obsidian")

    def test_import_obsidian_skips_system_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, {"version": 1})
            obsidian = Path(tmp) / "obsidian-vault"
            (obsidian / ".obsidian").mkdir(parents=True)
            (obsidian / ".teach-me").mkdir(parents=True)
            (obsidian / ".trash").mkdir(parents=True)
            (obsidian / ".obsidian" / "appearance.md").write_text("# Appearance\n\nSkipped.", encoding="utf-8")
            (obsidian / ".teach-me" / "note.md").write_text("# State\n\nSkipped.", encoding="utf-8")
            (obsidian / ".trash" / "deleted.md").write_text("# Deleted\n\nSkipped.", encoding="utf-8")
            (obsidian / "real-note.md").write_text("# Real Note\n\nContent.", encoding="utf-8")

            result = self.run_teach_me(
                env,
                "import",
                "--source", "obsidian",
                "--path", str(obsidian),
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["note_count"], 1)
            self.assertEqual(data["skipped_count"], 3)

    def test_import_obsidian_self_import_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
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
                        "initialized": True,
                    }
                },
            }
            (home / "config.json").write_text(json.dumps(config))
            (vault / "note.md").write_text("# Note\n\nText.", encoding="utf-8")

            env = os.environ.copy()
            env["TEACH_ME_HOME"] = str(home)

            result = self.run_teach_me(
                env,
                "import",
                "--source", "obsidian",
                "--path", str(vault),
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["status"], "self_import")
            self.assertEqual(data["extracted_length"], 0)


if __name__ == "__main__":
    unittest.main()
