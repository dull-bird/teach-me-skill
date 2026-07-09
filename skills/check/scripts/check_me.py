#!/usr/bin/env python3
"""
Teach Me Check — lightweight diagnostic companion.

Reads the local Teach Me configuration and vault, then prints either a
natural-language report or structured JSON.

Usage:
    python3 check_me.py report           # natural language report
    python3 check_me.py report --json    # structured JSON
    python3 check_me.py manual           # print operation manual
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def home_dir() -> Path:
    """Return the Teach Me home directory."""
    raw = os.environ.get("TEACH_ME_HOME", "~/.teach_me_skill")
    return Path(raw).expanduser().resolve()


def config_path() -> Path:
    return home_dir() / "config.json"


def vault_dir(config: dict[str, Any] | None = None) -> Path:
    if config is None:
        config = load_config()
    raw = config.get("vault_path", "~/.teach_me_skill/vault")
    return Path(raw).expanduser().resolve()


def load_config() -> dict[str, Any]:
    """Load config.json, returning defaults if it does not exist."""
    path = config_path()
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return default_config()


def default_config() -> dict[str, Any]:
    return {
        "version": 1,
        "initialized": False,
        "vault_path": "~/.teach_me_skill/vault",
        "language": "auto",
        "max_notes_per_phase": 3,
        "git_sync": {
            "enabled": False,
            "remote": "",
            "branch": "main",
            "auto_sync": False,
        },
    }


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except OSError:
        return 0


def summarize_jsonl(path: Path, limit: int = 100) -> dict[str, int]:
    """Count recent events by type."""
    if not path.exists():
        return {}
    counts: dict[str, int] = {}
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        for line in lines[-limit:]:
            try:
                event = json.loads(line)
                event_type = event.get("type", "unknown")
                counts[event_type] = counts.get(event_type, 0) + 1
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return counts


def count_markdown_files(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(1 for p in folder.rglob("*.md") if p.is_file())


def count_knowledge_tree_nodes(path: Path) -> int:
    """Roughly count headings in Knowledge_Tree.md as proxy for node count."""
    if not path.exists():
        return 0
    try:
        text = path.read_text(encoding="utf-8")
        return sum(1 for line in text.splitlines() if line.startswith("#"))
    except OSError:
        return 0


def detect_installations() -> dict[str, bool]:
    """Detect which agent hooks appear to be installed."""
    home = Path.home()
    return {
        "claude-code": (home / ".claude" / "settings.json").exists(),
        "codex": (home / ".codex" / "config.toml").exists(),
        "kimi": (home / ".kimi" / "config.toml").exists(),
        "openclaw": (home / ".openclaw" / "hooks" / "teach-me-learning").exists(),
    }


def check_git_sync(vault: Path, config: dict[str, Any]) -> dict[str, Any]:
    git_sync = config.get("git_sync", {})
    enabled = bool(git_sync.get("enabled", False))
    remote = git_sync.get("remote", "")
    branch = git_sync.get("branch", "main")
    auto_sync = bool(git_sync.get("auto_sync", False))

    status = {
        "enabled": enabled,
        "remote": remote,
        "branch": branch,
        "auto_sync": auto_sync,
        "repo_present": (vault / ".git").is_dir(),
        "has_local_changes": False,
    }

    if status["repo_present"]:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(vault),
                capture_output=True,
                text=True,
                timeout=10,
            )
            status["has_local_changes"] = bool(result.stdout.strip())
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

    return status


def gather_report() -> dict[str, Any]:
    config = load_config()
    vault = vault_dir(config)
    teach_me_home = home_dir()

    installations = detect_installations()
    any_installed = any(installations.values())

    vault_folders = {
        "concepts": vault / "02_Concepts",
        "algorithmic_ideas": vault / "03_Algorithmic_Ideas",
        "project_maps": vault / "04_Project_Maps",
        "socratic_questions": vault / "05_Socratic_Questions",
        "reviews": vault / "06_Reviews",
    }
    folder_counts = {k: count_markdown_files(v) for k, v in vault_folders.items()}

    learning_state = read_json(vault / ".teach-me" / "learning-state.json") or {}
    style_profile = read_json(vault / ".teach-me" / "style-profile.json") or {}
    events_path = vault / ".teach-me" / "events.jsonl"
    event_counts = summarize_jsonl(events_path, limit=200)
    total_events = count_jsonl(events_path)

    knowledge_tree_path = vault / "07_Learning_Profile" / "Knowledge_Tree.md"
    knowledge_tree_nodes = count_knowledge_tree_nodes(knowledge_tree_path)

    git_status = check_git_sync(vault, config)

    language = config.get("language", "auto")
    if language == "auto":
        language = "中文（自动）"

    return {
        "installed": any_installed,
        "installations": installations,
        "config": {
            "vault_path": str(vault),
            "language": language,
            "max_notes_per_phase": config.get("max_notes_per_phase", 3),
            "initialized": config.get("initialized", False),
        },
        "vault": {
            "exists": vault.exists(),
            "path": str(vault),
            "folder_counts": folder_counts,
            "knowledge_tree_nodes": knowledge_tree_nodes,
            "total_events": total_events,
            "recent_event_counts": event_counts,
            "concepts": len(learning_state.get("concepts", {})),
            "assessed_nodes": len(learning_state.get("knowledge_tree", {})),
        },
        "git_sync": git_status,
        "style_profile": {
            "exists": bool(style_profile),
            "language": style_profile.get("language", "auto"),
            "verbosity": style_profile.get("verbosity", "medium"),
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def format_report(report: dict[str, Any], lang: str) -> str:
    """Format a natural-language report from the structured report."""
    is_zh = lang.startswith("zh") or "中文" in report["config"]["language"]

    if is_zh:
        return _format_zh(report)
    return _format_en(report)


def _installed_zh(installations: dict[str, bool]) -> str:
    installed = [k for k, v in installations.items() if v]
    names = {
        "claude-code": "Claude Code",
        "codex": "Codex",
        "kimi": "Kimi Code CLI",
        "openclaw": "OpenClaw",
    }
    if not installed:
        return "暂无已注册的 agent hook"
    return "、".join(names.get(k, k) for k in installed)


def _format_zh(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("## Teach Me 状态检查")
    lines.append("")

    if not report["installed"]:
        lines.append("看起来 Teach Me 还没有安装。你可以把下面这段发给 agent 来安装：")
        lines.append("")
        lines.append('```text')
        lines.append("请帮我安装 Teach Me 这个 Agent Skill：")
        lines.append("1. 克隆 https://github.com/dull-bird/teach-me-skill.git")
        lines.append("2. 进入 teach-me-skill，运行 ./install.sh")
        lines.append("3. 按我使用的 agent 运行对应的 install-hook.sh")
        lines.append('```')
        lines.append("")
        return "\n".join(lines)

    lines.append(f"✅ 已检测到 hook：{_installed_zh(report['installations'])}")
    lines.append("")

    cfg = report["config"]
    lines.append("### 配置")
    lines.append(f"- **vault 路径**：`{cfg['vault_path']}`")
    lines.append(f"- **笔记语言**：{cfg['language']}")
    lines.append(f"- **每阶段最多笔记数**：{cfg['max_notes_per_phase']}")
    lines.append(f"- **首次配置完成**：{'是' if cfg['initialized'] else '否'}")
    lines.append("")

    vault = report["vault"]
    if not vault["exists"]:
        lines.append("⚠️ vault 目录还不存在。首次写笔记时会自动创建。")
        lines.append("")
    else:
        lines.append("### Vault 内容")
        fc = vault["folder_counts"]
        lines.append(f"- 概念笔记：`{fc['concepts']}` 篇")
        lines.append(f"- 算法思想：`{fc['algorithmic_ideas']}` 篇")
        lines.append(f"- 项目地图：`{fc['project_maps']}` 篇")
        lines.append(f"- 苏格拉底问题：`{fc['socratic_questions']}` 篇")
        lines.append(f"- 复盘记录：`{fc['reviews']}` 篇")
        lines.append(f"- 知识树节点：`{vault['knowledge_tree_nodes']}` 个")
        lines.append(f"- 概念掌握记录：`{vault['concepts']}` 条")
        lines.append(f"- 已评估节点：`{vault['assessed_nodes']}` 个")
        lines.append(f"- 事件总数：`{vault['total_events']}` 条")
        lines.append("")

        recent = vault["recent_event_counts"]
        if recent:
            parts = [f"{k}: {v}" for k, v in recent.items()]
            lines.append(f"最近活动：{', '.join(parts)}")
            lines.append("")

    gs = report["git_sync"]
    lines.append("### Git sync")
    if not gs["enabled"]:
        lines.append("Git sync 当前**未开启**。")
    else:
        lines.append(f"Git sync 已开启，远程：`{gs['remote'] or '未设置'}`，分支：`{gs['branch']}`")
        lines.append(f"本地仓库：{'已初始化' if gs['repo_present'] else '未初始化'}")
        lines.append(f"自动同步：{'开启' if gs['auto_sync'] else '关闭'}")
        if gs["has_local_changes"]:
            lines.append("vault 里有未提交的改动。")
    lines.append("")

    lines.append("### 你可以这样说")
    lines.append("- “把 Teach Me vault 改到 `~/Documents/Teach-Me`”")
    lines.append("- “把笔记语言改成英文/中文/自动”")
    if gs["enabled"]:
        lines.append("- “关闭 Git sync” / “关闭自动同步”")
    else:
        lines.append("- “开启 Git sync 到 `github.com/user/repo.git`”")
    lines.append("- “给我看看最近的学习记录”")
    lines.append("- “帮我整理一下知识图谱”")
    lines.append("")

    return "\n".join(lines)


def _installed_en(installations: dict[str, bool]) -> str:
    installed = [k for k, v in installations.items() if v]
    names = {
        "claude-code": "Claude Code",
        "codex": "Codex",
        "kimi": "Kimi Code CLI",
        "openclaw": "OpenClaw",
    }
    if not installed:
        return "no agent hooks registered"
    return ", ".join(names.get(k, k) for k in installed)


def _format_en(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("## Teach Me status check")
    lines.append("")

    if not report["installed"]:
        lines.append("Teach Me does not appear to be installed yet. You can ask your agent to run:")
        lines.append("")
        lines.append('```text')
        lines.append("Please install the Teach Me Agent Skill:")
        lines.append("1. Clone https://github.com/dull-bird/teach-me-skill.git")
        lines.append("2. Run ./install.sh inside teach-me-skill")
        lines.append("3. Run the matching install-hook.sh for my agent")
        lines.append('```')
        lines.append("")
        return "\n".join(lines)

    lines.append(f"✅ Hooks detected: {_installed_en(report['installations'])}")
    lines.append("")

    cfg = report["config"]
    lines.append("### Configuration")
    lines.append(f"- **Vault path**: `{cfg['vault_path']}`")
    lines.append(f"- **Note language**: {cfg['language']}")
    lines.append(f"- **Max notes per phase**: {cfg['max_notes_per_phase']}")
    lines.append(f"- **Initialized**: {'yes' if cfg['initialized'] else 'no'}")
    lines.append("")

    vault = report["vault"]
    if not vault["exists"]:
        lines.append("⚠️ The vault directory does not exist yet. It will be created on the first note.")
        lines.append("")
    else:
        lines.append("### Vault contents")
        fc = vault["folder_counts"]
        lines.append(f"- Concepts: `{fc['concepts']}`")
        lines.append(f"- Algorithmic ideas: `{fc['algorithmic_ideas']}`")
        lines.append(f"- Project maps: `{fc['project_maps']}`")
        lines.append(f"- Socratic questions: `{fc['socratic_questions']}`")
        lines.append(f"- Reviews: `{fc['reviews']}`")
        lines.append(f"- Knowledge-tree nodes: `{vault['knowledge_tree_nodes']}`")
        lines.append(f"- Concept mastery records: `{vault['concepts']}`")
        lines.append(f"- Assessed nodes: `{vault['assessed_nodes']}`")
        lines.append(f"- Total events: `{vault['total_events']}`")
        lines.append("")

        recent = vault["recent_event_counts"]
        if recent:
            parts = [f"{k}: {v}" for k, v in recent.items()]
            lines.append(f"Recent activity: {', '.join(parts)}")
            lines.append("")

    gs = report["git_sync"]
    lines.append("### Git sync")
    if not gs["enabled"]:
        lines.append("Git sync is currently **disabled**.")
    else:
        lines.append(f"Git sync is enabled. Remote: `{gs['remote'] or 'not set'}`, branch: `{gs['branch']}`")
        lines.append(f"Local repo: {'initialized' if gs['repo_present'] else 'not initialized'}")
        lines.append(f"Auto-sync: {'on' if gs['auto_sync'] else 'off'}")
        if gs["has_local_changes"]:
            lines.append("The vault has uncommitted changes.")
    lines.append("")

    lines.append("### You can say")
    lines.append("- “Move my Teach Me vault to `~/Documents/Teach-Me`”")
    lines.append("- “Change my note language to English/Chinese/auto”")
    if gs["enabled"]:
        lines.append("- “Disable Git sync” / “Turn off auto-sync”")
    else:
        lines.append("- “Enable Git sync to `github.com/user/repo.git`”")
    lines.append("- “Show my recent learning records”")
    lines.append("- “Help me organize my knowledge graph”")
    lines.append("")

    return "\n".join(lines)


def cmd_report(args: argparse.Namespace) -> int:
    report = gather_report()
    lang = report["config"]["language"]

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(format_report(report, lang))
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
        prog="check_me.py",
        description="Teach Me Check — inspect installation, config, and vault.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser("report", help="Print diagnostic report")
    report_parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON instead of natural language",
    )
    report_parser.set_defaults(func=cmd_report)

    manual_parser = subparsers.add_parser("manual", help="Print operation manual")
    manual_parser.set_defaults(func=cmd_manual)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
