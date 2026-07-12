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


class GoalSummaryTests(unittest.TestCase):
    def run_cli(self, home: Path, *args: str, input_data: str | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["TEACH_ME_HOME"] = str(home)
        return subprocess.run(
            [sys.executable, str(TEACH_ME), *args],
            cwd=ROOT,
            env=env,
            text=True,
            input=input_data,
            capture_output=True,
            timeout=30,
        )

    def configure(self, home: Path) -> None:
        result = self.run_cli(home, "configure", "--teacher-style", "theorist")
        self.assertEqual(result.returncode, 0, result.stderr)

    def log_tool(self, home: Path, command: str, *, cwd: str = "/repo/demo", timestamp: str | None = None) -> None:
        payload = {
            "phase": "post",
            "cwd": cwd,
            "tool_name": "Bash",
            "command": command,
            "score": 3,
            "signal_tags": ["modification", "verification"],
        }
        if timestamp:
            payload["timestamp"] = timestamp
        result = self.run_cli(
            home,
            "log-event",
            "--type",
            "tool",
            input_data=json.dumps(payload),
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_goal_complete_returns_project_summary_contract_with_five_points(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.configure(home)
            start = self.run_cli(
                home, "goal", "start", "--id", "goal-1", "--project-name", "Demo", "--project-path", "/repo/demo"
            )
            self.log_tool(home, "edit parser.py and run tests")
            self.log_tool(home, "run integration tests")
            complete = self.run_cli(home, "goal", "complete", "--id", "goal-1")

        self.assertEqual(start.returncode, 0, start.stderr)
        self.assertEqual(complete.returncode, 0, complete.stderr)
        data = json.loads(complete.stdout)
        self.assertEqual(data["status"], "ready")
        self.assertEqual(data["summary_contract"]["knowledge_point_count"], 5)
        self.assertIn("one coherent paragraph", data["prompt_for_ai"])
        self.assertIn("exactly 5", data["prompt_for_ai"])
        self.assertIn("[项目：Demo]", data["prompt_for_ai"])

    def test_quiet_window_is_only_a_non_scheduled_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.configure(home)
            self.run_cli(home, "goal", "start", "--id", "goal-quiet", "--quiet-window-minutes", "15")
            self.log_tool(home, "run test suite", cwd="")
            waiting = self.run_cli(home, "goal", "summary", "--id", "goal-quiet")
            forced = self.run_cli(home, "goal", "summary", "--id", "goal-quiet", "--force")

        self.assertEqual(json.loads(waiting.stdout)["status"], "waiting_for_quiet_window")
        self.assertEqual(json.loads(forced.stdout)["status"], "ready")

    def test_manual_recent_summary_works_without_an_active_goal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.configure(home)
            self.log_tool(home, "edit migration.py and verify output")
            result = self.run_cli(home, "goal", "summary", "--recent", "--force")

        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "ready")
        self.assertEqual(data["source"], "manual")
        self.assertIn("exactly 5", data["prompt_for_ai"])

    def test_goal_complete_rebuilds_the_whole_goal_after_a_quiet_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            self.configure(home)
            self.run_cli(home, "goal", "start", "--id", "goal-full", "--project-name", "Demo", "--project-path", "/repo/demo")
            self.log_tool(home, "design the state model", timestamp="2099-01-01T00:00:01+00:00")
            fallback = self.run_cli(home, "goal", "summary", "--id", "goal-full", "--force")
            self.log_tool(home, "verify the final behavior", timestamp="2099-01-01T00:00:02+00:00")
            complete = self.run_cli(home, "goal", "complete", "--id", "goal-full")

        self.assertEqual(fallback.returncode, 0, fallback.stderr)
        self.assertEqual(complete.returncode, 0, complete.stderr)
        self.assertEqual(json.loads(complete.stdout)["evidence_count"], 2)


if __name__ == "__main__":
    unittest.main()
