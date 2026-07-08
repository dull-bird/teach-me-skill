from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "skills" / "teach-me" / "scripts" / "teach_me_hook.py"


def run_hook(payload: dict, home: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["TEACH_ME_HOME"] = str(home)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(ROOT),
        env=env,
        check=False,
    )


def parse_stdout(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stdout)


def read_events(home: Path) -> list[dict]:
    path = home / "vault" / ".teach-me" / "events.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def write_initialized_config(home: Path) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.json").write_text(
        json.dumps(
            {
                "version": 1,
                "initialized": True,
                "vault_path": str(home / "vault"),
                "language": "auto",
                "max_notes_per_phase": 3,
                "git_sync": {
                    "enabled": False,
                    "remote": "",
                    "branch": "main",
                    "auto_sync": False,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TeachMeHookTests(unittest.TestCase):
    def test_manual_prompt_injects_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "教我这个 hook 是怎么工作的",
                    "session_id": "s1",
                    "turn_id": "t1",
                },
                Path(tmp),
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        data = parse_stdout(result)
        context = data["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Teach Me learning context", context)
        self.assertIn("manual teaching trigger detected", context.lower())

    def test_non_learning_prompt_stays_silent_without_tool_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "今天晚上吃什么",
                    "session_id": "s1",
                    "turn_id": "t1",
                },
                Path(tmp),
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_pre_and_post_tool_events_are_logged_even_before_initialization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            pre = run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest tests/test_parser.py"},
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                },
                home,
            )
            post = run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest tests/test_parser.py"},
                    "tool_response": {"stdout": "3 passed in 0.12s", "stderr": ""},
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                },
                home,
            )
            events = read_events(home)

        self.assertEqual(pre.returncode, 0, pre.stderr)
        self.assertEqual(post.returncode, 0, post.stderr)
        self.assertGreaterEqual(len(events), 2)
        self.assertTrue(any(event.get("phase") == "pre" for event in events))
        self.assertTrue(any(event.get("phase") == "post" for event in events))
        self.assertTrue(any("test" in event.get("signal_tags", []) for event in events))

    def test_stop_blocks_after_learning_worthy_tool_work_without_prompt_keywords(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Edit",
                    "tool_input": {"file_path": "/repo/src/parser.py"},
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                },
                home,
            )
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest tests/test_parser.py"},
                    "tool_response": {"stdout": "4 passed in 0.18s", "stderr": ""},
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                },
                home,
            )
            result = run_hook(
                {
                    "hook_event_name": "Stop",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                    "stop_hook_active": False,
                    "last_assistant_message": "已修复解析问题，并通过测试。",
                },
                home,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        data = parse_stdout(result)
        self.assertEqual(data["decision"], "block")
        self.assertEqual(data["systemMessage"], "🌱")
        self.assertIn("🌱", data["reason"])
        self.assertNotIn("🌱 Teach Me:", data["reason"])
        self.assertIn("confirm", data["reason"].lower())
        self.assertIn("vault", data["reason"].lower())

    def test_initialized_stop_blocks_with_capture_instruction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            write_initialized_config(home)
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Bash",
                    "tool_input": {"command": "npm test && npm run build"},
                    "tool_response": {"stdout": "tests passed\nbuild complete", "stderr": ""},
                    "session_id": "s1",
                    "turn_id": "t2",
                    "cwd": "/repo",
                },
                home,
            )
            result = run_hook(
                {
                    "hook_event_name": "Stop",
                    "session_id": "s1",
                    "turn_id": "t2",
                    "cwd": "/repo",
                    "stop_hook_active": False,
                    "last_assistant_message": "实现完成，测试和构建都通过。",
                },
                home,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        data = parse_stdout(result)
        self.assertEqual(data["decision"], "block")
        self.assertEqual(data["systemMessage"], "🌱")
        self.assertIn("🌱", data["reason"])
        self.assertNotIn("🌱 Teach Me:", data["reason"])
        self.assertIn("capture", data["reason"].lower())
        self.assertIn("1-3", data["reason"])

    def test_stop_stays_silent_without_meaningful_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Bash",
                    "tool_input": {"command": "pwd"},
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                },
                home,
            )
            result = run_hook(
                {
                    "hook_event_name": "Stop",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                    "stop_hook_active": False,
                    "last_assistant_message": "当前目录是 /repo。",
                },
                home,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_stop_hook_active_never_blocks_again(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest"},
                    "tool_response": {"stdout": "1 passed", "stderr": ""},
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                },
                home,
            )
            result = run_hook(
                {
                    "hook_event_name": "Stop",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                    "stop_hook_active": True,
                    "last_assistant_message": "Teach Me review done.",
                },
                home,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_stop_only_blocks_once_per_turn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest"},
                    "tool_response": {"stdout": "1 passed", "stderr": ""},
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                },
                home,
            )
            first = run_hook(
                {
                    "hook_event_name": "Stop",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                    "stop_hook_active": False,
                    "last_assistant_message": "测试通过。",
                },
                home,
            )
            second = run_hook(
                {
                    "hook_event_name": "Stop",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                    "stop_hook_active": False,
                    "last_assistant_message": "测试通过。",
                },
                home,
            )

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(parse_stdout(first)["decision"], "block")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second.stdout, "")

    def test_stop_ignores_other_turn_evidence_when_turn_id_is_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Edit",
                    "tool_input": {"file_path": "/repo/src/old.py"},
                    "session_id": "s1",
                    "turn_id": "old-turn",
                    "cwd": "/repo",
                },
                home,
            )
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest"},
                    "tool_response": {"stdout": "9 passed", "stderr": ""},
                    "session_id": "s1",
                    "turn_id": "old-turn",
                    "cwd": "/repo",
                },
                home,
            )
            result = run_hook(
                {
                    "hook_event_name": "Stop",
                    "session_id": "s1",
                    "turn_id": "new-turn",
                    "cwd": "/repo",
                    "stop_hook_active": False,
                    "last_assistant_message": "没有执行新的开发操作。",
                },
                home,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_later_turn_can_block_after_earlier_turn_already_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest tests/test_a.py"},
                    "tool_response": {"stdout": "1 passed", "stderr": ""},
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                },
                home,
            )
            first = run_hook(
                {
                    "hook_event_name": "Stop",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                    "stop_hook_active": False,
                    "last_assistant_message": "测试通过。",
                },
                home,
            )
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest tests/test_b.py"},
                    "tool_response": {"stdout": "2 passed", "stderr": ""},
                    "session_id": "s1",
                    "turn_id": "t2",
                    "cwd": "/repo",
                },
                home,
            )
            second = run_hook(
                {
                    "hook_event_name": "Stop",
                    "session_id": "s1",
                    "turn_id": "t2",
                    "cwd": "/repo",
                    "stop_hook_active": False,
                    "last_assistant_message": "第二个测试场景也通过。",
                },
                home,
            )

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(parse_stdout(first)["decision"], "block")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(parse_stdout(second)["decision"], "block")


class InstallerTests(unittest.TestCase):
    def test_codex_installer_registers_stop_and_all_tool_phases(self) -> None:
        module = load_module(ROOT / "codex" / "install_hook.py")
        text = module.install("")
        self.assertIn("[[hooks.Stop]]", text)
        self.assertIn("[[hooks.PreToolUse]]", text)
        self.assertIn("[[hooks.PostToolUse]]", text)
        self.assertIn('matcher = "*"', text)
        self.assertIn("teach_me_hook.py", text)

    def test_claude_installer_registers_stop_and_post_tool_use(self) -> None:
        module = load_module(ROOT / "claude-code" / "install_hook.py")
        settings = module.install({})
        self.assertIn("Stop", settings["hooks"])
        self.assertIn("PostToolUse", settings["hooks"])
        self.assertEqual(settings["hooks"]["PreToolUse"][-1]["matcher"], "*")
        self.assertEqual(settings["hooks"]["PostToolUse"][-1]["matcher"], "*")

    def test_kimi_installer_appends_stop_to_inline_hooks_array(self) -> None:
        module = load_module(ROOT / "kimi" / "install_hook.py")
        existing = (
            'default_model = "kimi-code/kimi-for-coding"\n'
            'hooks = [\n'
            '  { event = "UserPromptSubmit", command = "python3 existing.py" }\n'
            ']\n'
        )
        text = module.install(existing)
        self.assertIn('event = "Stop"', text)
        self.assertIn('event = "PostToolUse"', text)
        self.assertIn('event = "PreToolUse"', text)
        self.assertIn("teach_me_hook.py", text)

    def test_kimi_installer_uses_array_of_tables_when_no_hooks_exist(self) -> None:
        module = load_module(ROOT / "kimi" / "install_hook.py")
        text = module.install('default_model = "kimi-code/kimi-for-coding"\n')
        self.assertIn("[[hooks]]", text)
        self.assertIn('event = "Stop"', text)
        self.assertIn('matcher = "*"', text)


if __name__ == "__main__":
    unittest.main()
