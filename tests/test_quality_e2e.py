from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "run_quality_e2e.py"
SPEC = importlib.util.spec_from_file_location("run_quality_e2e", RUNNER_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def scenario(scenario_id: str):
    return next(item for item in runner.SCENARIOS if item.id == scenario_id)


class QualityE2ETests(unittest.TestCase):
    def test_extract_codex_final_response_ignores_terminal_log_questions(self) -> None:
        output = (
            "user\n这是任务吗？\n"
            "hook: PostToolUse\n"
            "codex\n核心是默认列表只创建一次。可选判断：这样会共享状态，对吗？\n"
            "diff --git a/a.py b/a.py\n"
            "hook: Stop\n"
            "tokens used\n10"
        )
        final_response = runner.extract_final_response("codex", output)
        self.assertEqual(final_response, "核心是默认列表只创建一次。可选判断：这样会共享状态，对吗？")
        self.assertEqual(runner.question_count(final_response), 1)

    def test_extract_kimi_final_response_uses_last_assistant_message(self) -> None:
        output = "\n".join(
            (
                '"diagnostic string"',
                '{"role":"assistant","content":"先读取文件？","tool_calls":[{"name":"Read"}]}',
                '{"role":"tool","content":"# Demo"}',
                '{"role":"assistant","content":"已完成修改。"}',
                '{"role":"meta","type":"session.resume_hint","content":"resume"}',
            )
        )
        self.assertEqual(runner.extract_final_response("kimi", output), "已完成修改。")

    def test_codex_token_usage_is_parsed(self) -> None:
        self.assertEqual(runner.token_usage("codex", "tokens used\n25,757\n"), 25757)

    def test_evaluate_counts_only_final_response_questions(self) -> None:
        item = scenario("mutable_default")
        events = [
            {
                "type": "stop_decision",
                "decision": "block",
                "review_prompt": "short",
                "score": 8,
                "signal_tags": ["modification", "verification"],
            }
        ]
        assessment = runner.evaluate(
            item,
            "默认参数只求值一次，可变列表会共享状态。这样理解对吗？",
            events,
            True,
        )
        self.assertEqual(assessment["question_count"], 1)
        self.assertTrue(assessment["decision_correct"])
        self.assertTrue(assessment["task_completed"])

    def test_task_completion_requires_expected_workspace_content(self) -> None:
        item = scenario("mechanical_rename")
        before = {"README.md": "# Demo\n"}
        self.assertFalse(runner.task_completed(item, before, before))
        self.assertTrue(runner.task_completed(item, before, {"README.md": "# Sample\n"}))

    def test_config_completion_accepts_chinese_or_english_seconds(self) -> None:
        item = scenario("config_change")
        before = {"app.ini": "[network]\ntimeout = 5\n"}
        self.assertTrue(runner.task_completed(item, before, {"app.ini": "[network]\n# 单位：秒\ntimeout = 15\n"}))
        self.assertTrue(runner.task_completed(item, before, {"app.ini": "[network]\n# Unit: seconds\ntimeout = 15\n"}))

    def test_opt_out_without_review_scores_correctly(self) -> None:
        item = scenario("explicit_opt_out")
        assessment = runner.evaluate(item, "已更新版本。", [], True)
        self.assertTrue(assessment["decision_correct"])
        self.assertEqual(assessment["question_count"], 0)
        self.assertEqual(assessment["score"], 100)


if __name__ == "__main__":
    unittest.main()
