#!/usr/bin/env python3
"""
Kimi Code CLI 集成测试：运行一次真实的 headless `kimi --print` 会话，
执行会触发 file_edit 的开发任务，然后验证 Stop hook 触发 block 并产生 teach-me 回顾输出。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

TEST_FILE = Path("/tmp/kimi_e2e_hook_test.txt")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
KIMI_BIN = shutil.which("kimi")
EVENTS_PATH = Path.home() / ".teach_me_skill" / "vault" / ".teach-me" / "events.jsonl"


def read_events(limit: int = 200) -> list[dict]:
    if not EVENTS_PATH.exists():
        return []
    lines = EVENTS_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[-limit:]]


class KimiE2EHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if KIMI_BIN is None:
            raise unittest.SkipTest("kimi binary not found in PATH")

    def setUp(self) -> None:
        TEST_FILE.write_text("")

    def tearDown(self) -> None:
        TEST_FILE.unlink(missing_ok=True)

    def test_real_kimi_run_logs_stop_block_decision(self) -> None:
        """真实 Kimi CLI 运行 WriteFile 任务后，teach-me 应记录 stop_decision=block。"""
        before_events = read_events()
        before_block_count = sum(
            1
            for e in before_events
            if e.get("type") == "stop_decision" and e.get("decision") == "block"
        )

        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)
            prompt = (
                f"Use the WriteFile tool to write the text 'hello from e2e test' to the file {TEST_FILE}. "
                "Then use ReadFile to confirm the content. Keep your final response under 30 words."
            )
            cmd = [KIMI_BIN, "--print", "--prompt", prompt]
            result = subprocess.run(
                cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=120,
                env=os.environ.copy(),
            )

        print("kimi returncode:", result.returncode)
        if result.stderr:
            print("kimi stderr:\n", result.stderr[:2000])
        print("kimi stdout tail:\n", result.stdout[-1500:])

        # 基本断言：任务成功完成
        self.assertEqual(result.returncode, 0, f"kimi 退出非零：{result.stderr[:1000]}")
        self.assertTrue(TEST_FILE.exists(), "测试文件未被创建")
        self.assertIn("hello from e2e test", TEST_FILE.read_text(encoding="utf-8"))

        # 没有无效正则警告
        self.assertNotIn("Invalid regex in hook matcher", result.stderr)

        # 验证 teach-me 事件库新增了一条 block 型 stop_decision
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

        # 验证新增的事件里有 file_edit 工具证据
        new_tool_events = [
            e
            for e in after_events
            if e not in before_events and e.get("type") == "tool"
        ]
        has_file_edit = any("file_edit" in e.get("signal_tags", []) for e in new_tool_events)
        self.assertTrue(has_file_edit, "新增 tool 事件里没有 file_edit 标签")

        # 验证 Kimi CLI 确实执行了 teach-me 回顾轮次（stdout 中出现 🌱）
        self.assertIn("🌱", result.stdout, "kimi 输出中没有出现 teach-me 回顾标志 🌱")
        self.assertIn("Teach Me review", result.stdout, "kimi 输出中没有出现 'Teach Me review' 文本")


if __name__ == "__main__":
    unittest.main()
