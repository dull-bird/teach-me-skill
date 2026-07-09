#!/usr/bin/env python3
"""
Teach Me Exam — adaptive quiz and test generator.

Plans an exam from the learner portrait, then records graded results back to the
vault. The skill selects concepts and formats; the AI agent generates the actual
questions and collects answers.

Usage:
    python3 exam.py plan --time 15                       # plan a 15-minute test
    python3 exam.py plan --time 30 --topic Python        # focus on Python
    python3 exam.py plan --type quiz --formats mcq,tf    # quick quiz
    python3 exam.py grade < exam-results.json            # record results
    python3 exam.py history                              # past exam sessions
    python3 exam.py topics                               # available topics
    python3 exam.py stats                                # exam statistics
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


MASTERY_ORDER = [
    "unknown",
    "seen",
    "explained",
    "practiced",
    "transferable",
    "confident",
]
MASTERY_SCORE = {name: idx for idx, name in enumerate(MASTERY_ORDER)}
PROFILE_FOLDER = "07_Learning_Profile"

# Time budget defaults.
QUIZ_MAX_MINUTES = 10
TEST_MAX_MINUTES = 30

# Questions per exam type.
TYPE_QUESTION_COUNT = {
    "quiz": 4,
    "test": 7,
    "exam": 12,
}

# Default formats per type.
TYPE_DEFAULT_FORMATS = {
    "quiz": ["tf", "mcq"],
    "test": ["tf", "mcq", "short"],
    "exam": ["tf", "mcq", "short", "coding"],
}

# Days until next review for each mastery level.
REVIEW_DAYS = {
    "unknown": 1,
    "seen": 1,
    "explained": 3,
    "practiced": 6,
    "transferable": 14,
    "confident": 30,
}


# ---------------------------------------------------------------------------
# Config / state utilities (replicated from teach-me conventions)
# ---------------------------------------------------------------------------


def home_dir() -> Path:
    raw = os.environ.get("TEACH_ME_HOME", "~/.teach_me_skill")
    return Path(raw).expanduser().resolve()


def config_path() -> Path:
    return home_dir() / "config.json"


def default_user_config(user_id: str = "default") -> dict[str, Any]:
    vault = home_dir() / "vault" if user_id == "default" else home_dir() / "users" / user_id / "vault"
    return {
        "name": user_id,
        "github": None,
        "vault_path": str(vault),
        "language": "auto",
        "max_notes_per_phase": 3,
        "git_sync": {
            "enabled": False,
            "remote": "",
            "branch": "main",
            "auto_sync": False,
        },
        "initialized": False,
    }


def default_config() -> dict[str, Any]:
    return {
        "version": 2,
        "current_user": "default",
        "users": {"default": default_user_config()},
    }


def migrate_v1_to_v2(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("version") == 2:
        return config
    user_cfg = default_user_config()
    for key in ("vault_path", "language", "max_notes_per_phase", "initialized"):
        if key in config:
            user_cfg[key] = config[key]
    git_sync = config.get("git_sync", {})
    if git_sync:
        user_cfg["git_sync"] = {
            "enabled": bool(git_sync.get("enabled", False)),
            "remote": str(git_sync.get("remote", "")),
            "branch": str(git_sync.get("branch", "main")),
            "auto_sync": bool(git_sync.get("auto_sync", False)),
        }
    return {
        "version": 2,
        "current_user": "default",
        "users": {"default": user_cfg},
    }


def load_config() -> dict[str, Any]:
    path = config_path()
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            config = default_config()
    else:
        config = default_config()
    return migrate_v1_to_v2(config)


def resolve_user_config(config: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
    uid = user_id or config.get("current_user", "default")
    users = config.get("users", {})
    if uid not in users:
        uid = "default"
    user_cfg = dict(users.get(uid, default_user_config(uid)))
    base = default_user_config(uid)
    base.update(user_cfg)
    base["_user_id"] = uid
    base["_top_level"] = config
    return base


def vault_dir(user_cfg: dict[str, Any]) -> Path:
    raw = user_cfg.get("vault_path", "~/.teach_me_skill/vault")
    return Path(raw).expanduser().resolve()


def state_path(user_cfg: dict[str, Any]) -> Path:
    return vault_dir(user_cfg) / ".teach-me" / "learning-state.json"


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today() -> datetime:
    return datetime.now(timezone.utc)


def detect_language(user_cfg: dict[str, Any]) -> str:
    lang = str(user_cfg.get("language", "auto")).lower()
    if lang != "auto":
        return lang
    return "zh"


# ---------------------------------------------------------------------------
# Exam planning
# ---------------------------------------------------------------------------


def collect_exam_items(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a flat list of reviewable items from concepts and knowledge_tree."""
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for name, data in state.get("concepts", {}).items():
        if name in seen:
            continue
        seen.add(name)
        item = dict(data)
        item["name"] = name
        item.setdefault("type", "concept")
        item.setdefault("score", 0)
        item.setdefault("mastery", "unknown")
        items.append(item)

    for name, data in state.get("knowledge_tree", {}).items():
        if name in seen:
            existing = next(i for i in items if i["name"] == name)
            for key in ("probes", "gaps", "prerequisites", "children", "misconceptions", "evidence"):
                if key in data:
                    existing[key] = data[key]
            continue
        seen.add(name)
        item = dict(data)
        item["name"] = name
        item.setdefault("type", "concept")
        item.setdefault("score", 0)
        item.setdefault("mastery", "unknown")
        items.append(item)

    return items


def matches_topic(item: dict[str, Any], topic: str) -> bool:
    """Case-insensitive substring match against name, projects, prerequisites, or gaps."""
    topic = topic.lower()
    haystacks = [
        item.get("name", ""),
        " ".join(str(p) for p in item.get("projects", [])),
        " ".join(str(p) for p in item.get("prerequisites", [])),
        " ".join(str(g) for g in item.get("gaps", [])),
        " ".join(str(c) for c in item.get("children", [])),
    ]
    return any(topic in haystack.lower() for haystack in haystacks)


def infer_type_from_time(time_budget: int) -> str:
    if time_budget <= QUIZ_MAX_MINUTES:
        return "quiz"
    if time_budget <= TEST_MAX_MINUTES:
        return "test"
    return "exam"


def parse_formats(formats_str: str | None, exam_type: str) -> list[str]:
    if not formats_str:
        return list(TYPE_DEFAULT_FORMATS[exam_type])
    allowed = {"mcq", "tf", "short", "coding"}
    parsed = [f.strip().lower() for f in formats_str.split(",") if f.strip()]
    parsed = [f for f in parsed if f in allowed]
    if not parsed:
        return list(TYPE_DEFAULT_FORMATS[exam_type])
    return parsed


def looks_code_related(item: dict[str, Any]) -> bool:
    """Simple heuristic: does this concept likely benefit from a coding question?"""
    text = " ".join(
        [
            item.get("name", ""),
            item.get("type", ""),
            " ".join(str(p) for p in item.get("projects", [])),
        ]
    ).lower()
    code_hints = [
        "python", "javascript", "typescript", "rust", "go", "java", "c++",
        "api", "function", "algorithm", "data structure", "regex", "sql",
        "docker", "kubernetes", "bash", "shell", "cli", "test", "pytest",
        "fastapi", "django", "react", "vue", "angular", "node",
    ]
    return any(hint in text for hint in code_hints)


def assign_format(item: dict[str, Any], available_formats: list[str], index: int) -> str:
    """Pick a question format for a concept."""
    if "coding" in available_formats and looks_code_related(item):
        return "coding"
    if "short" in available_formats and (item.get("probes") or item.get("gaps")):
        return "short"
    if "mcq" in available_formats and index % 2 == 0:
        return "mcq"
    if "tf" in available_formats:
        return "tf"
    # Fallback to first available format.
    return available_formats[0]


def select_concepts(
    items: list[dict[str, Any]],
    time_budget: int,
    exam_type: str,
    formats: list[str],
) -> list[dict[str, Any]]:
    """Select concepts and assign a format to each."""
    count = TYPE_QUESTION_COUNT[exam_type]
    # Sort by mastery score ascending (weakest first), then by last_seen recency.
    sorted_items = sorted(
        items,
        key=lambda i: (
            MASTERY_SCORE.get(str(i.get("mastery", "unknown")), 0),
            i.get("last_seen", ""),
        ),
    )
    selected = sorted_items[:count]

    concepts: list[dict[str, Any]] = []
    for idx, item in enumerate(selected):
        fmt = assign_format(item, formats, idx)
        concepts.append(
            {
                "name": item["name"],
                "type": item.get("type", "concept"),
                "mastery": item.get("mastery", "unknown"),
                "format": fmt,
                "why": f"{item.get('mastery', 'unknown')} mastery, selected from {len(items)} candidates",
            }
        )
    return concepts


def build_prompt_for_ai(
    user_cfg: dict[str, Any],
    time_budget: int,
    exam_type: str,
    formats: list[str],
    concepts: list[dict[str, Any]],
) -> str:
    lang = detect_language(user_cfg)
    if lang.startswith("zh"):
        prompt = (
            f"请为当前用户生成一份 {time_budget} 分钟的{exam_type}。\n"
            f"题型：{', '.join(formats)}。\n"
            f"覆盖以下 {len(concepts)} 个知识点（优先薄弱项）：\n"
        )
        for c in concepts:
            prompt += f"- {c['name']}（{c['type']}，掌握度 {c['mastery']}）→ 用 {c['format']} 题型\n"
        prompt += (
            "\n要求：\n"
            "1. 每道题标明题型、分值和预计答题时间。\n"
            "2. 选择题和判断题要附带正确答案和简要解析。\n"
            "3. 简答题和上机题要给出评分要点。\n"
            "4. 上机题要求用户在编辑器写代码，然后粘贴回答案。\n"
            "5. 试卷顶部说明总分、建议用时和作答方式。\n"
        )
    else:
        prompt = (
            f"Generate a {time_budget}-minute {exam_type} for the current user.\n"
            f"Formats: {', '.join(formats)}.\n"
            f"Cover these {len(concepts)} concepts (weakest first):\n"
        )
        for c in concepts:
            prompt += f"- {c['name']} ({c['type']}, mastery {c['mastery']}) → use {c['format']}\n"
        prompt += (
            "\nRequirements:\n"
            "1. Label each question with format, points, and estimated time.\n"
            "2. MCQ and true/false questions must include the correct answer and a brief explanation.\n"
            "3. Short-answer and coding questions must include grading rubrics.\n"
            "4. For coding questions, instruct the user to write code in their editor and paste it back.\n"
            "5. Begin the exam with total points, suggested time, and instructions.\n"
        )
    return prompt


def plan_exam(
    user_cfg: dict[str, Any],
    time_budget: int,
    topic: str | None,
    requested_type: str | None,
    requested_formats: str | None,
) -> dict[str, Any]:
    state = read_json(state_path(user_cfg)) or {"version": 1}
    items = collect_exam_items(state)

    if topic:
        items = [i for i in items if matches_topic(i, topic)]

    exam_type = requested_type or infer_type_from_time(time_budget)
    if exam_type not in TYPE_QUESTION_COUNT:
        exam_type = infer_type_from_time(time_budget)

    formats = parse_formats(requested_formats, exam_type)
    concepts = select_concepts(items, time_budget, exam_type, formats)

    session_id = f"exam-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    return {
        "session_id": session_id,
        "user": user_cfg["_user_id"],
        "time_budget_minutes": time_budget,
        "type": exam_type,
        "formats": formats,
        "topic": topic,
        "concepts": concepts,
        "estimated_questions": len(concepts),
        "prompt_for_ai": build_prompt_for_ai(user_cfg, time_budget, exam_type, formats, concepts),
    }


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------


def clamp_mastery_index(idx: int) -> int:
    return max(0, min(len(MASTERY_ORDER) - 1, idx))


def review_days_for_mastery(mastery: str) -> int:
    return REVIEW_DAYS.get(mastery, 1)


def update_mastery(state: dict[str, Any], result: dict[str, Any]) -> None:
    """Update a concept or knowledge-tree node based on one exam result."""
    name = str(result.get("name", "")).strip()
    if not name:
        return

    correct = bool(result.get("correct"))
    confidence = float(result.get("confidence", 0.5))

    target: dict[str, Any] | None = None
    location: str | None = None
    for section in ("concepts", "knowledge_tree"):
        section_data = state.get(section, {})
        if name in section_data:
            target = section_data[name]
            location = section
            break

    if target is None:
        return

    current_mastery = str(target.get("mastery", "unknown"))
    if current_mastery not in MASTERY_SCORE:
        current_mastery = "unknown"
    current_idx = MASTERY_SCORE[current_mastery]

    if correct and confidence >= 0.8:
        new_idx = clamp_mastery_index(current_idx + 1)
    elif correct:
        new_idx = current_idx
    else:
        new_idx = clamp_mastery_index(current_idx - 1)

    new_mastery = MASTERY_ORDER[new_idx]
    target["mastery"] = new_mastery
    target["score"] = MASTERY_SCORE[new_mastery]
    target["last_seen"] = now_iso()

    if location == "concepts":
        interval = review_days_for_mastery(new_mastery)
        target["next_review"] = (today().date() + timedelta(days=interval)).isoformat()
        target["review_interval_days"] = interval
    elif location == "knowledge_tree":
        target["last_assessed"] = now_iso()
        if not correct:
            target["needs_probe"] = True


def record_exam(state: dict[str, Any], plan: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    correct = sum(1 for r in results if r.get("correct"))
    accuracy = correct / total if total else 0.0

    exam_record = {
        "session_id": plan.get("session_id"),
        "timestamp": now_iso(),
        "time_budget_minutes": plan.get("time_budget_minutes"),
        "type": plan.get("type"),
        "formats": plan.get("formats"),
        "topic": plan.get("topic"),
        "results": results,
        "summary": {
            "total": total,
            "correct": correct,
            "accuracy": round(accuracy, 2),
        },
    }

    state.setdefault("exams", []).append(exam_record)
    return exam_record


# ---------------------------------------------------------------------------
# Markdown rewrites (kept consistent with teach_me.py)
# ---------------------------------------------------------------------------


def wikilink(title: str) -> str:
    return f"[[{title}]]"


def listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def rewrite_knowledge_tree(user_cfg: dict[str, Any], state: dict[str, Any]) -> None:
    tree = state.get("knowledge_tree", {})
    lines = ["# Knowledge Tree", ""]
    if not tree:
        lines.append("No assessed concepts yet.")
    else:
        lines.extend(
            [
                "This file is generated from Teach Me's learning state. It tracks observed mastery, prerequisite gaps, and probe questions.",
                "",
                "## Weak Or Unknown Nodes",
                "",
            ]
        )
        weak = sorted(
            tree.items(),
            key=lambda pair: (
                MASTERY_SCORE.get(str(pair[1].get("mastery", "unknown")), 0),
                pair[0].lower(),
            ),
        )
        for title, node in weak[:20]:
            mastery = node.get("mastery", "unknown")
            needs_probe = "needs probe" if node.get("needs_probe") else "observed"
            lines.append(f"- {wikilink(title)} - {mastery}, {needs_probe}")

        lines.extend(["", "## Nodes", ""])
        for title in sorted(tree):
            node = tree[title]
            lines.extend(
                [
                    f"### {title}",
                    "",
                    f"- Mastery: {node.get('mastery', 'unknown')}",
                    f"- Confidence: {node.get('confidence', 0.0):.2f}",
                    f"- Needs probe: {str(bool(node.get('needs_probe'))).lower()}",
                ]
            )
            for key, label in [
                ("prerequisites", "Prerequisites"),
                ("children", "Children"),
                ("gaps", "Gaps"),
                ("probes", "Probe questions"),
            ]:
                values = listify(node.get(key))
                if values:
                    if key in ("prerequisites", "children"):
                        lines.append(f"- {label}: " + ", ".join(wikilink(v) for v in values))
                    else:
                        lines.append(f"- {label}: " + "; ".join(values))
            evidence = node.get("evidence", [])[-3:]
            if evidence:
                lines.append("- Evidence:")
                for entry in evidence:
                    stamp = str(entry.get("timestamp", ""))[:10]
                    summary = str(entry.get("summary", "")).strip()
                    if summary:
                        lines.append(f"  - {stamp}: {summary}")
            lines.append("")

    tree_path = vault_dir(user_cfg) / PROFILE_FOLDER / "Knowledge_Tree.md"
    tree_path.parent.mkdir(parents=True, exist_ok=True)
    tree_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def rewrite_index(user_cfg: dict[str, Any], state: dict[str, Any]) -> None:
    vault = vault_dir(user_cfg)
    total_concepts = len(state.get("concepts", {}))
    total_tree = len(state.get("knowledge_tree", {}))
    exams = state.get("exams", [])

    lines = [
        "# Learning Index",
        "",
        f"- Concepts: {total_concepts}",
        f"- Knowledge-tree nodes: {total_tree}",
        f"- Exam sessions: {len(exams)}",
        "",
        "## Learning Profile",
        "",
        f"- [[{PROFILE_FOLDER}/Knowledge_Tree]]",
    ]
    if exams:
        lines.append(f"- [[{PROFILE_FOLDER}/Exam_History]]")
    lines.append("")

    (vault / "00_Index.md").parent.mkdir(parents=True, exist_ok=True)
    (vault / "00_Index.md").write_text("\n".join(lines), encoding="utf-8")


def rewrite_exam_history(user_cfg: dict[str, Any], state: dict[str, Any]) -> None:
    exams = state.get("exams", [])
    lines = ["# Exam History", ""]
    if not exams:
        lines.append("No exam sessions yet.")
    else:
        lines.append(f"Total sessions: {len(exams)}")
        lines.append("")
        for exam in reversed(exams[-20:]):
            sid = exam.get("session_id", "unknown")
            ts = exam.get("timestamp", "")[:16]
            typ = exam.get("type", "unknown")
            topic = exam.get("topic") or "all topics"
            summary = exam.get("summary", {})
            total = summary.get("total", 0)
            correct = summary.get("correct", 0)
            accuracy = summary.get("accuracy", 0.0)
            lines.append(
                f"- **{sid}** ({ts}) — {typ} on `{topic}` — "
                f"{correct}/{total} correct ({accuracy:.0%})"
            )
    path = vault_dir(user_cfg) / PROFILE_FOLDER / "Exam_History.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def cmd_plan(args: argparse.Namespace) -> int:
    top_config = load_config()
    user_cfg = resolve_user_config(top_config, args.user)

    if not user_cfg.get("initialized"):
        lang = detect_language(user_cfg)
        msg = (
            "Teach Me 尚未初始化。请先运行 teach_me.py configure。"
            if lang.startswith("zh")
            else "Teach Me is not initialized. Run teach_me.py configure first."
        )
        print(msg, file=sys.stderr)
        return 2

    time_budget = args.time
    if time_budget <= 0:
        print("Time budget must be positive.", file=sys.stderr)
        return 1

    plan = plan_exam(
        user_cfg,
        time_budget=time_budget,
        topic=args.topic,
        requested_type=args.type,
        requested_formats=args.formats,
    )

    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        lang = detect_language(user_cfg)
        if lang.startswith("zh"):
            print(f"## 考试计划（{plan['type']}）")
            print(f"- 时长：{plan['time_budget_minutes']} 分钟")
            print(f"- 主题：{plan['topic'] or '全部'}")
            print(f"- 题型：{', '.join(plan['formats'])}")
            print(f"- 预计题数：{plan['estimated_questions']}")
            print(f"- session_id：`{plan['session_id']}`")
            print("")
            print("覆盖知识点：")
            for c in plan["concepts"]:
                print(f"- {c['name']}（{c['mastery']}）→ {c['format']}")
            print("")
            print("AI 生成提示已包含在 JSON 输出中。用 `--json` 查看。")
        else:
            print(f"## Exam plan ({plan['type']})")
            print(f"- Time: {plan['time_budget_minutes']} minutes")
            print(f"- Topic: {plan['topic'] or 'all'}")
            print(f"- Formats: {', '.join(plan['formats'])}")
            print(f"- Estimated questions: {plan['estimated_questions']}")
            print(f"- session_id: `{plan['session_id']}`")
            print("")
            print("Concepts:")
            for c in plan["concepts"]:
                print(f"- {c['name']} ({c['mastery']}) → {c['format']}")
            print("")
            print("AI prompt included in JSON output. Use `--json` to see it.")
    return 0


def cmd_grade(args: argparse.Namespace) -> int:
    top_config = load_config()
    user_cfg = resolve_user_config(top_config, args.user)
    lang = detect_language(user_cfg)

    if not user_cfg.get("initialized"):
        msg = (
            "Teach Me 尚未初始化。请先运行 teach_me.py configure。"
            if lang.startswith("zh")
            else "Teach Me is not initialized. Run teach_me.py configure first."
        )
        print(msg, file=sys.stderr)
        return 2

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Invalid result JSON: {exc}", file=sys.stderr)
        return 1

    state = read_json(state_path(user_cfg)) or {"version": 1}
    results = payload.get("results", [])
    if not isinstance(results, list) or not results:
        print("No results provided.", file=sys.stderr)
        return 1

    # Find the matching plan or use the payload's plan.
    plan = payload.get("plan", {})
    session_id = plan.get("session_id") or payload.get("session_id")
    if not session_id:
        session_id = f"exam-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        plan["session_id"] = session_id

    for result in results:
        update_mastery(state, result)

    exam_record = record_exam(state, plan, results)
    write_json(state_path(user_cfg), state)
    rewrite_knowledge_tree(user_cfg, state)
    rewrite_exam_history(user_cfg, state)
    rewrite_index(user_cfg, state)

    if args.json:
        print(json.dumps(exam_record, ensure_ascii=False, indent=2))
    else:
        if lang.startswith("zh"):
            print(
                f"已记录考试 {session_id}："
                f"{exam_record['summary']['correct']}/{exam_record['summary']['total']} 正确 "
                f"（{exam_record['summary']['accuracy']:.0%}）"
            )
        else:
            print(
                f"Recorded exam {session_id}: "
                f"{exam_record['summary']['correct']}/{exam_record['summary']['total']} correct "
                f"({exam_record['summary']['accuracy']:.0%})"
            )
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    top_config = load_config()
    user_cfg = resolve_user_config(top_config, args.user)
    state = read_json(state_path(user_cfg)) or {"version": 1}
    exams = state.get("exams", [])

    if args.json:
        print(json.dumps(exams, ensure_ascii=False, indent=2))
        return 0

    lang = detect_language(user_cfg)
    if lang.startswith("zh"):
        if not exams:
            print("还没有考试记录。")
            return 0
        print("## 考试历史")
        for exam in reversed(exams):
            summary = exam.get("summary", {})
            print(
                f"- {exam.get('session_id')} ({exam.get('timestamp', '')[:16]}) — "
                f"{exam.get('type')} — {summary.get('correct', 0)}/{summary.get('total', 0)} "
                f"({summary.get('accuracy', 0):.0%})"
            )
    else:
        if not exams:
            print("No exam sessions yet.")
            return 0
        print("## Exam history")
        for exam in reversed(exams):
            summary = exam.get("summary", {})
            print(
                f"- {exam.get('session_id')} ({exam.get('timestamp', '')[:16]}) — "
                f"{exam.get('type')} — {summary.get('correct', 0)}/{summary.get('total', 0)} "
                f"({summary.get('accuracy', 0):.0%})"
            )
    return 0


def cmd_topics(args: argparse.Namespace) -> int:
    top_config = load_config()
    user_cfg = resolve_user_config(top_config, args.user)
    state = read_json(state_path(user_cfg)) or {"version": 1}

    topics: set[str] = set()
    for name, data in {**state.get("concepts", {}), **state.get("knowledge_tree", {})}.items():
        topics.add(name)
        for project in data.get("projects", []):
            topics.add(str(project))

    sorted_topics = sorted(topics, key=lambda s: s.lower())
    if args.json:
        print(json.dumps(sorted_topics, ensure_ascii=False, indent=2))
        return 0

    lang = detect_language(user_cfg)
    if lang.startswith("zh"):
        print("## 可选主题")
    else:
        print("## Available topics")
    for t in sorted_topics:
        print(f"- {t}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    top_config = load_config()
    user_cfg = resolve_user_config(top_config, args.user)
    state = read_json(state_path(user_cfg)) or {"version": 1}
    exams = state.get("exams", [])

    total_sessions = len(exams)
    total_questions = sum(e.get("summary", {}).get("total", 0) for e in exams)
    total_correct = sum(e.get("summary", {}).get("correct", 0) for e in exams)
    accuracy = total_correct / total_questions if total_questions else 0.0

    weak_items = collect_exam_items(state)
    weak_items = [i for i in weak_items if MASTERY_SCORE.get(str(i.get("mastery", "unknown")), 0) <= MASTERY_SCORE["seen"]]
    weak_items = sorted(weak_items, key=lambda i: MASTERY_SCORE.get(str(i.get("mastery", "unknown")), 0))[:8]

    stats = {
        "total_sessions": total_sessions,
        "total_questions": total_questions,
        "total_correct": total_correct,
        "accuracy": round(accuracy, 2),
        "weak_concepts": [i["name"] for i in weak_items],
    }

    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0

    lang = detect_language(user_cfg)
    if lang.startswith("zh"):
        print("## 考试统计")
        print(f"- 考试次数：{total_sessions}")
        print(f"- 总题数：{total_questions}")
        print(f"- 正确数：{total_correct}")
        print(f"- 总正确率：{accuracy:.0%}")
        if weak_items:
            print("- 薄弱概念：" + ", ".join(f"`{i['name']}`" for i in weak_items))
    else:
        print("## Exam statistics")
        print(f"- Sessions: {total_sessions}")
        print(f"- Total questions: {total_questions}")
        print(f"- Correct: {total_correct}")
        print(f"- Accuracy: {accuracy:.0%}")
        if weak_items:
            print("- Weak concepts: " + ", ".join(f"`{i['name']}`" for i in weak_items))
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="exam.py",
        description="Teach Me Exam — adaptive quiz and test generator.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_flags(p: argparse.ArgumentParser) -> None:
        p.add_argument("--user", help="Target user ID (defaults to current_user)")
        p.add_argument("--json", action="store_true", help="Output structured JSON")

    plan_parser = subparsers.add_parser("plan", help="Generate an exam plan")
    plan_parser.add_argument("--time", type=int, required=True, help="Available time in minutes")
    plan_parser.add_argument("--topic", help="Filter concepts by topic substring")
    plan_parser.add_argument(
        "--type",
        choices=["quiz", "test", "exam"],
        help="Exam type (default inferred from time)",
    )
    plan_parser.add_argument(
        "--formats",
        help="Comma-separated formats: mcq,tf,short,coding",
    )
    add_common_flags(plan_parser)
    plan_parser.set_defaults(func=cmd_plan)

    grade_parser = subparsers.add_parser("grade", help="Record graded exam results from stdin")
    add_common_flags(grade_parser)
    grade_parser.set_defaults(func=cmd_grade)

    history_parser = subparsers.add_parser("history", help="List past exam sessions")
    add_common_flags(history_parser)
    history_parser.set_defaults(func=cmd_history)

    topics_parser = subparsers.add_parser("topics", help="List available exam topics")
    add_common_flags(topics_parser)
    topics_parser.set_defaults(func=cmd_topics)

    stats_parser = subparsers.add_parser("stats", help="Show exam statistics")
    add_common_flags(stats_parser)
    stats_parser.set_defaults(func=cmd_stats)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
