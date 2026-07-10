#!/usr/bin/env python3
"""
Codex CLI 集成测试：运行一次真实的 headless `codex exec` 会话，
执行会触发 test 标签的 Bash 任务，验证 PreToolUse / PostToolUse / Stop hooks 都被触发，
且 Stop hook 输出 block 决策（没有 Failed）。

注意：Codex 当前 Pre/PostToolUse 只对 Bash 工具触发，因此用 `python3 -m unittest` 作为任务。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

TEST_FILE = Path("/tmp/codex_e2e_hook_test.txt")
EVENTS_PATH = Path.home() / ".teach_me_skill" / "vault" / ".teach-me" / "events.jsonl"
CODEX_BIN = shutil.which("codex")


def read_events(limit: int = 200) -> list[dict]:
    if not EVENTS_PATH.exists():
        return []
    lines = EVENTS_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[-limit:]]


class CodexE2EHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if CODEX_BIN is None:
            raise unittest.SkipTest("codex binary not found in PATH")

    def setUp(self) -> None:
        TEST_FILE.write_text("")

    def tearDown(self) -> None:
        TEST_FILE.unlink(missing_ok=True)

    def test_real_codex_run_triggers_all_teach_me_hooks(self) -> None:
        """真实 Codex CLI 运行测试任务后，teach-me 的三个 hooks 都应触发并记录 block 决策。"""
        before_events = read_events()
        before_block_count = sum(
            1
            for e in before_events
            if e.get("type") == "stop_decision" and e.get("decision") == "block"
        )

        # 准备工作目录和测试文件
        work_dir = Path("/tmp/codex_e2e_work")
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / ".git").mkdir(exist_ok=True)
        (work_dir / "test_dummy.py").write_text(
            "import unittest\n"
            "class TestDummy(unittest.TestCase):\n"
            "    def test_dummy(self):\n"
            "        self.assertTrue(True)\n"
            "if __name__ == '__main__':\n"
            "    unittest.main()\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                CODEX_BIN,
                "exec",
                "--dangerously-bypass-approvals-and-sandbox",
                "--dangerously-bypass-hook-trust",
                "--sandbox", "danger-full-access",
                "--enable", "hooks",
                "Run python3 -m unittest test_dummy and report the result. Keep response under 30 words.",
            ],
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=120,
            env=os.environ.copy(),
        )

        print("codex returncode:", result.returncode)
        print("codex stderr:\n", result.stderr[-2000:])
        print("codex stdout:\n", result.stdout[-2000:])

        # Codex 可能因为额度限制返回非零，但 hook 事件应该已经记录
        # 我们重点断言 hooks 的触发情况

        # Stop hook 不应 Failed，应该 Blocked
        combined = result.stderr + result.stdout
        self.assertNotIn("hook: Stop Failed", combined)
        self.assertIn("hook: Stop Blocked", combined)

        # 验证 teach-me 事件库新增 block 决策
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
            "Stop hook 没有输出 block 决策",
        )
        new_stop_events = [
            e
            for e in after_events
            if e not in before_events and e.get("type") == "stop_decision" and e.get("decision") == "block"
        ]
        self.assertTrue(new_stop_events, "没有新增 block 型 Stop 事件")
        review_prompt = new_stop_events[-1].get("review_prompt", "")
        self.assertIn("SKILL.md", review_prompt)
        self.assertIn("context --full", review_prompt)
        self.assertNotIn("Before finishing, do a short Teach Me review", review_prompt)
        self.assertLess(len(review_prompt), 1600)

        # 验证新增事件包含 PreToolUse、PostToolUse、test 标签
        new_tool_events = [
            e
            for e in after_events
            if e not in before_events and e.get("type") == "tool"
        ]
        phases = {e.get("phase") for e in new_tool_events}
        self.assertIn("pre", phases, "没有 PreToolUse 事件")
        self.assertIn("post", phases, "没有 PostToolUse 事件")
        self.assertTrue(
            any("test" in e.get("signal_tags", []) for e in new_tool_events),
            "tool 事件里没有 test 标签",
        )


if __name__ == "__main__":
    unittest.main()
