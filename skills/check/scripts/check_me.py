#!/usr/bin/env python3
"""
Teach Me Check — lightweight diagnostic companion.

Reads the local Teach Me configuration and vault, then prints either a
natural-language report or structured JSON.

Usage:
    python3 check_me.py report              # natural language report
    python3 check_me.py report --json       # structured JSON
    python3 check_me.py report --user alice # report for a specific user
    python3 check_me.py profile             # show current user and all users
    python3 check_me.py profile --switch alice
    python3 check_me.py profile --add bob --name Bob --github bob
    python3 check_me.py style               # show current style
    python3 check_me.py style --set speaking_style "friendly coach"
    python3 check_me.py manual              # print operation manual
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
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
    """Load config.json, returning defaults if it does not exist."""
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


def save_config(config: dict[str, Any]) -> None:
    config["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


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


TEACH_ME_HOOK_MARKER = "teach-me/scripts/teach_me_hook.py"


def _json_config_has_hook(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return TEACH_ME_HOOK_MARKER in json.dumps(data, ensure_ascii=False)


def _text_config_has_hook(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return TEACH_ME_HOOK_MARKER in path.read_text(encoding="utf-8")
    except OSError:
        return False


def _openclaw_hook_enabled() -> bool:
    hook_dir = Path.home() / ".openclaw" / "hooks" / "teach-me-learning"
    if not hook_dir.exists():
        return False
    if shutil.which("openclaw") is None:
        return False
    try:
        result = subprocess.run(
            ["openclaw", "hooks", "info", "teach-me-learning"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = (result.stdout + result.stderr).lower()
        return result.returncode == 0 and "disabled" not in output
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def detect_installations() -> dict[str, bool]:
    """Detect which agent hooks are actually registered and enabled."""
    home = Path.home()
    return {
        "claude-code": _json_config_has_hook(home / ".claude" / "settings.json"),
        "codex": _text_config_has_hook(home / ".codex" / "config.toml"),
        "kimi": _text_config_has_hook(home / ".kimi" / "config.toml"),
        "openclaw": _openclaw_hook_enabled(),
    }


def check_git_sync(vault: Path, user_cfg: dict[str, Any]) -> dict[str, Any]:
    git_sync = user_cfg.get("git_sync", {})
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


def gather_report(user_id: str | None = None) -> dict[str, Any]:
    top_config = load_config()
    user_cfg = resolve_user_config(top_config, user_id)
    vault = vault_dir(user_cfg)
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

    meta_dir = vault / ".teach-me"
    learning_state = read_json(meta_dir / "learning-state.json") or {}
    style_profile = read_json(meta_dir / "style-profile.json") or {}
    events_path = meta_dir / "events.jsonl"
    event_counts = summarize_jsonl(events_path, limit=200)
    total_events = count_jsonl(events_path)

    knowledge_tree_path = vault / "07_Learning_Profile" / "Knowledge_Tree.md"
    knowledge_tree_nodes = count_knowledge_tree_nodes(knowledge_tree_path)

    git_status = check_git_sync(vault, user_cfg)

    language = user_cfg.get("language", "auto")
    display_language = language
    if display_language == "auto":
        display_language = "中文（自动）"

    return {
        "installed": any_installed,
        "installations": installations,
        "user": {
            "id": user_cfg.get("_user_id", "default"),
            "name": user_cfg.get("name", "Default User"),
            "github": user_cfg.get("github"),
        },
        "all_users": {
            uid: {
                "name": data.get("name", uid),
                "github": data.get("github"),
                "vault_path": data.get("vault_path"),
            }
            for uid, data in top_config.get("users", {}).items()
        },
        "config": {
            "vault_path": str(vault),
            "language": display_language,
            "raw_language": language,
            "max_notes_per_phase": user_cfg.get("max_notes_per_phase", 3),
            "initialized": user_cfg.get("initialized", False),
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
            "verbosity": style_profile.get("verbosity", "compact"),
            "speaking_style": style_profile.get("speaking_style", "friendly and direct"),
            "teach_me_persona": style_profile.get("teach_me_persona", "a patient tutor"),
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

    user = report["user"]
    lines.append(f"当前用户：**{user['name']}** (`{user['id']}`)")
    if user.get("github"):
        lines.append(f"GitHub: `@{user['github']}`")
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

    style = report["style_profile"]
    lines.append("### 对话风格")
    lines.append(f"- **说话风格**：{style['speaking_style']}")
    lines.append(f"- **教学人格**：{style['teach_me_persona']}")
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
    lines.append("- “把说话风格改成 friendly coach”")
    lines.append("- “切换到用户 alice”")
    if gs["enabled"]:
        lines.append("- “关闭 Git sync” / “关闭自动同步”")
    else:
        lines.append("- “开启 Git sync 到 `github.com/user/repo.git`”")
    lines.append("- “导入我的 Obsidian vault：`/path/to/vault`”")
    lines.append("- “关闭所有 Teach Me 钩子” / “打开所有 Teach Me 钩子”")
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

    user = report["user"]
    lines.append(f"Current user: **{user['name']}** (`{user['id']}`)")
    if user.get("github"):
        lines.append(f"GitHub: `@{user['github']}`")
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

    style = report["style_profile"]
    lines.append("### Conversation style")
    lines.append(f"- **Speaking style**: {style['speaking_style']}")
    lines.append(f"- **Teaching persona**: {style['teach_me_persona']}")
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
    lines.append("- “Set my speaking style to friendly coach”")
    lines.append("- “Switch to user alice”")
    if gs["enabled"]:
        lines.append("- “Disable Git sync” / “Turn off auto-sync”")
    else:
        lines.append("- “Enable Git sync to `github.com/user/repo.git`”")
    lines.append("- “Import my Obsidian vault: `/path/to/vault`”")
    lines.append("- “Disable all Teach Me hooks” / “Enable all Teach Me hooks”")
    lines.append("- “Show my recent learning records”")
    lines.append("- “Help me organize my knowledge graph”")
    lines.append("")

    return "\n".join(lines)


def cmd_report(args: argparse.Namespace) -> int:
    report = gather_report(user_id=args.user)
    lang = report["config"]["raw_language"]

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(format_report(report, lang))
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    top_config = load_config()

    if args.switch:
        if args.switch not in top_config.get("users", {}):
            print(f"User '{args.switch}' does not exist. Use --add to create.", file=sys.stderr)
            return 1
        top_config["current_user"] = args.switch
        save_config(top_config)
        print(f"Switched to user '{args.switch}'.")
        return 0

    if args.add:
        user_id = args.add
        users = top_config.setdefault("users", {})
        if user_id in users:
            print(f"User '{user_id}' already exists.", file=sys.stderr)
            return 1
        user_cfg = default_user_config(user_id)
        if args.name:
            user_cfg["name"] = args.name
        if args.github:
            user_cfg["github"] = args.github
        user_cfg["vault_path"] = str(home_dir() / "users" / user_id / "vault")
        users[user_id] = user_cfg
        save_config(top_config)
        print(f"Added user '{user_id}'. Vault: {user_cfg['vault_path']}")
        if args.switch_after_add:
            top_config["current_user"] = user_id
            save_config(top_config)
            print(f"Switched to user '{user_id}'.")
        return 0

    # Show profile
    user_cfg = resolve_user_config(top_config, args.user)
    users = top_config.get("users", {})
    print(f"Current user: {user_cfg.get('name', user_cfg['_user_id'])} ({user_cfg['_user_id']})")
    if user_cfg.get("github"):
        print(f"  GitHub: @{user_cfg['github']}")
    print(f"  Vault: {user_cfg.get('vault_path')}")
    print("All users:")
    for uid, data in users.items():
        marker = " *" if uid == top_config.get("current_user") else ""
        print(f"  - {uid}: {data.get('name', uid)}{marker}")
    return 0


def cmd_style(args: argparse.Namespace) -> int:
    top_config = load_config()
    user_cfg = resolve_user_config(top_config, args.user)
    vault = vault_dir(user_cfg)
    meta_dir = vault / ".teach-me"
    style_path = meta_dir / "style-profile.json"
    style = read_json(style_path) or {
        "language": user_cfg.get("language", "auto"),
        "speaking_style": "friendly and direct",
        "teach_me_persona": "a patient tutor who explains simply and asks one short question",
    }

    if args.set:
        if len(args.set) != 2:
            print("Usage: style --set <key> <value>", file=sys.stderr)
            return 1
        key, value = args.set
        allowed = {
            "speaking_style",
            "teach_me_persona",
            "analogy_level",
            "socratic_level",
            "code_example_level",
            "first_principles_level",
            "verbosity",
            "probe_format",
            "language",
        }
        if key not in allowed:
            print(f"Unknown style key '{key}'. Allowed: {', '.join(sorted(allowed))}", file=sys.stderr)
            return 1
        style[key] = value
        style["last_feedback_at"] = datetime.now(timezone.utc).isoformat()
        write_json(style_path, style)
        print(f"Updated {key} for user '{user_cfg['_user_id']}'.")
        return 0

    print(f"Style for user '{user_cfg['_user_id']}':")
    for key, value in sorted(style.items()):
        if key == "last_feedback_at":
            continue
        print(f"  {key}: {value}")
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
    report_parser.add_argument("--user", help="Target user ID (defaults to current_user)")
    report_parser.set_defaults(func=cmd_report)

    profile_parser = subparsers.add_parser("profile", help="Show or manage user profiles")
    profile_parser.add_argument("--user", help="Show profile for a specific user")
    profile_parser.add_argument("--switch", help="Switch the active user")
    profile_parser.add_argument("--add", help="Add a new user with this ID")
    profile_parser.add_argument("--name", help="Display name for the new user")
    profile_parser.add_argument("--github", help="GitHub username for the new user")
    profile_parser.add_argument(
        "--switch-after-add",
        action="store_true",
        help="Switch to the newly added user",
    )
    profile_parser.set_defaults(func=cmd_profile)

    style_parser = subparsers.add_parser("style", help="Show or update conversation style")
    style_parser.add_argument("--user", help="Target user ID (defaults to current_user)")
    style_parser.add_argument(
        "--set",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="Update a style key (speaking_style, teach_me_persona, verbosity, etc.)",
    )
    style_parser.set_defaults(func=cmd_style)

    manual_parser = subparsers.add_parser("manual", help="Print operation manual")
    manual_parser.set_defaults(func=cmd_manual)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
