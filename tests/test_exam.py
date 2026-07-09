#!/usr/bin/env python3
"""Tests for the Teach Me Exam skill."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
EXAM_SCRIPT = REPO_ROOT / "skills" / "exam" / "scripts" / "exam.py"


class ExamSkillTests(unittest.TestCase):
    def run_exam(self, env: dict[str, str], *args: str, input_data: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(EXAM_SCRIPT), *args],
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

    def test_plan_empty_state(self) -> None:
        state = {"version": 1, "concepts": {}, "knowledge_tree": {}}
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state)
            result = self.run_exam(env, "plan", "--time", "15")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("考试计划", result.stdout)

    def test_plan_selects_weakest_concepts(self) -> None:
        state = {
            "version": 1,
            "concepts": {
                "Alpha": {"mastery": "confident", "score": 5, "last_seen": "2026-07-01T00:00:00"},
                "Beta": {"mastery": "unknown", "score": 0},
                "Gamma": {"mastery": "seen", "score": 1},
                "Delta": {"mastery": "explained", "score": 2},
                "Epsilon": {"mastery": "seen", "score": 1},
                "Zeta": {"mastery": "unknown", "score": 0},
                "Eta": {"mastery": "practiced", "score": 3},
                "Theta": {"mastery": "seen", "score": 1},
            },
            "knowledge_tree": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state)
            result = self.run_exam(env, "plan", "--time", "15", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(result.stdout)
            names = [c["name"] for c in plan["concepts"]]
            self.assertIn("Beta", names)
            self.assertIn("Gamma", names)
            self.assertNotIn("Alpha", names)

    def test_plan_filters_by_topic(self) -> None:
        state = {
            "version": 1,
            "concepts": {
                "Python decorator": {"mastery": "seen", "score": 1, "projects": ["py"]},
                "Rust lifetime": {"mastery": "unknown", "score": 0, "projects": ["rs"]},
            },
            "knowledge_tree": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state)
            result = self.run_exam(env, "plan", "--time", "15", "--topic", "Python", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(result.stdout)
            names = [c["name"] for c in plan["concepts"]]
            self.assertIn("Python decorator", names)
            self.assertNotIn("Rust lifetime", names)

    def test_plan_respects_formats(self) -> None:
        state = {
            "version": 1,
            "concepts": {
                "Python decorator": {"mastery": "seen", "score": 1},
                "Rust lifetime": {"mastery": "unknown", "score": 0},
            },
            "knowledge_tree": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state)
            result = self.run_exam(env, "plan", "--time", "60", "--formats", "mcq,coding", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(result.stdout)
            self.assertEqual(plan["type"], "exam")
            self.assertEqual(set(plan["formats"]), {"mcq", "coding"})
            for c in plan["concepts"]:
                self.assertIn(c["format"], {"mcq", "coding"})

    def test_grade_updates_mastery(self) -> None:
        state = {
            "version": 1,
            "concepts": {
                "Decorator": {"mastery": "seen", "score": 1},
            },
            "knowledge_tree": {},
        }
        payload = {
            "plan": {"session_id": "exam-test-001", "type": "test", "time_budget_minutes": 15},
            "results": [
                {"name": "Decorator", "format": "short", "correct": True, "confidence": 0.9}
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state)
            result = self.run_exam(env, "grade", input_data=json.dumps(payload))
            self.assertEqual(result.returncode, 0, result.stderr)

            updated = json.loads((Path(tmp) / "teach_me_home" / "vault" / ".teach-me" / "learning-state.json").read_text())
            self.assertEqual(updated["concepts"]["Decorator"]["mastery"], "explained")
            self.assertEqual(len(updated["exams"]), 1)

    def test_grade_records_exam_summary(self) -> None:
        state = {
            "version": 1,
            "concepts": {
                "A": {"mastery": "seen", "score": 1},
                "B": {"mastery": "seen", "score": 1},
            },
            "knowledge_tree": {},
        }
        payload = {
            "plan": {"session_id": "exam-test-002", "type": "quiz"},
            "results": [
                {"name": "A", "format": "mcq", "correct": True, "confidence": 0.9},
                {"name": "B", "format": "tf", "correct": False, "confidence": 0.5},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state)
            result = self.run_exam(env, "grade", "--json", input_data=json.dumps(payload))
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(result.stdout)
            self.assertEqual(record["summary"]["total"], 2)
            self.assertEqual(record["summary"]["correct"], 1)
            self.assertEqual(record["summary"]["accuracy"], 0.5)

    def test_history_and_stats(self) -> None:
        state = {
            "version": 1,
            "concepts": {
                "A": {"mastery": "seen", "score": 1},
            },
            "knowledge_tree": {},
            "exams": [
                {
                    "session_id": "old-1",
                    "timestamp": "2026-07-08T10:00:00",
                    "type": "quiz",
                    "summary": {"total": 2, "correct": 2, "accuracy": 1.0},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state)
            history = self.run_exam(env, "history", "--json")
            self.assertEqual(history.returncode, 0, history.stderr)
            self.assertEqual(len(json.loads(history.stdout)), 1)

            stats = self.run_exam(env, "stats", "--json")
            self.assertEqual(stats.returncode, 0, stats.stderr)
            data = json.loads(stats.stdout)
            self.assertEqual(data["total_sessions"], 1)
            self.assertEqual(data["total_correct"], 2)

    def test_topics(self) -> None:
        state = {
            "version": 1,
            "concepts": {
                "Python": {"mastery": "seen", "score": 1, "projects": ["py"]},
            },
            "knowledge_tree": {
                "Decorator": {"mastery": "unknown", "score": 0},
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp, state)
            result = self.run_exam(env, "topics", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            topics = json.loads(result.stdout)
            self.assertIn("Python", topics)
            self.assertIn("Decorator", topics)
            self.assertIn("py", topics)

    def test_user_specific_vault(self) -> None:
        state = {
            "version": 1,
            "concepts": {
                "Alice Topic": {"mastery": "unknown", "score": 0},
            },
            "knowledge_tree": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "teach_me_home"
            home.mkdir()
            default_vault = home / "vault"
            default_vault.mkdir()
            alice_vault = home / "users" / "alice" / "vault"
            alice_vault.mkdir(parents=True)
            (alice_vault / ".teach-me").mkdir(parents=True)
            (alice_vault / ".teach-me" / "learning-state.json").write_text(json.dumps(state))

            config = {
                "version": 2,
                "current_user": "default",
                "users": {
                    "default": {
                        "name": "Default User",
                        "github": None,
                        "vault_path": str(default_vault),
                        "language": "auto",
                        "max_notes_per_phase": 3,
                        "git_sync": {"enabled": False, "remote": "", "branch": "main", "auto_sync": False},
                        "initialized": True,
                    },
                    "alice": {
                        "name": "Alice",
                        "github": None,
                        "vault_path": str(alice_vault),
                        "language": "auto",
                        "max_notes_per_phase": 3,
                        "git_sync": {"enabled": False, "remote": "", "branch": "main", "auto_sync": False},
                        "initialized": True,
                    },
                },
            }
            (home / "config.json").write_text(json.dumps(config))

            env = os.environ.copy()
            env["TEACH_ME_HOME"] = str(home)

            result = self.run_exam(env, "plan", "--time", "15", "--user", "alice", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(result.stdout)
            self.assertEqual(plan["user"], "alice")
            self.assertEqual(plan["concepts"][0]["name"], "Alice Topic")


if __name__ == "__main__":
    unittest.main()
