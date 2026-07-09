#!/usr/bin/env python3
"""Tests for the Teach Me Recap review skill."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECAP_SCRIPT = REPO_ROOT / "skills" / "recap" / "scripts" / "recap.py"


class RecapSkillTests(unittest.TestCase):
    def run_recap(self, env: dict[str, str], *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(RECAP_SCRIPT), *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

    def make_env(self, tmp: str, state: dict | None = None, lang: str = "zh") -> dict[str, str]:
        home = Path(tmp) / "teach_me_home"
        home.mkdir()
        vault = home / "vault"
        vault.mkdir()
        (vault / ".teach-me").mkdir(parents=True)

        config = {
            "version": 1,
            "initialized": True,
            "vault_path": str(vault),
            "language": lang,
            "max_notes_per_phase": 3,
            "git_sync": {"enabled": False, "remote": "", "branch": "main", "auto_sync": False},
        }
        (home / "config.json").write_text(json.dumps(config))

        if state is not None:
            (vault / ".teach-me" / "learning-state.json").write_text(json.dumps(state))

        env = os.environ.copy()
        env["TEACH_ME_HOME"] = str(home)
        return env

    def test_due_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, {"version": 1, "concepts": {}, "knowledge_tree": {}})
            result = self.run_recap(env, "due")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("没有到期", result.stdout)

    def test_due_lists_overdue_item(self) -> None:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        state = {
            "version": 1,
            "concepts": {
                "State Machine": {
                    "type": "concept",
                    "mastery": "seen",
                    "score": 1,
                    "next_review": yesterday,
                    "review_interval_days": 1,
                    "ease": 2.5,
                }
            },
            "knowledge_tree": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state)
            result = self.run_recap(env, "due")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("State Machine", result.stdout)

    def test_next_shows_hint(self) -> None:
        state = {
            "version": 1,
            "concepts": {
                "PDF Tree": {
                    "type": "concept",
                    "mastery": "seen",
                    "score": 1,
                    "next_review": date.today().isoformat(),
                    "review_interval_days": 1,
                    "ease": 2.5,
                    "probes": ["True or false: PDF page tree is mutable."],
                }
            },
            "knowledge_tree": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state)
            result = self.run_recap(env, "next")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PDF Tree", result.stdout)
            self.assertIn("思考题", result.stdout)

    def test_rate_good_updates_schedule(self) -> None:
        state = {
            "version": 1,
            "concepts": {
                "Mutation Intent": {
                    "type": "concept",
                    "mastery": "seen",
                    "score": 1,
                    "next_review": date.today().isoformat(),
                    "review_interval_days": 1,
                    "ease": 2.5,
                    "repetitions": 1,
                }
            },
            "knowledge_tree": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state)
            result = self.run_recap(env, "rate", "Mutation Intent", "good")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("good", result.stdout)
            self.assertIn("6", result.stdout)  # second repetition -> 6 days

            # Verify file updated
            updated = json.loads((Path(tmp) / "teach_me_home" / "vault" / ".teach-me" / "learning-state.json").read_text())
            item = updated["concepts"]["Mutation Intent"]
            self.assertEqual(item["score"], 4)
            self.assertEqual(item["mastery"], "practiced")
            self.assertEqual(item["review_interval_days"], 6)
            self.assertIn("review_history", item)

    def test_rate_again_resets(self) -> None:
        state = {
            "version": 1,
            "concepts": {
                "Hard Concept": {
                    "type": "concept",
                    "mastery": "practiced",
                    "score": 3,
                    "next_review": date.today().isoformat(),
                    "review_interval_days": 6,
                    "ease": 2.5,
                    "repetitions": 2,
                }
            },
            "knowledge_tree": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state)
            result = self.run_recap(env, "rate", "Hard Concept", "again")
            self.assertEqual(result.returncode, 0, result.stderr)

            updated = json.loads((Path(tmp) / "teach_me_home" / "vault" / ".teach-me" / "learning-state.json").read_text())
            item = updated["concepts"]["Hard Concept"]
            self.assertEqual(item["score"], 0)
            self.assertEqual(item["review_interval_days"], 1)
            self.assertEqual(item["repetitions"], 0)

    def test_stats(self) -> None:
        state = {
            "version": 1,
            "concepts": {
                "A": {"score": 1, "next_review": date.today().isoformat(), "review_interval_days": 1, "ease": 2.5},
                "B": {"score": 4, "next_review": (date.today() + timedelta(days=10)).isoformat(), "review_interval_days": 10, "ease": 2.5},
            },
            "knowledge_tree": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state)
            result = self.run_recap(env, "stats")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("2", result.stdout)
            self.assertIn("A", result.stdout)

    def test_json_output(self) -> None:
        state = {
            "version": 1,
            "concepts": {
                "JSON Test": {"score": 1, "next_review": date.today().isoformat(), "review_interval_days": 1, "ease": 2.5}
            },
            "knowledge_tree": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state, lang="en")
            result = self.run_recap(env, "next", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["name"], "JSON Test")
            self.assertIn("hint", data)


if __name__ == "__main__":
    unittest.main()
