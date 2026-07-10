#!/usr/bin/env python3
"""Run qualitative Teach Me E2E scenarios against real Codex and Kimi CLIs.

The runner uses a pseudo-terminal, an isolated worktree, and an isolated
TEACH_ME_HOME for every case. It keeps both raw agent output and hook-event
evidence, then writes a machine-readable result and a Markdown report.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import pty
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEACH_ME = PROJECT_ROOT / "skills" / "teach-me" / "scripts" / "teach_me.py"
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|authorization|access[_-]?token|secret)\b(\s*[:=]\s*)([^\s,;]+)"
)

EXPECTED_CONTENT = {
    "bug_fix": {"parser.py": ("[0]",)},
    "refactor": {"pricing.py": ("discount",)},
    "mutable_default": {"basket.py": ("items=None",)},
    "data_analysis": {"findings.md": ("18",)},
    "state_machine_docs": {"architecture.md": ("状态", "转换")},
    "mechanical_rename": {"README.md": ("# Sample",)},
    "explicit_opt_out": {"VERSION": ("1.0.1",)},
}


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    prompt: str
    files: dict[str, str]
    expect_review: bool
    keywords: tuple[str, ...]
    rationale: str


SCENARIOS = (
    Scenario(
        "bug_fix",
        "边界条件调试",
        "请检查 parser.py 和 test_parser.py，修复失败的边界条件并运行测试。最终回复不超过120字。",
        {
            "parser.py": "def first_field(line):\n    return line.split(',')[1]\n",
            "test_parser.py": (
                "import unittest\nfrom parser import first_field\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_first(self): self.assertEqual(first_field('a,b'), 'a')\n\n"
                "if __name__ == '__main__': unittest.main()\n"
            ),
        },
        True,
        ("边界", "索引", "解析"),
        "真实修复包含可迁移的索引与输入边界知识。",
    ),
    Scenario(
        "refactor",
        "重复逻辑重构",
        "重构 pricing.py 中重复的折扣逻辑，保持 test_pricing.py 通过并运行测试。最终回复不超过120字。",
        {
            "pricing.py": (
                "def retail(x):\n    return x * 0.9 if x > 100 else x\n\n"
                "def wholesale(x):\n    return x * 0.9 if x > 100 else x\n"
            ),
            "test_pricing.py": (
                "import unittest\nfrom pricing import retail, wholesale\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_prices(self):\n"
                "        self.assertEqual(retail(200), 180)\n"
                "        self.assertEqual(wholesale(50), 50)\n"
            ),
        },
        True,
        ("重复", "单一", "重构"),
        "重构应提炼重复知识，而不只是报告测试通过。",
    ),
    Scenario(
        "mutable_default",
        "可变默认参数",
        "找出 basket.py 的状态泄漏原因，修复并运行 test_basket.py。最终回复不超过120字。",
        {
            "basket.py": "def add(item, items=[]):\n    items.append(item)\n    return items\n",
            "test_basket.py": (
                "import unittest\nfrom basket import add\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_isolated(self):\n"
                "        self.assertEqual(add('a'), ['a'])\n"
                "        self.assertEqual(add('b'), ['b'])\n"
            ),
        },
        True,
        ("可变", "默认", "共享", "状态"),
        "应理解 Python 默认参数只求值一次这一隐藏机制。",
    ),
    Scenario(
        "data_analysis",
        "小型数据分析",
        "分析 sales.csv，计算平均销售额并在 findings.md 写出一个值得注意的现象。最终回复不超过120字。",
        {"sales.csv": "day,sales\nMon,10\nTue,12\nWed,50\nThu,8\nFri,10\n"},
        True,
        ("平均", "异常", "离群", "18"),
        "应从数据得到结论并识别平均数受异常值影响。",
    ),
    Scenario(
        "state_machine_docs",
        "状态机理解",
        "阅读 state_machine.py，在 architecture.md 用简短中文解释状态转换约束，不修改代码。最终回复不超过120字。",
        {
            "state_machine.py": (
                "TRANSITIONS = {'idle': {'running'}, 'running': {'idle', 'failed'}, 'failed': {'idle'}}\n"
                "def move(current, target):\n"
                "    if target not in TRANSITIONS[current]:\n"
                "        raise ValueError('invalid transition')\n"
                "    return target\n"
            )
        },
        True,
        ("状态", "转换", "约束"),
        "应基于实际代码理解允许边，而非泛泛讲状态机。",
    ),
    Scenario(
        "config_change",
        "配置语义修改",
        "把 app.ini 的 timeout 从 5 改为 15，并在同一行上方写注释说明单位为秒。最终回复不超过80字。",
        {"app.ini": "[network]\ntimeout = 5\n"},
        True,
        ("配置", "超时", "秒", "单位"),
        "虽修改很小，但单位和配置语义具有可迁移价值。",
    ),
    Scenario(
        "manual_teach",
        "显式教学请求",
        "教我理解 service.py 里的依赖注入，只解释，不改文件。先讲最基础前提，只问一个简短问题。",
        {
            "service.py": (
                "class Service:\n"
                "    def __init__(self, repository):\n        self.repository = repository\n"
                "    def find(self, key):\n        return self.repository.get(key)\n"
            )
        },
        True,
        ("依赖", "注入", "解耦", "替换"),
        "显式请求必须教学，并从弱前提开始且最多问一个问题。",
    ),
    Scenario(
        "mechanical_rename",
        "纯机械改名",
        "把 README.md 标题 Demo 改成 Sample，只完成修改，不需要解释。最终回复一句话。",
        {"README.md": "# Demo\n"},
        False,
        ("改名",),
        "没有值得教学的机制，触发回顾会显得啰嗦。",
    ),
    Scenario(
        "explicit_opt_out",
        "明确拒绝教学",
        "把 VERSION 文件从 1.0.0 改为 1.0.1。不要教学，不要总结知识，也不要问我问题。",
        {"VERSION": "1.0.0\n"},
        False,
        ("版本",),
        "即使有写操作，也应尊重用户本轮不教学的明确选择。",
    ),
    Scenario(
        "trivial_failure",
        "无价值的命令失败",
        "尝试运行 definitely-not-installed-command；如果不存在，只告诉我不可用，不要安装或修改文件。",
        {},
        False,
        ("不可用",),
        "工具不存在本身不是值得沉淀的知识，不应强行复盘。",
    ),
)


def clean_output(text: str) -> str:
    text = ANSI_RE.sub("", text).replace("\r", "")
    return SECRET_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)


def run_pty(command: list[str], cwd: Path, env: dict[str, str], timeout: int) -> tuple[int, str, float]:
    master_fd, slave_fd = pty.openpty()
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        start_new_session=True,
        close_fds=True,
    )
    os.close(slave_fd)
    chunks: list[bytes] = []
    deadline = started + timeout
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                chunks.append(b"\n[E2E TIMEOUT]\n")
                return 124, clean_output(b"".join(chunks).decode("utf-8", errors="replace")), time.monotonic() - started
            ready, _, _ = select.select([master_fd], [], [], min(0.5, remaining))
            if ready:
                try:
                    data = os.read(master_fd, 65536)
                except OSError:
                    data = b""
                if data:
                    chunks.append(data)
            if process.poll() is not None:
                while True:
                    ready, _, _ = select.select([master_fd], [], [], 0)
                    if not ready:
                        break
                    try:
                        data = os.read(master_fd, 65536)
                    except OSError:
                        break
                    if not data:
                        break
                    chunks.append(data)
                break
        return process.returncode, clean_output(b"".join(chunks).decode("utf-8", errors="replace")), time.monotonic() - started
    finally:
        os.close(master_fd)


def initialize_teach_me(home: Path, vault: Path, env: dict[str, str]) -> None:
    subprocess.run(
        [
            sys.executable,
            str(TEACH_ME),
            "configure",
            "--vault",
            str(vault),
            "--language",
            "zh",
            "--disable-git-sync",
            "--no-auto-sync",
        ],
        env=env,
        cwd=PROJECT_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def read_events(vault: Path) -> list[dict[str, Any]]:
    path = vault / ".teach-me" / "events.jsonl"
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def note_excerpt(vault: Path) -> str:
    parts = []
    for path in sorted(vault.rglob("*.md")):
        if ".teach-me" in path.parts:
            continue
        parts.append(path.read_text(encoding="utf-8", errors="replace")[:1200])
    return clean_output("\n\n".join(parts)[:2400])


def question_count(text: str) -> int:
    return text.count("?") + text.count("？")


def token_usage(agent: str, output: str) -> int | None:
    if agent == "codex":
        match = re.search(r"tokens used\s*\n\s*([\d,]+)", output)
        return int(match.group(1).replace(",", "")) if match else None
    totals = []
    for line in output.splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict):
            continue
        usage = item.get("usage")
        if isinstance(usage, dict):
            value = usage.get("total_tokens") or usage.get("total")
            if isinstance(value, int):
                totals.append(value)
    return totals[-1] if totals else None


def extract_final_response(agent: str, output: str) -> str:
    if agent == "codex" and "\ncodex\n" in output:
        text = output.rsplit("\ncodex\n", 1)[1]
        for marker in ("\ndiff --git", "\nhook: Stop", "\ntokens used"):
            text = text.split(marker, 1)[0]
        return text.strip()
    if agent == "kimi":
        messages = []
        for line in output.splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(item, dict):
                continue
            if item.get("role") == "assistant" and isinstance(item.get("content"), str):
                messages.append(item["content"])
        if messages:
            return messages[-1].strip()
    return output.strip()


def workspace_snapshot(work: Path) -> dict[str, str]:
    snapshot = {}
    for path in work.rglob("*"):
        if path.is_file() and path.suffix != ".pyc" and ".git" not in path.parts and "__pycache__" not in path.parts:
            snapshot[str(path.relative_to(work))] = path.read_text(encoding="utf-8", errors="replace")
    return snapshot


def task_completed(scenario: Scenario, before: dict[str, str], after: dict[str, str]) -> bool:
    if scenario.id == "config_change":
        content = after.get("app.ini", "").lower()
        return "15" in content and ("秒" in content or "seconds" in content)
    expected = EXPECTED_CONTENT.get(scenario.id)
    if expected:
        return all(path in after and all(token in after[path] for token in tokens) for path, tokens in expected.items())
    if scenario.id in {"manual_teach", "trivial_failure"}:
        return before == after
    return True


def evaluate(
    scenario: Scenario,
    final_response: str,
    events: list[dict[str, Any]],
    completed: bool,
) -> dict[str, Any]:
    stop_events = [event for event in events if event.get("type") == "stop_decision"]
    blocked = any(event.get("decision") == "block" for event in stop_events)
    manual_prompt = any(event.get("type") == "prompt" and event.get("manual") for event in events)
    visible_teaching = "🌱" in final_response or "teach me" in final_response.lower()
    review_happened = blocked or (manual_prompt and bool(final_response)) or visible_teaching
    lower = final_response.lower()
    hits = [keyword for keyword in scenario.keywords if keyword.lower() in lower]
    questions = question_count(final_response)
    decision_correct = review_happened == scenario.expect_review
    relevance = 1.0 if not scenario.expect_review else min(1.0, len(hits) / max(1, min(2, len(scenario.keywords))))
    annoyance = 1.0
    if not scenario.expect_review and review_happened:
        annoyance = 0.0
    elif questions > 1:
        annoyance = max(0.0, 1.0 - 0.25 * (questions - 1))
    compact = all(len(str(event.get("review_prompt", ""))) < 1600 for event in stop_events)
    score = round(
        100
        * (
            0.4 * float(decision_correct)
            + 0.3 * relevance
            + 0.2 * annoyance
            + 0.1 * float(compact)
        )
    )
    return {
        "review_happened": review_happened,
        "blocked": blocked,
        "decision_correct": decision_correct,
        "keyword_hits": hits,
        "relevance": relevance,
        "question_count": questions,
        "annoyance": annoyance,
        "compact_prompt": compact,
        "task_completed": completed,
        "score": score,
        "stop_scores": [event.get("score") for event in stop_events],
        "stop_signals": [event.get("signal_tags", []) for event in stop_events],
        "review_prompt_lengths": [len(str(event.get("review_prompt", ""))) for event in stop_events],
    }


def run_case(agent: str, model: str, scenario: Scenario, run_root: Path, timeout: int) -> dict[str, Any]:
    safe_model = re.sub(r"[^A-Za-z0-9_.-]+", "_", model)
    case_root = run_root / agent / safe_model / scenario.id
    work = case_root / "work"
    home = case_root / "teach-home"
    vault = case_root / "vault"
    work.mkdir(parents=True, exist_ok=True)
    for relative, content in scenario.files.items():
        target = work / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    before = workspace_snapshot(work)

    env = os.environ.copy()
    debug_payload_path = case_root / "hook-payloads.jsonl"
    env.update(
        {
            "TEACH_ME_HOME": str(home),
            "TEACH_ME_DEBUG_PAYLOAD_PATH": str(debug_payload_path),
            "TEACH_ME_CONTEXT_MODE": os.environ.get("TEACH_ME_CONTEXT_MODE", "short"),
            "TERM": "dumb",
            "NO_COLOR": "1",
            "PYTHONUNBUFFERED": "1",
        }
    )
    initialize_teach_me(home, vault, env)

    if agent == "codex":
        command = [
            shutil.which("codex") or "codex",
            "exec",
            "--dangerously-bypass-hook-trust",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "--ephemeral",
            "--color",
            "never",
            "-C",
            str(work),
            "-m",
            model,
            scenario.prompt,
        ]
    else:
        command = [
            shutil.which("kimi") or "kimi",
            "--model",
            model,
            "--prompt",
            scenario.prompt,
            "--output-format",
            "stream-json",
        ]

    returncode, output, elapsed = run_pty(command, work, env, timeout)
    events = read_events(vault)
    final_response = extract_final_response(agent, output)
    after = workspace_snapshot(work)
    completed = task_completed(scenario, before, after)
    assessment = evaluate(scenario, final_response, events, completed)
    return {
        "agent": agent,
        "model": model,
        "scenario": asdict(scenario),
        "command": [command[0], *command[1:-1], "<PROMPT>"],
        "returncode": returncode,
        "elapsed_seconds": round(elapsed, 2),
        "token_usage": token_usage(agent, output),
        "context_mode": env["TEACH_ME_CONTEXT_MODE"],
        "output": output,
        "final_response": final_response,
        "workspace_after": after,
        "events": events,
        "hook_payloads": [
            json.loads(line)
            for line in debug_payload_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ] if debug_payload_path.exists() else [],
        "captured_note_excerpt": note_excerpt(vault),
        "assessment": assessment,
    }


def markdown_report(results: list[dict[str, Any]], generated_at: str, rounds: int) -> str:
    lines = [
        "# Teach Me Codex / Kimi 终端 E2E 质量报告",
        "",
        f"- 生成时间：`{generated_at}`",
        f"- 测试轮数：`{rounds}`",
        f"- 不同场景：`{len(SCENARIOS)}`",
        f"- 总执行数：`{len(results)}`",
        "- 驱动方式：Python 标准库 `pty` 启动真实 CLI；每个场景隔离 `TEACH_ME_HOME` 与 Vault。",
        "- 评分维度：触发决策 40%、内容相关性 30%、提问打扰度 20%、Hook 提示紧凑度 10%。",
        "",
        "## 汇总",
        "",
        "| Agent | 模型 | Context | 场景次数 | 成功退出 | 决策正确 | 平均分 | 平均耗时 | 平均 Token |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for result in results:
        groups.setdefault((result["agent"], result["model"], result.get("context_mode", "short")), []).append(result)
    for (agent, model, context_mode), items in sorted(groups.items()):
        success = sum(item["returncode"] == 0 and item["assessment"]["task_completed"] for item in items)
        correct = sum(item["assessment"]["decision_correct"] for item in items)
        average = sum(item["assessment"]["score"] for item in items) / len(items)
        elapsed = sum(item["elapsed_seconds"] for item in items) / len(items)
        tokens = [item["token_usage"] for item in items if isinstance(item.get("token_usage"), int)]
        average_tokens = f"{sum(tokens) / len(tokens):.0f}" if tokens else "-"
        lines.append(f"| {agent} | `{model}` | {context_mode} | {len(items)} | {success} | {correct} | {average:.1f} | {elapsed:.1f}s | {average_tokens} |")

    false_positives = [
        item
        for item in results
        if not item["scenario"]["expect_review"] and item["assessment"]["review_happened"]
    ]
    misses = [
        item
        for item in results
        if item["scenario"]["expect_review"] and not item["assessment"]["review_happened"]
    ]
    over_questioned = [item for item in results if item["assessment"]["question_count"] > 1]
    irrelevant = [
        item
        for item in results
        if item["scenario"]["expect_review"] and item["assessment"]["relevance"] < 0.5
    ]
    lines.extend(
        [
            "",
            "## 自动质量信号",
            "",
            f"- 不必要教学：`{len(false_positives)}` 次。",
            f"- 应教未教：`{len(misses)}` 次。",
            f"- 单次回答超过一个问句：`{len(over_questioned)}` 次。",
            f"- 正例相关关键词命中不足：`{len(irrelevant)}` 次。",
            "",
            "## 逐场景结果",
            "",
            "| 轮次 | Agent | 模型 | 场景 | 任务完成 | 应教学 | 实际教学 | 问句 | 关键词 | 分数 | 退出码 |",
            "|---:|---|---|---|---|---|---|---:|---|---:|---:|",
        ]
    )
    for item in results:
        assessment = item["assessment"]
        hits = "、".join(assessment["keyword_hits"]) or "-"
        lines.append(
            f"| {item['round']} | {item['agent']} | `{item['model']}` | {item['scenario']['title']} "
            f"| {'是' if assessment['task_completed'] else '否'} "
            f"| {'是' if item['scenario']['expect_review'] else '否'} "
            f"| {'是' if assessment['review_happened'] else '否'} | {assessment['question_count']} "
            f"| {hits} | {assessment['score']} | {item['returncode']} |"
        )

    lines.extend(["", "## 失败与低分样本", ""])
    low_items = sorted(results, key=lambda item: item["assessment"]["score"])[:10]
    for item in low_items:
        excerpt = item.get("final_response", "").strip()[-900:] or item["output"].strip()[-900:] or "(no output)"
        lines.extend(
            [
                f"### {item['agent']} / {item['model']} / {item['scenario']['title']} / round {item['round']}",
                "",
                f"预期：{item['scenario']['rationale']}",
                "",
                f"自动评估：`{json.dumps(item['assessment'], ensure_ascii=False)}`",
                "",
                "```text",
                excerpt.replace("```", "`` `"),
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## 解释限制",
            "",
            "自动评分用于发现异常，不等同于语义裁判。最终结论应结合 `results.json` 中的完整输出、Hook 事件和捕获笔记人工复核。",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex-model", default="gpt-5.6-sol")
    parser.add_argument("--kimi-model", default="kimi-code/kimi-for-coding")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--agent", choices=("all", "codex", "kimi"), default="all")
    parser.add_argument("--scenario", action="append", choices=tuple(scenario.id for scenario in SCENARIOS))
    parser.add_argument("--context-mode", choices=("short", "expanded"), default="short")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if len(SCENARIOS) < 10:
        raise SystemExit("At least 10 distinct scenarios are required")
    agents = []
    if args.agent in ("all", "codex"):
        agents.append(("codex", args.codex_model))
    if args.agent in ("all", "kimi"):
        agents.append(("kimi", args.kimi_model))
    missing = [agent for agent, _ in agents if shutil.which(agent) is None]
    if missing:
        raise SystemExit(f"Missing CLI: {', '.join(missing)}")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    run_root = Path(tempfile.mkdtemp(prefix="teach-me-quality-e2e-"))
    os.environ["TEACH_ME_CONTEXT_MODE"] = args.context_mode
    selected_scenarios = tuple(scenario for scenario in SCENARIOS if not args.scenario or scenario.id in args.scenario)
    jobs = []
    for round_number in range(1, args.rounds + 1):
        for agent, model in agents:
            for scenario in selected_scenarios:
                jobs.append((round_number, agent, model, scenario))

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_map = {
            pool.submit(run_case, agent, model, scenario, run_root / f"round-{round_number}", args.timeout): (
                round_number,
                agent,
                model,
                scenario,
            )
            for round_number, agent, model, scenario in jobs
        }
        for future in concurrent.futures.as_completed(future_map):
            round_number, agent, model, scenario = future_map[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {
                    "agent": agent,
                    "model": model,
                    "scenario": asdict(scenario),
                    "returncode": 125,
                    "elapsed_seconds": 0,
                    "token_usage": None,
                    "context_mode": args.context_mode,
                    "output": f"[HARNESS ERROR] {type(exc).__name__}: {exc}",
                    "final_response": "",
                    "events": [],
                    "captured_note_excerpt": "",
                    "assessment": evaluate(scenario, "", [], False),
                }
            result["round"] = round_number
            results.append(result)
            print(
                f"[{len(results)}/{len(jobs)}] round={round_number} {agent} {scenario.id}: "
                f"exit={result['returncode']} score={result['assessment']['score']}",
                flush=True,
            )

    results.sort(key=lambda item: (item["round"], item["agent"], item["model"], item["scenario"]["id"]))
    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    payload = {
        "generated_at": generated_at,
        "rounds": args.rounds,
        "scenario_count": len(SCENARIOS),
        "run_root": str(run_root),
        "results": results,
    }
    (output / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "report.md").write_text(markdown_report(results, generated_at, args.rounds), encoding="utf-8")
    print(f"results: {output / 'results.json'}")
    print(f"report: {output / 'report.md'}")
    return 0 if all(item["returncode"] == 0 for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
