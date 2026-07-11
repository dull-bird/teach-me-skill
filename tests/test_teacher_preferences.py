from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEACH_ME = ROOT / "skills" / "teach-me" / "scripts" / "teach_me.py"


class TeacherPreferenceTests(unittest.TestCase):
    def run_cli(
        self, home: Path, *args: str, input_data: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["TEACH_ME_HOME"] = str(home)
        return subprocess.run(
            [sys.executable, str(TEACH_ME), *args],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            input=input_data,
            timeout=30,
        )

    def read_style(self, home: Path) -> dict:
        path = home / "vault" / ".teach-me" / "style-profile.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_default_choice_completes_initialization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            result = self.run_cli(home, "configure", "--teacher-style", "default", "--knowledge-focus", "balanced")
            config = json.loads((home / "config.json").read_text(encoding="utf-8"))
            style = self.read_style(home)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(config["users"]["default"]["initialized"])
        self.assertTrue(style["profile_initialized"])
        self.assertEqual(style["teacher_profile"], "default")
        self.assertEqual(style["knowledge_focus"], "balanced")

    def test_coach_profile_prioritizes_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            result = self.run_cli(home, "configure", "--teacher-style", "coach")
            style = self.read_style(home)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(style["teacher_profile"], "coach")
        self.assertEqual(style["knowledge_focus"], "implementation")
        self.assertIn("engineering coach", style["teach_me_persona"])

    def test_custom_teacher_style_and_general_focus(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            result = self.run_cli(
                home,
                "configure",
                "--teacher-style",
                "custom",
                "--custom-teacher-style",
                "先给结论，再用类比解释",
                "--knowledge-focus",
                "general",
            )
            style = self.read_style(home)
            context = self.run_cli(home, "context", "--full")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(style["teacher_profile"], "custom")
        self.assertEqual(style["knowledge_focus"], "general")
        self.assertEqual(style["teach_me_persona"], "先给结论，再用类比解释")
        self.assertIn("knowledge focus: general", context.stdout)

    def test_legacy_style_profile_requires_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.run_cli(home, "configure")
            style_path = home / "vault" / ".teach-me" / "style-profile.json"
            style = json.loads(style_path.read_text(encoding="utf-8"))
            style.pop("profile_initialized", None)
            style_path.write_text(json.dumps(style), encoding="utf-8")
            context = self.run_cli(home, "context")
            status = self.run_cli(home, "status")
        self.assertIn("teaching profile initialized: false", context.stdout)
        self.assertFalse(json.loads(status.stdout)["teaching_profile_initialized"])

    def test_capture_persists_domain_and_stable_project_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.run_cli(home, "configure", "--teacher-style", "default")
            project_path = "/work/teach-me-skill"
            first = {
                "project": {"name": "Teach Me", "path": project_path},
                "knowledge_domain": "AI",
                "items": [{"title": "Agent hooks", "type": "concept", "mastery": "seen"}],
            }
            second = {
                "project": {"name": "Teach Me Skill", "path": project_path},
                "knowledge_domain": "AI",
                "items": [{"title": "Agent hooks", "type": "concept", "mastery": "explained"}],
            }
            self.run_cli(home, "capture", input_data=json.dumps(first))
            result = self.run_cli(home, "capture", input_data=json.dumps(second))
            state = json.loads(
                (home / "vault" / ".teach-me" / "learning-state.json").read_text(encoding="utf-8")
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        concept = state["concepts"]["Agent hooks"]
        self.assertEqual(concept["knowledge_domain"], "AI")
        self.assertEqual(concept["project_refs"], [{"id": "path:/work/teach-me-skill", "name": "Teach Me Skill"}])


if __name__ == "__main__":
    unittest.main()
