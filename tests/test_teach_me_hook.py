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
    def test_manual_prompt_injects_context_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "教我这个 hook 是怎么工作的",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "transcript_path": "/tmp/fake_transcript.jsonl",
                },
                Path(tmp),
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        data = parse_stdout(result)
        self.assertNotIn("decision", data)
        context = data["hookSpecificOutput"]["additionalContext"]
        self.assertIn("SKILL.md", context)
        self.assertIn("read and follow", context)
        self.assertLess(len(context), 220)

    def test_messages_prompt_with_manual_trigger_injects_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "messages": [{"content": "请解释 Hook 的事件边界。"}],
                    "session_id": "s-messages",
                    "turn_id": "t-messages",
                },
                Path(tmp),
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        context = parse_stdout(result)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("read and follow", context)
        self.assertIn("SKILL.md", context)

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

    def test_uninitialized_work_prompt_uses_compact_skill_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "请修复这个 Python 测试。",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                },
                Path(tmp),
        )
        context = parse_stdout(result)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("read and follow", context)
        self.assertIn("SKILL.md", context)
        self.assertNotIn("configure", context)

    def test_uninitialized_setup_choice_uses_same_compact_skill_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "我选择 2：实战教练，知识重点 implementation。",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                },
                Path(tmp),
        )
        context = parse_stdout(result)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("read and follow", context)
        self.assertIn("SKILL.md", context)
        self.assertNotIn("configure", context)

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
        self.assertTrue(any("verification" in event.get("signal_tags", []) for event in events))

    def test_failed_tool_event_records_error_signal_for_scalar_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = run_hook(
                {
                    "hook_event_name": "PostToolUseFailure",
                    "tool_name": "Bash",
                    "tool_input": "pytest tests/test_parser.py",
                    "tool_response": "Command failed: exit status 1",
                    "session_id": "s-failure",
                    "turn_id": "t-failure",
                    "cwd": "/repo",
                },
                home,
            )
            events = read_events(home)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["phase"], "failure")
        self.assertIn("error_signal", events[0]["signal_tags"])
        self.assertEqual(events[0]["command"], "pytest tests/test_parser.py")

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
            hso = data["hookSpecificOutput"]
            self.assertEqual(hso["permissionDecision"], "deny")
            reason = hso["permissionDecisionReason"]
            self.assertEqual(
                reason,
                f"Teach Me review requires setup. Read and follow `{ROOT / 'skills' / 'teach-me' / 'SKILL.md'}`.",
            )
            events = read_events(home)
            stop_decision = events[-1]
            self.assertEqual(stop_decision["type"], "stop_decision")
            self.assertEqual(stop_decision["decision"], "block")
            self.assertIn("review_prompt", stop_decision)
            self.assertIn("Detection evidence", stop_decision["review_prompt"])
            self.assertIn("confirm", stop_decision["review_prompt"].lower())
            self.assertIn("vault", stop_decision["review_prompt"].lower())

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
            hso = data["hookSpecificOutput"]
            self.assertEqual(hso["permissionDecision"], "deny")
            reason = hso["permissionDecisionReason"]
            self.assertEqual(
                reason,
                f"Teach Me review required. Read and follow `{ROOT / 'skills' / 'teach-me' / 'SKILL.md'}`.",
            )
            events = read_events(home)
            stop_decision = events[-1]
            self.assertEqual(stop_decision["type"], "stop_decision")
            self.assertEqual(stop_decision["decision"], "block")
            self.assertIn("capture", stop_decision["review_prompt"].lower())
            self.assertIn("one core mechanism", stop_decision["review_prompt"])
            self.assertIn("teach", stop_decision["review_prompt"].lower())
            self.assertIn("follow-up", stop_decision["review_prompt"].lower())
            self.assertIn("prerequisite", stop_decision["review_prompt"].lower())
            self.assertIn("Detection evidence", stop_decision["review_prompt"])

    def test_codex_stop_uses_decision_block_format(self) -> None:
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
                    "transcript_path": "/tmp/codex-transcript.jsonl",
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
                    "last_assistant_message": "测试通过。",
                    "transcript_path": "/tmp/codex-transcript.jsonl",
                },
                home,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        data = parse_stdout(result)
        self.assertEqual(data["decision"], "block")
        self.assertIn("Teach Me", data["reason"])
        self.assertIn("requires setup", data["reason"])
        self.assertNotIn("hookSpecificOutput", data)
        self.assertNotIn("systemMessage", data)

    def test_codex_stop_with_weak_evidence_stays_silent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Bash",
                    "tool_input": {"command": "pwd"},
                    "session_id": "s-codex-weak",
                    "turn_id": "t-codex-weak",
                    "cwd": "/repo",
                },
                home,
            )
            result = run_hook(
                {
                    "hook_event_name": "Stop",
                    "session_id": "s-codex-weak",
                    "turn_id": "t-codex-weak",
                    "cwd": "/repo",
                    "transcript_path": "/tmp/codex-transcript.jsonl",
                    "stop_hook_active": False,
                    "last_assistant_message": "当前目录是 /repo。",
                },
                home,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_claude_code_stop_uses_decision_block_format(self) -> None:
        """Claude Code's Stop payload also carries transcript_path (it's a common
        field on every event, not Codex-specific), so it must hit the same
        top-level {"decision": "block", "reason": ...} branch as Codex, not the
        hookSpecificOutput.permissionDecision branch (invalid for Stop hooks
        per Claude Code's own hook schema)."""
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
                    "transcript_path": "/Users/dev/.claude/projects/repo/abc123.jsonl",
                    "permission_mode": "default",
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
                    "last_assistant_message": "测试通过。",
                    "transcript_path": "/Users/dev/.claude/projects/repo/abc123.jsonl",
                    "permission_mode": "default",
                },
                home,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        data = parse_stdout(result)
        self.assertEqual(data["decision"], "block")
        self.assertNotIn("hookSpecificOutput", data)

    def test_claude_code_manual_prompt_injects_context_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "教我这个 hook 是怎么工作的",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                    "transcript_path": "/Users/dev/.claude/projects/repo/abc123.jsonl",
                    "permission_mode": "default",
                },
                Path(tmp),
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        data = parse_stdout(result)
        self.assertNotIn("decision", data)
        self.assertIn("read and follow", data["hookSpecificOutput"]["additionalContext"])

    def test_explicit_opt_out_stays_silent_and_suppresses_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            write_initialized_config(home)
            prompt_result = run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": [
                        {"type": "text", "text": "修改 VERSION。不要教学，不要问我问题。"}
                    ],
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                },
                home,
            )
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "WriteFile",
                    "tool_input": {"file_path": "/repo/VERSION", "content": "1.0.1"},
                    "tool_response": {"ok": True},
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                },
                home,
            )
            stop_result = run_hook(
                {
                    "hook_event_name": "Stop",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                    "stop_hook_active": False,
                    "last_assistant_message": "修改完成。",
                },
                home,
            )

        self.assertEqual(prompt_result.stdout, "")
        self.assertEqual(stop_result.stdout, "")

    def test_internal_teach_me_reads_do_not_trigger_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            write_initialized_config(home)
            run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "Run a command and report whether it exists.",
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
                    "tool_input": {"command": "sed -n '1,200p' /home/me/.codex/skills/teach-me/SKILL.md"},
                    "tool_response": {"stdout": "skill text", "stderr": ""},
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
                    "last_assistant_message": "Command unavailable.",
                },
                home,
            )

        self.assertEqual(result.stdout, "")

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

    def test_stop_can_block_again_after_new_work_in_same_turn(self) -> None:
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
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Edit",
                    "tool_input": {"file_path": "/repo/video/.gitignore"},
                    "tool_response": {"ok": True},
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
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
                    "last_assistant_message": "已取消跟踪音频文件。",
                },
                home,
            )

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(parse_stdout(first)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(parse_stdout(second)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_kimi_style_stop_stays_silent_without_new_work_after_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest"},
                    "tool_response": {"stdout": "1 passed", "stderr": ""},
                    "session_id": "s-kimi",
                    "turn_id": "t-kimi",
                    "cwd": "/repo",
                },
                home,
            )
            first = run_hook(
                {
                    "hook_event_name": "Stop",
                    "session_id": "s-kimi",
                    "turn_id": "t-kimi",
                    "cwd": "/repo",
                    "last_assistant_message": "测试通过。",
                },
                home,
            )
            second = run_hook(
                {
                    "hook_event_name": "Stop",
                    "session_id": "s-kimi",
                    "turn_id": "t-kimi",
                    "cwd": "/repo",
                    "last_assistant_message": "复盘完成。",
                },
                home,
            )

        self.assertEqual(parse_stdout(first)["hookSpecificOutput"]["permissionDecision"], "deny")
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
        self.assertEqual(parse_stdout(first)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(parse_stdout(second)["hookSpecificOutput"]["permissionDecision"], "deny")


    def test_compact_stop_reason_in_long_conversation_with_ten_tasks(self) -> None:
        """Simulate a full multi-turn conversation covering 10 distinct tasks.

        Each turn is a different scope (turn_id), so Stop can independently
        decide whether to block. The returned reason must stay compact, while
        the full audit prompt (detection evidence, modified files, rubric) is
        preserved in the event log.
        """
        tasks = [
            {
                "name": "bug_fix",
                "prompt": "fix parser bug and run tests",
                "tools": [
                    {"event": "PostToolUse", "tool_name": "Edit", "tool_input": {"file_path": "/repo/parser.py", "old_string": "split(',')", "new_string": "split(',', 1)"}, "tool_response": {"ok": True}},
                    {"event": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "pytest test_parser.py"}, "tool_response": {"stdout": "5 passed", "stderr": ""}},
                ],
                "last_message": "Fixed edge case and all tests pass.",
                "should_block": True,
            },
            {
                "name": "config_change",
                "prompt": "increase timeout in app.ini",
                "tools": [
                    {"event": "PostToolUse", "tool_name": "Edit", "tool_input": {"file_path": "/repo/app.ini", "old_string": "timeout = 5", "new_string": "timeout = 15"}, "tool_response": {"ok": True}},
                    {"event": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "pytest test_config.py"}, "tool_response": {"stdout": "2 passed", "stderr": ""}},
                ],
                "last_message": "Timeout updated and config tests pass.",
                "should_block": True,
            },
            {
                "name": "data_analysis",
                "prompt": "analyze sales.csv",
                "tools": [
                    {"event": "PostToolUse", "tool_name": "Read", "tool_input": {"file_path": "/repo/sales.csv"}, "tool_response": {"content": "month,amount\nJan,100\nFeb,200"}},
                    {"event": "PostToolUse", "tool_name": "WriteFile", "tool_input": {"file_path": "/repo/findings.md", "content": "Average sales: 150."}, "tool_response": {"ok": True}},
                ],
                "last_message": "Wrote findings to findings.md.",
                "should_block": True,
            },
            {
                "name": "explicit_opt_out",
                "prompt": "update VERSION to 1.0.1. 不要教学，不要总结知识。",
                "tools": [
                    {"event": "PostToolUse", "tool_name": "WriteFile", "tool_input": {"file_path": "/repo/VERSION", "content": "1.0.1"}, "tool_response": {"ok": True}},
                    {"event": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "cat VERSION"}, "tool_response": {"stdout": "1.0.1", "stderr": ""}},
                ],
                "last_message": "VERSION updated.",
                "should_block": False,
            },
            {
                "name": "manual_teach_with_work",
                "prompt": "教我理解 service.py 的依赖注入，先读代码再解释",
                "tools": [
                    {"event": "PostToolUse", "tool_name": "Read", "tool_input": {"file_path": "/repo/service.py"}, "tool_response": {"content": "class Service:\n    def __init__(self, repo):\n        self.repo = repo"}},
                    {"event": "PostToolUse", "tool_name": "Edit", "tool_input": {"file_path": "/repo/service.py", "old_string": "def __init__(self, repo):", "new_string": "def __init__(self, repo: Repository):"}, "tool_response": {"ok": True}},
                ],
                "last_message": "Read service.py and added type hint.",
                "should_block": True,
            },
            {
                "name": "mechanical_rename_with_error",
                "prompt": "rename Demo to Sample in README",
                "tools": [
                    {"event": "PostToolUse", "tool_name": "Edit", "tool_input": {"file_path": "/repo/README.md", "old_string": "# Demo", "new_string": "# Sample"}, "tool_response": {"ok": True}},
                    {"event": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "python3 -c \"raise Exception('Sample failed')\""}, "tool_response": {"stdout": "", "stderr": "Exception: Sample failed"}},
                ],
                "last_message": "Renamed but the smoke test failed.",
                "should_block": True,
            },
            {
                "name": "mutable_default_bug",
                "prompt": "fix basket.py state leak and run tests",
                "tools": [
                    {"event": "PostToolUse", "tool_name": "Edit", "tool_input": {"file_path": "/repo/basket.py", "old_string": "def __init__(self, items=[]):", "new_string": "def __init__(self, items=None):"}, "tool_response": {"ok": True}},
                    {"event": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "pytest test_basket.py"}, "tool_response": {"stdout": "8 passed", "stderr": ""}},
                ],
                "last_message": "Fixed mutable default and tests pass.",
                "should_block": True,
            },
            {
                "name": "refactor",
                "prompt": "refactor pricing.py discount logic",
                "tools": [
                    {"event": "PostToolUse", "tool_name": "Edit", "tool_input": {"file_path": "/repo/pricing.py", "old_string": "if amount > 100:\n    discount = 0.1\nif amount > 200:\n    discount = 0.2", "new_string": "discount = 0.1 if amount > 100 else 0.2 if amount > 200 else 0"}, "tool_response": {"ok": True}},
                    {"event": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "pytest test_pricing.py"}, "tool_response": {"stdout": "6 passed", "stderr": ""}},
                ],
                "last_message": "Refactored discount logic and tests pass.",
                "should_block": True,
            },
            {
                "name": "state_machine_docs",
                "prompt": "read state_machine.py and explain transitions in architecture.md",
                "tools": [
                    {"event": "PostToolUse", "tool_name": "Read", "tool_input": {"file_path": "/repo/state_machine.py"}, "tool_response": {"content": "class StateMachine:\n    def transition(self, event):\n        if event in self.allowed:\n            self.state = event"}},
                    {"event": "PostToolUse", "tool_name": "WriteFile", "tool_input": {"file_path": "/repo/architecture.md", "content": "Transitions are guarded by allowed set."}, "tool_response": {"ok": True}},
                ],
                "last_message": "Documented transition constraints.",
                "should_block": True,
            },
            {
                "name": "build_pipeline",
                "prompt": "add feature and run full build",
                "tools": [
                    {"event": "PostToolUse", "tool_name": "WriteFile", "tool_input": {"file_path": "/repo/feature.py", "content": "def feature(): pass"}, "tool_response": {"ok": True}},
                    {"event": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "npm run build"}, "tool_response": {"stdout": "build complete", "stderr": ""}},
                    {"event": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "npm run lint"}, "tool_response": {"stdout": "no lint errors", "stderr": ""}},
                ],
                "last_message": "Feature added, build and lint pass.",
                "should_block": True,
            },
        ]

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            write_initialized_config(home)
            session_id = "long-conversation-1"
            cwd = "/repo"

            for index, task in enumerate(tasks, start=1):
                turn_id = f"t{index}"

                # Prompt hook for this turn
                run_hook(
                    {
                        "hook_event_name": "UserPromptSubmit",
                        "prompt": task["prompt"],
                        "session_id": session_id,
                        "turn_id": turn_id,
                        "cwd": cwd,
                    },
                    home,
                )

                # Tool hooks for this turn
                for tool in task["tools"]:
                    run_hook(
                        {
                            "hook_event_name": tool["event"],
                            "tool_name": tool["tool_name"],
                            "tool_input": tool["tool_input"],
                            "tool_response": tool["tool_response"],
                            "session_id": session_id,
                            "turn_id": turn_id,
                            "cwd": cwd,
                        },
                        home,
                    )

                # Stop hook for this turn
                result = run_hook(
                    {
                        "hook_event_name": "Stop",
                        "session_id": session_id,
                        "turn_id": turn_id,
                        "cwd": cwd,
                        "stop_hook_active": False,
                        "last_assistant_message": task["last_message"],
                    },
                    home,
                )

                self.assertEqual(result.returncode, 0, f"{task['name']} stop failed: {result.stderr}")
                events = read_events(home)
                stop_decisions = [
                    e for e in events
                    if e.get("type") == "stop_decision"
                    and e.get("turn_id") == turn_id
                ]
                self.assertEqual(len(stop_decisions), 1, f"{task['name']} should log exactly one stop_decision")
                decision = stop_decisions[0]
                self.assertEqual(decision["decision"], "block" if task["should_block"] else "allow", task["name"])

                if task["should_block"]:
                    data = parse_stdout(result)
                    reason = data["hookSpecificOutput"]["permissionDecisionReason"]
                    self.assertEqual(
                        reason,
                        f"Teach Me review required. Read and follow `{ROOT / 'skills' / 'teach-me' / 'SKILL.md'}`.",
                        task["name"],
                    )

                    # Full audit trail lives in the event log
                    self.assertIn("Detection evidence", decision["review_prompt"], task["name"])
                    self.assertIn("score:", decision["review_prompt"], task["name"])
                else:
                    self.assertEqual(result.stdout.strip(), "", f"{task['name']} should not emit stop output")
                    self.assertEqual(decision.get("review_prompt", ""), "", f"{task['name']} should not store review_prompt")

            # All events are recorded across the conversation
            all_events = read_events(home)
            self.assertGreaterEqual(len(all_events), 30)
            self.assertEqual(
                len([e for e in all_events if e.get("type") == "stop_decision"]),
                len(tasks),
            )



class InstallerTests(unittest.TestCase):
    def test_codex_installer_registers_stop_and_all_tool_phases(self) -> None:
        module = load_module(ROOT / "codex" / "install_hook.py")
        text = module.install("")
        self.assertIn("[[hooks.Stop]]", text)
        self.assertIn("[[hooks.PreToolUse]]", text)
        self.assertIn("[[hooks.PostToolUse]]", text)
        self.assertNotIn('matcher = "*"', text)
        self.assertIn("teach_me_hook.py", text)
        self.assertIn("[sandbox_workspace_write]", text)
        self.assertIn(f'"{module.TEACH_ME_HOME}"', text)

    def test_codex_installer_merges_writable_root_once(self) -> None:
        module = load_module(ROOT / "codex" / "install_hook.py")
        existing = (
            "[sandbox_workspace_write]\n"
            'writable_roots = ["/tmp/project"]\n'
            "\n"
            "[projects.\"/tmp/project\"]\n"
            'trust_level = "trusted"\n'
        )
        text = module.install(existing)
        second = module.install(text)
        self.assertIn('"/tmp/project"', second)
        self.assertIn(f'"{module.TEACH_ME_HOME}"', second)
        self.assertEqual(second.count(f'"{module.TEACH_ME_HOME}"'), 1)

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
        self.assertNotIn('matcher = "*"', text)

    def test_kimi_installer_uses_array_of_tables_when_no_hooks_exist(self) -> None:
        module = load_module(ROOT / "kimi" / "install_hook.py")
        text = module.install('default_model = "kimi-code/kimi-for-coding"\n')
        self.assertIn("[[hooks]]", text)
        self.assertIn('event = "Stop"', text)
        self.assertNotIn('matcher = "*"', text)

    def test_write_file_event_captures_content_excerpt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "WriteFile",
                    "tool_input": {
                        "file_path": "/repo/essay.md",
                        "content": "AI needs its own time to grow.\nIt is still borrowing human tools.",
                    },
                    "tool_response": {"ok": True},
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                },
                home,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            events = read_events(home)
            tool_events = [e for e in events if e.get("type") == "tool"]
            self.assertEqual(len(tool_events), 1)
            event = tool_events[0]
            self.assertIn("modification", event.get("signal_tags", []))
            self.assertIn("AI needs its own time", event.get("content_excerpt", ""))
            self.assertEqual(event.get("file_path"), "/repo/essay.md")

    def test_stop_prompt_lists_modified_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            write_initialized_config(home)
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "WriteFile",
                    "tool_input": {
                        "file_path": "/repo/essay.md",
                        "content": "AI needs its own time.",
                    },
                    "tool_response": {"ok": True},
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
                    "last_assistant_message": "Done.",
                },
                home,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = parse_stdout(result)
            reason = data["hookSpecificOutput"]["permissionDecisionReason"]
            self.assertEqual(
                reason,
                f"Teach Me review required. Read and follow `{ROOT / 'skills' / 'teach-me' / 'SKILL.md'}`.",
            )
            events = read_events(home)
            stop_decision = [e for e in events if e.get("type") == "stop_decision"][-1]
            self.assertIn("Files created or edited", stop_decision["review_prompt"])
            self.assertIn("/repo/essay.md", stop_decision["review_prompt"])
            self.assertIn("Read these files", stop_decision["review_prompt"])

    def test_work_prompt_injects_compact_progressive_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            write_initialized_config(home)
            result = run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "Please debug this Python service and update its tests.",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "cwd": "/repo",
                },
                home,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        context = parse_stdout(result)["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(
            context,
            f"Teach Me is active. Do not interrupt implementation. At a meaningful phase boundary, read and follow `{ROOT / 'skills' / 'teach-me' / 'SKILL.md'}`.",
        )
        self.assertNotIn("context --full", context)
        self.assertLess(len(context), 220)

    def test_initialized_stop_prompt_is_compact_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            write_initialized_config(home)
            run_hook(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "WriteFile",
                    "tool_input": {"file_path": "/repo/demo.py", "content": "print('ok')"},
                    "tool_response": {"ok": True},
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
                    "last_assistant_message": "Done.",
                },
                home,
            )

        reason = parse_stdout(result)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertEqual(
            reason,
            f"Teach Me review required. Read and follow `{ROOT / 'skills' / 'teach-me' / 'SKILL.md'}`.",
        )
