#!/usr/bin/env python3
"""Run a two-turn first-use setup flow in real Codex and Kimi sessions."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_quality_e2e import clean_output, extract_final_response, run_pty


FIRST_PROMPT = "请修复 parser.py 的 first_field，让 test_parser.py 通过，并运行测试。完成后简短回复。"
def parse_session_id(agent: str, output: str) -> str:
    if agent == "codex":
        match = re.search(r"session id:\s*([0-9a-f-]{20,})", output, re.IGNORECASE)
        return match.group(1) if match else ""
    for line in output.splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and item.get("session_id"):
            return str(item["session_id"])
    return ""


def markdown_report(results: list[dict[str, Any]], generated_at: str) -> str:
    lines = [
        "# Teach Me 首次使用多轮 E2E 报告",
        "",
        f"- 生成时间：`{generated_at}`",
        "- 流程：未初始化状态完成真实任务 → Agent 展示教师风格选项 → 用户选择实战教练 → 恢复同一会话完成配置。",
        "",
        "| Agent | 模型 | 首轮任务 | 展示选项 | 会话恢复 | initialized | 风格 | 知识重点 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in results:
        lines.append(
            f"| {item['agent']} | `{item['model']}` | {'通过' if item['task_completed'] else '失败'} "
            f"| {'通过' if item['offered_choices'] else '失败'} | {'通过' if item['resume_ok'] else '失败'} "
            f"| {str(item['initialized']).lower()} | {item['teacher_profile'] or '-'} | {item['knowledge_focus'] or '-'} |"
        )
    for item in results:
        lines.extend(
            [
                "",
                f"## {item['agent']} / {item['model']}",
                "",
                "### 首轮最终回答",
                "",
                "```text",
                item["first_final"].replace("```", "`` `"),
                "```",
                "",
                "### 选择风格后的最终回答",
                "",
                "```text",
                item["second_final"].replace("```", "`` `"),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def run_agent(agent: str, model: str, root: Path, timeout: int) -> dict[str, Any]:
    work = root / agent / "work"
    home = root / agent / "teach-home"
    work.mkdir(parents=True, exist_ok=True)
    (work / "parser.py").write_text("def first_field(line):\n    return line.split(',')[1]\n", encoding="utf-8")
    (work / "test_parser.py").write_text(
        "import unittest\nfrom parser import first_field\n\n"
        "class T(unittest.TestCase):\n"
        "    def test_first(self): self.assertEqual(first_field('a,b'), 'a')\n\n"
        "if __name__ == '__main__': unittest.main()\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.update(
        {
            "TEACH_ME_HOME": str(home),
            "TEACH_ME_CONTEXT_MODE": "short",
            "TEACH_ME_DEBUG_PAYLOAD_PATH": str(root / agent / "hook-payloads.jsonl"),
            "TERM": "dumb",
            "NO_COLOR": "1",
        }
    )
    installed_skill = (
        Path.home() / ".codex" / "skills" / "teach-me"
        if agent == "codex"
        else Path.home() / ".agents" / "skills" / "teach-me"
    )
    choice_prompt = (
        "我选择 2：实战教练；知识重点选 implementation；vault 和语言使用默认值；Git sync 关闭。"
        "请现在只完成配置，不要 capture、不要写学习笔记。必须执行这个隔离命令："
        f"`TEACH_ME_HOME='{home}' python3 '{installed_skill / 'scripts' / 'teach_me.py'} configure "
        f"--vault '{home / 'vault'}' --language auto --teacher-style coach "
        "--knowledge-focus implementation --disable-git-sync`。"
    )
    if agent == "codex":
        first_command = [
            shutil.which("codex") or "codex",
            "exec",
            "--dangerously-bypass-hook-trust",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "--color",
            "never",
            "-C",
            str(work),
            "-m",
            model,
            FIRST_PROMPT,
        ]
    else:
        first_command = [
            shutil.which("kimi") or "kimi",
            "--model",
            model,
            "--prompt",
            FIRST_PROMPT,
            "--output-format",
            "stream-json",
        ]
    first_code, first_output, first_elapsed = run_pty(first_command, work, env, timeout)
    session_id = parse_session_id(agent, first_output)

    if agent == "codex":
        second_command = [
            shutil.which("codex") or "codex",
            "exec",
            "resume",
            "--dangerously-bypass-hook-trust",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "-m",
            model,
            session_id,
            choice_prompt,
        ]
    else:
        second_command = [
            shutil.which("kimi") or "kimi",
            "--session",
            session_id,
            "--model",
            model,
            "--prompt",
            choice_prompt,
            "--output-format",
            "stream-json",
        ]
    if session_id:
        second_code, second_output, second_elapsed = run_pty(second_command, work, env, timeout)
    else:
        second_code, second_output, second_elapsed = 125, "[SESSION ID NOT FOUND]", 0.0

    config_path = home / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    user_cfg = config.get("users", {}).get("default", config)
    style_path = home / "vault" / ".teach-me" / "style-profile.json"
    style = json.loads(style_path.read_text(encoding="utf-8")) if style_path.exists() else {}
    first_final = extract_final_response(agent, first_output)
    second_final = extract_final_response(agent, second_output)
    choices_text = first_final.lower()
    offered_choices = (
        ("default" in choices_text or "默认" in choices_text)
        and ("coach" in choices_text or "教练" in choices_text)
        and ("socratic" in choices_text or "苏格拉底" in choices_text)
    )
    task_completed = "[0]" in (work / "parser.py").read_text(encoding="utf-8")
    result = {
        "agent": agent,
        "model": model,
        "first_returncode": first_code,
        "second_returncode": second_code,
        "first_elapsed_seconds": round(first_elapsed, 2),
        "second_elapsed_seconds": round(second_elapsed, 2),
        "session_id": session_id,
        "task_completed": task_completed,
        "offered_choices": offered_choices,
        "resume_ok": second_code == 0,
        "initialized": bool(user_cfg.get("initialized")),
        "teacher_profile": style.get("teacher_profile"),
        "knowledge_focus": style.get("knowledge_focus"),
        "first_final": clean_output(first_final),
        "second_final": clean_output(second_final),
        "first_output": clean_output(first_output),
        "second_output": clean_output(second_output),
    }
    result["passed"] = all(
        (
            first_code == 0,
            second_code == 0,
            task_completed,
            offered_choices,
            result["initialized"],
            result["teacher_profile"] == "coach",
            result["knowledge_focus"] == "implementation",
        )
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex-model", default="gpt-5.6-sol")
    parser.add_argument("--kimi-model", default="kimi-code/kimi-for-coding")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="teach-me-onboarding-e2e-"))
    specs = (("codex", args.codex_model), ("kimi", args.kimi_model))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_agent, agent, model, root, args.timeout) for agent, model in specs]
        results = [future.result() for future in futures]
    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    payload = {"generated_at": generated_at, "run_root": str(root), "results": results}
    (output / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "report.md").write_text(markdown_report(results, generated_at), encoding="utf-8")
    for result in results:
        print(
            f"{result['agent']}: passed={result['passed']} first={result['first_returncode']} "
            f"resume={result['second_returncode']} style={result['teacher_profile']} focus={result['knowledge_focus']}"
        )
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
