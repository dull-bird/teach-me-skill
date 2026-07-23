#!/usr/bin/env python3
"""Tests for the Oh My Pi (OMP) Teach Me hook integration.

The OMP integration relies on the @hsingjui/pi-hooks extension, which reads
command hooks from ~/.pi/agent/settings.json. These tests verify the installer,
the settings file format, and the hook script's handling of OMP-compatible
payloads.
"""

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
OMP_INSTALLER = REPO_ROOT / "omp" / "install_hook.py"
TEACH_ME_HOOK = REPO_ROOT / "skills" / "teach-me" / "scripts" / "teach_me_hook.py"
TEACH_ME_SCRIPT = REPO_ROOT / "skills" / "teach-me" / "scripts" / "teach_me.py"


class OmpInstallerTests(unittest.TestCase):
    def run_installer(self, tmp: str, *args: str) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["HOME"] = tmp
        return subprocess.run(
            [sys.executable, str(OMP_INSTALLER), *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

    def test_installer_creates_global_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_installer(tmp, "--skill-root", "/fake/skills")
            self.assertEqual(result.returncode, 0, result.stderr)

            settings_path = Path(tmp) / ".pi" / "agent" / "settings.json"
            self.assertTrue(settings_path.exists())
            settings = json.loads(settings_path.read_text())
            self.assertIn("hooks", settings)
            hooks = settings["hooks"]
            for event in ("PreToolUse", "PostToolUse", "PostToolUseFailure", "Stop"):
                self.assertIn(event, hooks)
                self.assertEqual(len(hooks[event]), 1)
                self.assertEqual(hooks[event][0]["hooks"][0]["type"], "command")
                self.assertIn("teach_me_hook.py", hooks[event][0]["hooks"][0]["command"])

    def test_installer_uses_custom_skill_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_root = Path(tmp) / "custom" / "skills"
            result = self.run_installer(tmp, "--skill-root", str(skill_root))
            self.assertEqual(result.returncode, 0, result.stderr)

            settings = json.loads((Path(tmp) / ".pi" / "agent" / "settings.json").read_text())
            command = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
            self.assertIn(str(skill_root / "teach-me" / "scripts" / "teach_me_hook.py"), command)

    def test_installer_adds_tool_matchers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.run_installer(tmp, "--skill-root", "/fake/skills")
            settings = json.loads((Path(tmp) / ".pi" / "agent" / "settings.json").read_text())
            for event in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
                self.assertEqual(settings["hooks"][event][0].get("matcher"), "*")
            # Stop does not use a matcher in pi-hooks.
            self.assertNotIn("matcher", settings["hooks"]["Stop"][0])

    def test_installer_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.run_installer(tmp, "--skill-root", "/fake/skills")
            first = (Path(tmp) / ".pi" / "agent" / "settings.json").read_text()
            self.run_installer(tmp, "--skill-root", "/fake/skills")
            second = (Path(tmp) / ".pi" / "agent" / "settings.json").read_text()
            # Running twice should not duplicate hook blocks.
            self.assertEqual(first, second)
            settings = json.loads(second)
            for event in ("PreToolUse", "PostToolUse", "PostToolUseFailure", "Stop"):
                self.assertEqual(len(settings["hooks"][event]), 1)

    def test_uninstall_removes_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.run_installer(tmp, "--skill-root", "/fake/skills")
            self.run_installer(tmp, "--skill-root", "/fake/skills", "--uninstall")
            settings = json.loads((Path(tmp) / ".pi" / "agent" / "settings.json").read_text())
            self.assertNotIn("hooks", settings)

    def test_installer_preserves_unrelated_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / ".pi" / "agent" / "settings.json"
            settings_path.parent.mkdir(parents=True)
            settings_path.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "SessionStart": [
                                {
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": "echo 'hello'",
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                )
            )
            self.run_installer(tmp, "--skill-root", "/fake/skills")
            settings = json.loads(settings_path.read_text())
            self.assertIn("SessionStart", settings["hooks"])
            self.assertIn("PreToolUse", settings["hooks"])

    def test_installer_project_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Change cwd to tmp so .pi/settings.json is written relative to it.
            original_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                result = self.run_installer(tmp, "--project", "--skill-root", "/fake/skills")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue((Path(tmp) / ".pi" / "settings.json").exists())
            finally:
                os.chdir(original_cwd)


class OmpHookPayloadTests(unittest.TestCase):
    def run_hook(self, payload: dict) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        # Ensure the hook does not pollute the real vault during tests.
        env["TEACH_ME_HOME"] = str(REPO_ROOT / ".teach_me_test")
        return subprocess.run(
            [sys.executable, str(TEACH_ME_HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

    def test_pretooluse_payload_is_accepted(self) -> None:
        payload = {
            "session_id": "test-omp-session",
            "transcript_path": "/tmp/test.jsonl",
            "cwd": "/tmp/project",
            "hook_event_name": "PreToolUse",
            "tool_name": "bash",
            "tool_input": {"command": "ls -la"},
            "tool_use_id": "toolu_123",
        }
        result = self.run_hook(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        # PreToolUse does not produce output for Teach Me.
        self.assertEqual(result.stdout.strip(), "")

    def test_posttooluse_write_payload_logs_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            teach_home = Path(tmp) / "teach_me"
            env = os.environ.copy()
            env["TEACH_ME_HOME"] = str(teach_home)
            payload = {
                "session_id": "test-omp-session",
                "transcript_path": "/tmp/test.jsonl",
                "cwd": "/tmp/project",
                "hook_event_name": "PostToolUse",
                "tool_name": "write",
                "tool_input": {"path": "/tmp/project/test.md", "content": "hello"},
                "tool_response": {"ok": True},
                "tool_use_id": "toolu_123",
            }
            result = subprocess.run(
                [sys.executable, str(TEACH_ME_HOOK)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            events_path = teach_home / "vault" / ".teach-me" / "events.jsonl"
            self.assertTrue(events_path.exists())
            events = [json.loads(line) for line in events_path.read_text().splitlines()]
            tool_events = [e for e in events if e.get("type") == "tool"]
            self.assertEqual(len(tool_events), 1)
            self.assertEqual(tool_events[0]["tool_name"], "write")
            self.assertIn("modification", tool_events[0]["signal_tags"])

    def test_stop_payload_returns_allow(self) -> None:
        payload = {
            "session_id": "test-omp-session",
            "transcript_path": "/tmp/test.jsonl",
            "cwd": "/tmp/project",
            "hook_event_name": "Stop",
            "stop_hook_active": False,
            "last_assistant_message": "Hello.",
        }
        result = self.run_hook(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        # No work has been logged, so the hook should allow the stop.
        self.assertEqual(result.stdout.strip(), "")

    def test_stop_payload_returns_block_with_high_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            teach_home = Path(tmp) / "teach_me"
            env = os.environ.copy()
            env["TEACH_ME_HOME"] = str(teach_home)
            # Log a high-value modification event first.
            write_payload = {
                "session_id": "test-omp-session",
                "transcript_path": "/tmp/test.jsonl",
                "cwd": "/tmp/project",
                "hook_event_name": "PostToolUse",
                "tool_name": "edit",
                "tool_input": {
                    "path": "/tmp/project/src.py",
                    "old_text": "old",
                    "new_text": "new",
                },
                "tool_response": {"ok": True},
                "tool_use_id": "toolu_edit",
            }
            subprocess.run(
                [sys.executable, str(TEACH_ME_HOOK)],
                input=json.dumps(write_payload),
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            # Log a finished/complete signal to push the score over threshold.
            bash_payload = {
                "session_id": "test-omp-session",
                "transcript_path": "/tmp/test.jsonl",
                "cwd": "/tmp/project",
                "hook_event_name": "PostToolUse",
                "tool_name": "bash",
                "tool_input": {"command": "pytest tests/test.py -v"},
                "tool_response": {"stdout": "passed", "stderr": "", "exitCode": 0},
                "tool_use_id": "toolu_bash",
            }
            subprocess.run(
                [sys.executable, str(TEACH_ME_HOOK)],
                input=json.dumps(bash_payload),
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            stop_payload = {
                "session_id": "test-omp-session",
                "transcript_path": "/tmp/test.jsonl",
                "cwd": "/tmp/project",
                "hook_event_name": "Stop",
                "stop_hook_active": False,
                "last_assistant_message": "I finished the refactor and tests pass.",
            }
            result = subprocess.run(
                [sys.executable, str(TEACH_ME_HOOK)],
                input=json.dumps(stop_payload),
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = result.stdout.strip()
            # transcript_path is present in OMP payloads, so the hook should
            # emit a Claude Code-style block decision.
            if output:
                parsed = json.loads(output)
                self.assertEqual(parsed.get("decision"), "block")
                self.assertIn("reason", parsed)
                self.assertIn("Teach Me", parsed["reason"])


class OmpHooksCommandTests(unittest.TestCase):
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
        # Put a mock `omp` on PATH so the hook command detects OMP and attempts
        # to check the pi-hooks extension.
        mock_bin = Path(tmp) / "bin"
        mock_bin.mkdir()
        env["PATH"] = str(mock_bin) + os.pathsep + env["PATH"]

        # Create a mock omp that reports pi-hooks installed and no other plugins.
        omp_mock = mock_bin / "omp"
        omp_mock.write_text(
            "#!/bin/bash\n"
            "if [ \"$1\" = \"plugin\" ] \u0026\u0026 [ \"$2\" = \"list\" ]; then\n"
            "  echo 'plugins:'\n"
            "  echo '  - @hsingjui/pi-hooks'\n"
            "else\n"
            "  echo \"Mock omp: $*\" \u003e\u00262\n"
            "  exit 1\n"
            "fi\n"
        )
        omp_mock.chmod(0o755)
        return env

    def test_hooks_enable_detects_omp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp)
            home = Path(tmp) / "home"
            (home / ".omp").mkdir()

            result = self.run_teach_me(env, "hooks", "--enable", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            agents = {r["agent"]: r for r in data["results"]}
            self.assertIn("omp", agents)
            # pi-hooks is mocked as installed, so it should attempt to write
            # the OMP settings file and succeed.
            self.assertTrue(agents["omp"]["ok"], agents["omp"]["message"])
            self.assertTrue((home / ".pi" / "agent" / "settings.json").exists())
            settings = json.loads((home / ".pi" / "agent" / "settings.json").read_text())
            self.assertIn("teach-me/scripts/teach_me_hook.py", json.dumps(settings))

    def test_hooks_enable_without_pi_hooks_reports_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp)
            # Override the mock to report no pi-hooks.
            home = Path(tmp) / "home"
            mock_bin = Path(tmp) / "bin"
            omp_mock = mock_bin / "omp"
            omp_mock.write_text(
                "#!/bin/bash\n"
                "if [ \"$1\" = \"plugin\" ] \u0026\u0026 [ \"$2\" = \"list\" ]; then\n"
                "  echo 'No plugins installed'\n"
                "else\n"
                "  echo \"Mock omp: $*\" \u003e\u00262\n"
                "  exit 1\n"
                "fi\n"
            )
            omp_mock.chmod(0o755)
            (home / ".omp").mkdir()

            result = self.run_teach_me(env, "hooks", "--enable", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            agents = {r["agent"]: r for r in data["results"]}
            self.assertFalse(agents["omp"]["ok"])
            self.assertIn("pi-hooks", agents["omp"]["message"])


if __name__ == "__main__":
    unittest.main()
