#!/usr/bin/env python3
"""
Teach Me Recap — spaced-repetition review companion.

Uses SM-2-like scheduling over the concepts and knowledge-tree nodes stored
in ~/.teach_me_skill/vault/.teach-me/learning-state.json.

Usage:
    python3 recap.py due              # list items due today
    python3 recap.py next             # show the next due item
    python3 recap.py rate "Title" good # record a review result
    python3 recap.py stats            # review statistics
    python3 recap.py manual           # print operation manual
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def home_dir() -> Path:
    raw = os.environ.get("TEACH_ME_HOME", "~/.teach_me_skill")
    return Path(raw).expanduser().resolve()


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
    """Convert legacy single-user config to v2 multi-user config."""
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
    path = home_dir() / "config.json"
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
    """Return the active user config, falling back to current_user then default."""
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


def learning_state_path(user_cfg: dict[str, Any]) -> Path:
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
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def today() -> date:
    return datetime.now(timezone.utc).date()


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def item_sort_key(item: dict[str, Any]) -> tuple:
    """Lower tuple = higher priority for review."""
    next_review = parse_date(item.get("next_review"))
    if next_review is None:
        next_review = date.min
    # Due or overdue first, then by mastery score (lower = weaker), then by importance
    mastery_score = item.get("score", 0)
    importance = item.get("importance", 5)
    return (next_review, mastery_score, -importance)


def collect_review_items(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a flat list of reviewable items from concepts and knowledge_tree."""
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    concepts = state.get("concepts", {})
    for name, data in concepts.items():
        if name in seen:
            continue
        seen.add(name)
        item = dict(data)
        item["name"] = name
        item.setdefault("type", "concept")
        item.setdefault("score", 0)
        item.setdefault("ease", 2.5)
        item.setdefault("review_interval_days", 0)
        item.setdefault("last_seen", None)
        item.setdefault("next_review", None)
        item.setdefault("importance", 5)
        items.append(item)

    tree = state.get("knowledge_tree", {})
    for name, data in tree.items():
        if name in seen:
            # Merge probes/gaps/children/prerequisites from tree into concept item
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
        item.setdefault("ease", 2.5)
        item.setdefault("review_interval_days", 0)
        item.setdefault("last_seen", None)
        item.setdefault("next_review", None)
        item.setdefault("importance", 5)
        items.append(item)

    return items


def is_due(item: dict[str, Any]) -> bool:
    next_review = parse_date(item.get("next_review"))
    if next_review is None:
        return True
    return next_review <= today()


def due_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted([i for i in items if is_due(i)], key=item_sort_key)


def weak_items(items: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    """Items with lowest mastery scores, regardless of due date."""
    scored = sorted(items, key=lambda i: (i.get("score", 0), i.get("importance", 5)))
    return scored[:limit]


def extract_hint(item: dict[str, Any], vault: Path) -> str:
    """Pick the best hint for active recall."""
    probes = item.get("probes", [])
    if probes:
        return f"思考题：{random.choice(probes)}"

    gaps = item.get("gaps", [])
    if gaps:
        return f"注意这个未解决的疑点：{gaps[0]}"

    prerequisites = item.get("prerequisites", [])
    if prerequisites:
        return f"它依赖于这些前置概念：{', '.join(prerequisites[:3])}。你能先解释它们吗？"

    note_path = item.get("note")
    if note_path:
        full = vault / note_path
        if full.exists():
            text = full.read_text(encoding="utf-8").strip()
            # First non-empty, non-heading paragraph
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    return f"提示：{line[:200]}{'…' if len(line) > 200 else ''}"

    return "尝试用自己的话解释这个概念。"


def quality_from_string(value: str) -> int:
    mapping = {
        "again": 0,
        "a": 0,
        "0": 0,
        "hard": 3,
        "h": 3,
        "3": 3,
        "good": 4,
        "g": 4,
        "4": 4,
        "easy": 5,
        "e": 5,
        "5": 5,
    }
    normalized = value.strip().lower()
    if normalized not in mapping:
        raise ValueError(f"Unknown quality '{value}'. Use again/hard/good/easy or 0/3/4/5.")
    return mapping[normalized]


def sm2_update(interval_days: int, repetitions: int, ease: float, quality: int) -> tuple[int, int, float]:
    """Return (new_interval_days, new_repetitions, new_ease)."""
    if quality < 3:
        return (1, 0, max(1.3, ease - 0.2))

    repetitions += 1
    if repetitions == 1:
        new_interval = 1
    elif repetitions == 2:
        new_interval = 6
    else:
        new_interval = int(interval_days * ease)

    # SM-2 ease factor update
    new_ease = ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ease = max(1.3, new_ease)

    return (new_interval, repetitions, new_ease)


def mastery_for_score(score: int) -> str:
    if score <= 0:
        return "unknown"
    if score <= 2:
        return "seen"
    if score <= 4:
        return "practiced"
    return "confident"


def load_state(user_cfg: dict[str, Any]) -> dict[str, Any]:
    path = learning_state_path(user_cfg)
    state = read_json(path)
    if state is None:
        return {"version": 1, "concepts": {}, "knowledge_tree": {}}
    return state


def save_state(state: dict[str, Any], user_cfg: dict[str, Any]) -> None:
    write_json(learning_state_path(user_cfg), state)


def update_item_in_state(state: dict[str, Any], name: str, quality: int) -> dict[str, Any] | None:
    """Update the item in learning-state.json and return the updated item."""
    target: dict[str, Any] | None = None
    location: str | None = None

    for section in ("concepts", "knowledge_tree"):
        section_data = state.get(section, {})
        if name in section_data:
            target = section_data[name]
            location = section
            break

    if target is None:
        return None

    interval = int(target.get("review_interval_days", 0) or 0)
    repetitions = int(target.get("repetitions", 0) or 0)
    ease = float(target.get("ease", 2.5) or 2.5)

    new_interval, new_repetitions, new_ease = sm2_update(interval, repetitions, ease, quality)
    next_review = (today() + timedelta(days=new_interval)).isoformat()
    new_score = min(5, quality)

    target["score"] = new_score
    target["mastery"] = mastery_for_score(new_score)
    target["last_seen"] = datetime.now(timezone.utc).isoformat()
    target["next_review"] = next_review
    target["review_interval_days"] = new_interval
    target["repetitions"] = new_repetitions
    target["ease"] = round(new_ease, 2)

    # Track review history
    history = target.setdefault("review_history", [])
    history.append({
        "quality": quality,
        "quality_label": _quality_label(quality),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "interval_days": new_interval,
    })
    target["name"] = name

    return target


def _quality_label(quality: int) -> str:
    labels = {0: "again", 3: "hard", 4: "good", 5: "easy"}
    return labels.get(quality, str(quality))


def gather_stats(state: dict[str, Any]) -> dict[str, Any]:
    items = collect_review_items(state)
    due = due_items(items)
    weak = weak_items(items)
    total = len(items)

    mastery_counts: dict[str, int] = {}
    for item in items:
        mastery = item.get("mastery", "unknown")
        mastery_counts[mastery] = mastery_counts.get(mastery, 0) + 1

    return {
        "total": total,
        "due_today": len(due),
        "weak_items": [i["name"] for i in weak],
        "mastery_counts": mastery_counts,
        "next_due": due[0]["name"] if due else None,
        "next_due_date": due[0].get("next_review") if due else None,
    }


def format_due_list(items: list[dict[str, Any]], lang: str) -> str:
    if not items:
        if lang.startswith("zh"):
            return "今天没有到期的复习项。你可以运行 `next` 看看最薄弱的概念，或者先休息。"
        return "Nothing is due today. Run `next` to review weak items anyway, or take a break."

    if lang.startswith("zh"):
        lines = ["## 今日到期复习项", ""]
        for i, item in enumerate(items, 1):
            due = item.get("next_review", "未安排")
            mastery = item.get("mastery", "unknown")
            lines.append(f"{i}. **{item['name']}**（{item.get('type', 'concept')}，掌握度：{mastery}，到期：{due}）")
        lines.append("")
        lines.append(f"共 {len(items)} 项。运行 `recap.py next` 开始复习。")
        return "\n".join(lines)

    lines = ["## Due today", ""]
    for i, item in enumerate(items, 1):
        due = item.get("next_review", "unscheduled")
        mastery = item.get("mastery", "unknown")
        lines.append(f"{i}. **{item['name']}** ({item.get('type', 'concept')}, mastery: {mastery}, due: {due})")
    lines.append("")
    lines.append(f"{len(items)} item(s) due. Run `recap.py next` to start.")
    return "\n".join(lines)


def format_next(item: dict[str, Any], vault: Path, lang: str) -> str:
    hint = extract_hint(item, vault)

    if lang.startswith("zh"):
        lines = [
            "## 复习题",
            "",
            f"**{item['name']}**（{item.get('type', 'concept')}）",
            "",
            f"{hint}",
            "",
            "先不要看笔记，试着自己解释这个概念。",
            "",
            "说完后，告诉我你记得多少，我会帮你标记掌握度。",
            "",
            "你可以说：",
            "- “我忘了” → 标为 again",
            "- “想起来了但有点费劲” → 标为 hard",
            "- “顺利想起来了” → 标为 good",
            "- “太简单了” → 标为 easy",
        ]
        return "\n".join(lines)

    lines = [
        "## Review prompt",
        "",
        f"**{item['name']}** ({item.get('type', 'concept')})",
        "",
        f"{hint}",
        "",
        "Try to explain this in your own words before looking at the note.",
        "",
        "Then tell me how well you remembered, and I'll update the schedule.",
        "",
        "You can say:",
        "- “I forgot” → rate again",
        "- “I recalled but it was hard” → rate hard",
        "- “I recalled it” → rate good",
        "- “Too easy” → rate easy",
    ]
    return "\n".join(lines)


def format_rate_result(item: dict[str, Any], quality: int, lang: str) -> str:
    label = _quality_label(quality)
    next_review = item.get("next_review", "未安排")
    interval = item.get("review_interval_days", 1)

    if lang.startswith("zh"):
        return (
            f"已标记 **{item['name']}** 为 `{label}`。"
            f"下次复习：{next_review}（间隔 {interval} 天）。"
        )
    return (
        f"Marked **{item['name']}** as `{label}`. "
        f"Next review: {next_review} (interval {interval} days)."
    )


def format_stats(stats: dict[str, Any], lang: str) -> str:
    if lang.startswith("zh"):
        lines = ["## 复习统计", ""]
        lines.append(f"- 总概念数：**{stats['total']}**")
        lines.append(f"- 今日到期：**{stats['due_today']}**")
        lines.append(f"- 掌握度分布：{stats['mastery_counts']}")
        if stats["next_due"]:
            lines.append(f"- 下一项：`{stats['next_due']}`（到期：{stats['next_due_date']}）")
        if stats["weak_items"]:
            lines.append("- 薄弱项：" + ", ".join(f"`{n}`" for n in stats["weak_items"][:5]))
        lines.append("")
        lines.append("运行 `recap.py next` 开始复习。")
        return "\n".join(lines)

    lines = ["## Review statistics", ""]
    lines.append(f"- Total items: **{stats['total']}**")
    lines.append(f"- Due today: **{stats['due_today']}**")
    lines.append(f"- Mastery distribution: {stats['mastery_counts']}")
    if stats["next_due"]:
        lines.append(f"- Next due: `{stats['next_due']}` (due: {stats['next_due_date']})")
    if stats["weak_items"]:
        lines.append("- Weak items: " + ", ".join(f"`{n}`" for n in stats["weak_items"][:5]))
    lines.append("")
    lines.append("Run `recap.py next` to start reviewing.")
    return "\n".join(lines)


def detect_language(config: dict[str, Any]) -> str:
    lang = config.get("language", "auto")
    if lang == "auto":
        return "zh"
    return lang


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_due(args: argparse.Namespace) -> int:
    top_config = load_config()
    user_cfg = resolve_user_config(top_config, args.user)
    state = load_state(user_cfg)
    items = collect_review_items(state)
    due = due_items(items)
    lang = detect_language(user_cfg)

    if args.json:
        print(json.dumps([{"name": i["name"], "type": i.get("type"), "mastery": i.get("mastery"), "next_review": i.get("next_review")} for i in due], ensure_ascii=False, indent=2))
        return 0

    print(format_due_list(due, lang))
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    top_config = load_config()
    user_cfg = resolve_user_config(top_config, args.user)
    state = load_state(user_cfg)
    items = collect_review_items(state)
    due = due_items(items)
    lang = detect_language(user_cfg)

    if not due:
        # Suggest a weak item even if not strictly due
        weak = weak_items(items)
        if weak:
            item = weak[0]
            print("今天没有严格到期的复习项，但有一个薄弱项值得回顾：\n")
        else:
            print("暂无复习项。先学点东西， Teach Me 会帮你记录下来。" if lang.startswith("zh") else "No items to review yet. Learn something new and Teach Me will track it.")
            return 0
    else:
        item = due[0]

    if args.json:
        print(json.dumps({
            "name": item["name"],
            "type": item.get("type"),
            "mastery": item.get("mastery"),
            "hint": extract_hint(item, vault_dir(user_cfg)),
            "note_path": item.get("note"),
        }, ensure_ascii=False, indent=2))
        return 0

    print(format_next(item, vault_dir(user_cfg), lang))
    return 0


def cmd_rate(args: argparse.Namespace) -> int:
    top_config = load_config()
    user_cfg = resolve_user_config(top_config, args.user)
    state = load_state(user_cfg)
    lang = detect_language(user_cfg)

    try:
        quality = quality_from_string(args.quality)
    except ValueError as e:
        print(str(e))
        return 1

    updated = update_item_in_state(state, args.name, quality)
    if updated is None:
        print(f"找不到复习项：{args.name}" if lang.startswith("zh") else f"Item not found: {args.name}")
        return 1

    save_state(state, user_cfg)

    if args.json:
        print(json.dumps(updated, ensure_ascii=False, indent=2))
        return 0

    print(format_rate_result(updated, quality, lang))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    top_config = load_config()
    user_cfg = resolve_user_config(top_config, args.user)
    state = load_state(user_cfg)
    stats = gather_stats(state)
    lang = detect_language(user_cfg)

    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0

    print(format_stats(stats, lang))
    return 0


def cmd_manual(_args: argparse.Namespace) -> int:
    manual_path = Path(__file__).parent.parent / "references" / "OPERATION_MANUAL.md"
    if manual_path.exists():
        print(manual_path.read_text(encoding="utf-8"))
    else:
        print("Operation manual not found.")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="recap.py",
        description="Teach Me Recap — spaced-repetition review.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_json_flag(p: argparse.ArgumentParser) -> None:
        p.add_argument("--json", action="store_true", help="Output structured JSON")

    due_parser = subparsers.add_parser("due", help="List items due today")
    due_parser.add_argument("--user", help="Target user ID (defaults to current_user)")
    add_json_flag(due_parser)
    due_parser.set_defaults(func=cmd_due)

    next_parser = subparsers.add_parser("next", help="Show the next review item")
    next_parser.add_argument("--user", help="Target user ID (defaults to current_user)")
    add_json_flag(next_parser)
    next_parser.set_defaults(func=cmd_next)

    rate_parser = subparsers.add_parser("rate", help="Record a review result")
    rate_parser.add_argument("--user", help="Target user ID (defaults to current_user)")
    rate_parser.add_argument("name", help="Name of the concept/knowledge item")
    rate_parser.add_argument("quality", help="again/hard/good/easy or 0/3/4/5")
    add_json_flag(rate_parser)
    rate_parser.set_defaults(func=cmd_rate)

    stats_parser = subparsers.add_parser("stats", help="Review statistics")
    stats_parser.add_argument("--user", help="Target user ID (defaults to current_user)")
    add_json_flag(stats_parser)
    stats_parser.set_defaults(func=cmd_stats)

    manual_parser = subparsers.add_parser("manual", help="Print operation manual")
    manual_parser.add_argument("--user", help="Target user ID (defaults to current_user)")
    manual_parser.set_defaults(func=cmd_manual)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
