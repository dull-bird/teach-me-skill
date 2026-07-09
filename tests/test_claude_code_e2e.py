#!/usr/bin/env python3
"""
Claude Code CLI 集成测试：运行一次真实的 headless `claude -p` 会话，
执行会触发 WriteFile 的开发任务，然后验证 PreToolUse / PostToolUse / Stop hooks
都被触发，且 Stop hook 输出 block 决策（触发一次 teach-me 回顾）。

要求：本机 `claude` 已登录（`claude -p "hi"` 能正常出结果），且已经运行过
`claude-code/install-hook.sh` 把 teach-me hooks 注册进 ~/.claude/settings.json
（`./install.sh` 只同步 skill 文件，不会自动注册 hook）。

跟 test_codex_e2e.py / test_kimi_e2e.py 保持同样的结构和断言习惯，方便三个
agent 的 hook 集成测试互相对照。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

TEST_FILE = Path("/tmp/claude_code_e2e_hook_test.txt")
EVENTS_PATH = Path.home() / ".teach_me_skill" / "vault" / ".teach-me" / "events.jsonl"
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
CLAUDE_BIN = shutil.which("claude")


def read_events(limit: int = 200) -> list[dict]:
    if not EVENTS_PATH.exists():
        return []
    lines = EVENTS_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[-limit:]]


def hook_is_registered() -> bool:
    if not SETTINGS_PATH.exists():
        return False
    try:
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    hooks = settings.get("hooks", {})
    for event in ("PreToolUse", "PostToolUse", "Stop"):
        blocks = hooks.get(event, [])
        found = any(
            "teach_me_hook" in h.get("command", "")
            for block in blocks
            for h in block.get("hooks", [])
        )
        if not found:
            return False
    return True


def claude_is_logged_in() -> bool:
    try:
        probe = subprocess.run(
            [CLAUDE_BIN, "-p", "say ok", "--dangerously-skip-permissions"],
            capture_output=True,
            text=True,
            timeout=30,
            env=os.environ.copy(),
        )
    except (subprocess.SubprocessError, OSError):
        return False
    combined = (probe.stdout or "") + (probe.stderr or "")
    return "Not logged in" not in combined


class ClaudeCodeE2EHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if CLAUDE_BIN is None:
            raise unittest.SkipTest("claude binary not found in PATH")
        if not hook_is_registered():
            raise unittest.SkipTest(
                "teach-me hooks are not registered in ~/.claude/settings.json; "
                "run claude-code/install-hook.sh first"
            )
        if not claude_is_logged_in():
            raise unittest.SkipTest(
                "claude CLI is not logged in (run `claude` interactively and /login first)"
            )

    def setUp(self) -> None:
        TEST_FILE.write_text("")

    def tearDown(self) -> None:
        TEST_FILE.unlink(missing_ok=True)

    def test_real_claude_code_run_triggers_all_teach_me_hooks(self) -> None:
        """真实 Claude Code CLI 运行 Write 任务后，PreToolUse / PostToolUse / Stop
        三个 hook 都应触发，且 teach-me 记录一次 stop_decision=block。"""
        before_events = read_events()
        before_block_count = sum(
            1
            for e in before_events
            if e.get("type") == "stop_decision" and e.get("decision") == "block"
        )

        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)
            prompt = (
                f"Use the Write tool to write the text 'hello from e2e test' to the file "
                f"{TEST_FILE}. Then use Read to confirm the content. "
                "Keep your final response under 30 words."
            )
            result = subprocess.run(
                [
                    CLAUDE_BIN,
                    "-p",
                    prompt,
                    "--dangerously-skip-permissions",
                ],
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=120,
                env=os.environ.copy(),
            )

        print("claude returncode:", result.returncode)
        if result.stderr:
            print("claude stderr:\n", result.stderr[:2000])
        print("claude stdout tail:\n", result.stdout[-1500:])

        self.assertEqual(result.returncode, 0, f"claude 退出非零：{result.stderr[:1000]}")
        self.assertTrue(TEST_FILE.exists(), "测试文件未被创建")
        self.assertIn("hello from e2e test", TEST_FILE.read_text(encoding="utf-8"))

        after_events = read_events()
        after_block_count = sum(
            1
            for e in after_events
            if e.get("type") == "stop_decision" and e.get("decision") == "block"
        )
        print(f"stop block decisions: {before_block_count} -> {after_block_count}")
        self.assertGreater(
            after_block_count,
            before_block_count,
            "Stop hook 没有输出 block 决策。可能工具调用未产生足够分数，或 hook 未被触发。",
        )

        new_events = [e for e in after_events if e not in before_events]
        new_tool_events = [e for e in new_events if e.get("type") == "tool"]
        phases = {e.get("phase") for e in new_tool_events}
        self.assertIn("pre", phases, "没有 PreToolUse 事件")
        self.assertIn("post", phases, "没有 PostToolUse 事件")
        self.assertTrue(
            any("modification" in e.get("signal_tags", []) for e in new_tool_events),
            "tool 事件里没有 modification 标签",
        )

        # Stop hook 的 block 决策应该真的让 Claude 在同一轮里做了一次 teach-me 回顾
        # （回顾文本以 🌱 开头，会体现在最终回复或 review_prompt 里）。
        new_stop_decisions = [
            e
            for e in new_events
            if e.get("type") == "stop_decision" and e.get("decision") == "block"
        ]
        self.assertTrue(
            any("🌱" in e.get("review_prompt", "") for e in new_stop_decisions),
            "stop_decision 事件里没有 🌱 开头的 review_prompt",
        )


if __name__ == "__main__":
    unittest.main()
