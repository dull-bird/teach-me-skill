#!/usr/bin/env python3
"""Teach Me runtime.

This script owns deterministic state and file operations for the teach-me skill:
configuration, Obsidian vault initialization, learning captures, style profile
updates, and lightweight event logging.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


TEACH_ME_HOME = Path(
    os.environ.get("TEACH_ME_HOME", str(Path.home() / ".teach_me_skill"))
).expanduser()
CONFIG_PATH = TEACH_ME_HOME / "config.json"
DEFAULT_VAULT = TEACH_ME_HOME / "vault"
USERS_DIR = TEACH_ME_HOME / "users"

MASTERY_ORDER = [
    "unknown",
    "seen",
    "explained",
    "practiced",
    "transferable",
    "confident",
]
MASTERY_SCORE = {name: index for index, name in enumerate(MASTERY_ORDER)}
ITEM_FOLDERS = {
    "concept": "02_Concepts",
    "algorithmic_idea": "03_Algorithmic_Ideas",
    "project_map": "04_Project_Maps",
}
PROFILE_FOLDER = "07_Learning_Profile"


def local_now() -> datetime:
    return datetime.now().astimezone()


def now_iso() -> str:
    return local_now().isoformat(timespec="seconds")


def today() -> str:
    return local_now().date().isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")


def default_git_sync() -> dict[str, Any]:
    return {
        "enabled": False,
        "remote": "",
        "branch": "main",
        "auto_sync": False,
    }


def default_user_config(user_id: str = "default", name: str = "Default User") -> dict[str, Any]:
    vault = DEFAULT_VAULT if user_id == "default" else USERS_DIR / user_id / "vault"
    return {
        "name": name,
        "github": None,
        "vault_path": str(vault),
        "language": "auto",
        "max_notes_per_phase": 3,
        "git_sync": default_git_sync(),
        "initialized": False,
    }


def default_config() -> dict[str, Any]:
    return {
        "version": 2,
        "current_user": "default",
        "users": {"default": default_user_config()},
        "created_at": now_iso(),
        "updated_at": now_iso(),
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
        "created_at": config.get("created_at", now_iso()),
        "updated_at": now_iso(),
    }


def load_config(create: bool = True) -> dict[str, Any]:
    if CONFIG_PATH.exists():
        config = read_json(CONFIG_PATH, default_config())
    else:
        config = default_config()
        if create:
            write_json(CONFIG_PATH, config)

    config = migrate_v1_to_v2(config)
    config.setdefault("current_user", "default")
    users = config.setdefault("users", {"default": default_user_config()})
    if "default" not in users:
        users["default"] = default_user_config()
    return config


def save_config(config: dict[str, Any]) -> None:
    config["updated_at"] = now_iso()
    write_json(CONFIG_PATH, config)


def resolve_user_id(config: dict[str, Any], user_id: str | None = None) -> str:
    if user_id:
        return user_id
    return str(config.get("current_user", "default"))


def resolve_user_config(config: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
    """Return a resolved config dict for the given user."""
    uid = resolve_user_id(config, user_id)
    users = config.get("users", {})
    if uid not in users:
        uid = "default"
    user_cfg = dict(users.get(uid, default_user_config()))
    base = default_user_config(uid, user_cfg.get("name", uid))
    base.update(user_cfg)
    base["_user_id"] = uid
    base["_top_level"] = config
    return base


def switch_current_user(config: dict[str, Any], user_id: str) -> bool:
    """Switch the active user if the user exists. Returns success."""
    if user_id not in config.get("users", {}):
        return False
    config["current_user"] = user_id
    return True


def add_user(config: dict[str, Any], user_id: str, name: str | None = None, github: str | None = None, vault_path_override: str | None = None) -> dict[str, Any]:
    """Add a new user to the config. Returns the user config."""
    users = config.setdefault("users", {})
    if user_id in users:
        return resolve_user_config(config, user_id)
    user_cfg = default_user_config(user_id, name or user_id)
    if github:
        user_cfg["github"] = github
    if vault_path_override:
        user_cfg["vault_path"] = str(Path(vault_path_override).expanduser())
    else:
        user_cfg["vault_path"] = str(USERS_DIR / user_id / "vault")
    users[user_id] = user_cfg
    return resolve_user_config(config, user_id)


def persist_user_config(user_cfg: dict[str, Any]) -> None:
    """Write a resolved user config back into the top-level config."""
    top = user_cfg.get("_top_level")
    if not top:
        return
    user_id = user_cfg.get("_user_id", "default")
    clean = {k: v for k, v in user_cfg.items() if not k.startswith("_")}
    top.setdefault("users", {})[user_id] = clean


def vault_path(config: dict[str, Any]) -> Path:
    return Path(config.get("vault_path") or DEFAULT_VAULT).expanduser()


def meta_dir(config: dict[str, Any]) -> Path:
    return vault_path(config) / ".teach-me"


def default_state() -> dict[str, Any]:
    return {
        "version": 1,
        "concepts": {},
        "knowledge_tree": {},
        "graph_edges": [],
        "captures": [],
        "assessments": [],
    }


def default_style(language: str = "auto") -> dict[str, Any]:
    return {
        "version": 1,
        "language": language,
        "analogy_level": "medium",
        "socratic_level": "gentle",
        "code_example_level": "high",
        "first_principles_level": "high",
        "verbosity": "compact",
        "probe_format": "mostly_choice",
        "probe_required": False,
        "speaking_style": "friendly and direct",
        "teach_me_persona": "a patient tutor who explains simply and asks one short question",
        "last_feedback_at": None,
    }


def state_path(config: dict[str, Any]) -> Path:
    return meta_dir(config) / "learning-state.json"


def style_path(config: dict[str, Any]) -> Path:
    return meta_dir(config) / "style-profile.json"


def events_path(config: dict[str, Any]) -> Path:
    return meta_dir(config) / "events.jsonl"


def git_sync_config(config: dict[str, Any]) -> dict[str, Any]:
    sync = config.setdefault("git_sync", {})
    sync.setdefault("enabled", False)
    sync.setdefault("remote", "")
    sync.setdefault("branch", "main")
    sync.setdefault("auto_sync", False)
    return sync


def run_git(vault: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=str(vault),
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        command = "git " + " ".join(args)
        message = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"{command} failed: {message}")
    return result


def git_has_head(vault: Path) -> bool:
    return run_git(vault, ["rev-parse", "--verify", "HEAD"], check=False).returncode == 0


def git_current_branch(vault: Path) -> str:
    result = run_git(vault, ["branch", "--show-current"], check=False)
    return result.stdout.strip()


def ensure_git_remote(vault: Path, remote: str) -> None:
    if not remote:
        return
    current = run_git(vault, ["remote", "get-url", "origin"], check=False)
    if current.returncode == 0:
        if current.stdout.strip() != remote:
            run_git(vault, ["remote", "set-url", "origin", remote])
    else:
        run_git(vault, ["remote", "add", "origin", remote])


def ensure_git_repo(config: dict[str, Any]) -> None:
    vault = vault_path(config)
    sync = git_sync_config(config)
    branch = str(sync.get("branch") or "main")
    if not (vault / ".git").exists():
        run_git(vault, ["init"])
        if run_git(vault, ["checkout", "-b", branch], check=False).returncode != 0:
            run_git(vault, ["checkout", branch], check=False)
    elif not git_current_branch(vault) and not git_has_head(vault):
        run_git(vault, ["checkout", "-b", branch], check=False)
    ensure_git_remote(vault, str(sync.get("remote") or ""))


def remote_branch_exists(vault: Path, branch: str) -> bool:
    if run_git(vault, ["remote", "get-url", "origin"], check=False).returncode != 0:
        return False
    result = run_git(vault, ["ls-remote", "--exit-code", "--heads", "origin", branch], check=False)
    return result.returncode == 0


def commit_vault_changes(config: dict[str, Any], reason: str) -> tuple[bool, str]:
    vault = vault_path(config)
    run_git(vault, ["add", "-A"])
    if run_git(vault, ["diff", "--cached", "--quiet"], check=False).returncode == 0:
        return False, "no changes"
    stamp = local_now().strftime("%Y-%m-%d %H:%M")
    message = f"teach-me: sync vault {stamp}"
    if reason:
        message = f"{message} - {reason[:48]}"
    run_git(
        vault,
        [
            "-c",
            "user.name=Teach Me",
            "-c",
            "user.email=teach-me@local",
            "commit",
            "-m",
            message,
        ],
    )
    return True, message


def sync_vault(config: dict[str, Any], reason: str = "manual") -> dict[str, Any]:
    if not config.get("initialized"):
        return {"enabled": False, "ok": False, "message": "Teach Me is not initialized"}
    ensure_vault(config)
    sync = git_sync_config(config)
    if not sync.get("enabled"):
        return {"enabled": False, "ok": True, "message": "git sync disabled"}

    vault = vault_path(config)
    branch = str(sync.get("branch") or "main")
    remote = str(sync.get("remote") or "")
    try:
        ensure_git_repo(config)
        current_branch = git_current_branch(vault)
        if current_branch and current_branch != branch:
            branch = current_branch
        committed, commit_message = commit_vault_changes(config, reason)
        pulled = False
        pushed = False
        if remote and remote_branch_exists(vault, branch):
            run_git(vault, ["pull", "--rebase", "--autostash", "origin", branch])
            pulled = True
        if remote:
            run_git(vault, ["push", "-u", "origin", branch])
            pushed = True
        return {
            "enabled": True,
            "ok": True,
            "vault": str(vault),
            "branch": branch,
            "remote": remote,
            "committed": committed,
            "pulled": pulled,
            "pushed": pushed,
            "message": commit_message,
        }
    except Exception as exc:
        return {
            "enabled": True,
            "ok": False,
            "vault": str(vault),
            "branch": branch,
            "remote": remote,
            "message": str(exc),
        }


def auto_sync_vault(config: dict[str, Any], reason: str) -> dict[str, Any] | None:
    sync = git_sync_config(config)
    if not sync.get("enabled") or not sync.get("auto_sync"):
        return None
    return sync_vault(config, reason)


def slugify(title: str) -> str:
    title = title.strip()
    title = re.sub(r"[\\/:*?\"<>|#^\[\]]+", "-", title)
    title = re.sub(r"\s+", "-", title)
    title = re.sub(r"-{2,}", "-", title).strip(".- ")
    return title or "untitled"


def mastery_max(current: str, new: str) -> str:
    current_score = MASTERY_SCORE.get(current, 0)
    new_score = MASTERY_SCORE.get(new, 1)
    return MASTERY_ORDER[max(current_score, new_score)]


def review_days_for_mastery(mastery: str, requested: int | None = None) -> int:
    if requested is not None and requested > 0:
        return requested
    return {
        "unknown": 1,
        "seen": 2,
        "explained": 4,
        "practiced": 7,
        "transferable": 14,
        "confident": 30,
    }.get(mastery, 2)


def read_state(config: dict[str, Any]) -> dict[str, Any]:
    state = read_json(state_path(config), default_state())
    state.setdefault("version", 1)
    state.setdefault("concepts", {})
    state.setdefault("knowledge_tree", {})
    state.setdefault("graph_edges", [])
    state.setdefault("captures", [])
    state.setdefault("assessments", [])
    return state


def read_style(config: dict[str, Any]) -> dict[str, Any]:
    style = read_json(style_path(config), default_style(config.get("language", "auto")))
    base = default_style(config.get("language", "auto"))
    base.update(style)
    return base


def ensure_vault(config: dict[str, Any]) -> None:
    vault = vault_path(config)
    dirs = [
        vault / ".obsidian",
        vault / ".teach-me" / "sessions",
        vault / "02_Concepts",
        vault / "03_Algorithmic_Ideas",
        vault / "04_Project_Maps",
        vault / "05_Socratic_Questions",
        vault / "06_Reviews",
        vault / PROFILE_FOLDER,
    ]
    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)

    app_json = vault / ".obsidian" / "app.json"
    if not app_json.exists():
        write_json(
            app_json,
            {
                "alwaysUpdateLinks": True,
                "newFileLocation": "folder",
                "newFileFolderPath": "02_Concepts",
            },
        )

    appearance_json = vault / ".obsidian" / "appearance.json"
    if not appearance_json.exists():
        write_json(appearance_json, {})

    if not state_path(config).exists():
        write_json(state_path(config), default_state())
    if not style_path(config).exists():
        write_json(style_path(config), default_style(config.get("language", "auto")))
    events_path(config).touch(exist_ok=True)

    index = vault / "00_Index.md"
    if not index.exists():
        index.write_text(
            "\n".join(
                [
                    "# Teach Me Index",
                    "",
                    "This Obsidian vault is maintained by the Teach Me skill.",
                    "",
                    "## Maps",
                    "",
                    "- [[01_Knowledge_Graph]]",
                    "",
                    "## Folders",
                    "",
                    "- [[02_Concepts]]",
                    "- [[03_Algorithmic_Ideas]]",
                    "- [[04_Project_Maps]]",
                    "- [[05_Socratic_Questions]]",
                    "- [[06_Reviews]]",
                    f"- [[{PROFILE_FOLDER}/Knowledge_Tree]]",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    graph = vault / "01_Knowledge_Graph.md"
    if not graph.exists():
        graph.write_text(
            "# Knowledge Graph\n\nNo captured relationships yet.\n",
            encoding="utf-8",
        )

    tree = vault / PROFILE_FOLDER / "Knowledge_Tree.md"
    if not tree.exists():
        tree.write_text(
            "# Knowledge Tree\n\nNo assessed concepts yet.\n",
            encoding="utf-8",
        )

    gitignore = vault / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "\n".join(
                [
                    "# Teach Me vault sync defaults",
                    ".obsidian/workspace*",
                    ".obsidian/cache/",
                    ".trash/",
                    ".teach-me/sessions/",
                    ".teach-me/events.jsonl",
                    "",
                ]
            ),
            encoding="utf-8",
        )


def wikilink(title: str) -> str:
    return f"[[{title.strip()}]]"


def normalize_relationships(raw: Any) -> list[dict[str, str]]:
    relationships: list[dict[str, str]] = []
    if not isinstance(raw, list):
        return relationships
    for rel in raw:
        if isinstance(rel, str):
            relationships.append({"target": rel, "relation": "related"})
        elif isinstance(rel, dict):
            target = str(rel.get("target", "")).strip()
            if not target:
                continue
            relation = str(rel.get("relation", "related")).strip() or "related"
            relationships.append({"target": target, "relation": relation})
    return relationships


def listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def note_path_for_item(config: dict[str, Any], item: dict[str, Any]) -> Path:
    item_type = str(item.get("type", "concept"))
    folder = ITEM_FOLDERS.get(item_type, ITEM_FOLDERS["concept"])
    return vault_path(config) / folder / f"{slugify(str(item.get('title', 'untitled')))}.md"


def render_note(item: dict[str, Any], payload: dict[str, Any], existing: bool) -> str:
    title = str(item.get("title", "untitled")).strip() or "untitled"
    item_type = str(item.get("type", "concept"))
    mastery = str(item.get("mastery", "seen"))
    project = payload.get("project") or {}
    project_name = str(project.get("name", "")).strip()
    phase = str(payload.get("phase", "")).strip()
    one_line = str(item.get("one_line", "") or item.get("why_it_matters", "")).strip()
    first_principles = listify(item.get("first_principles"))
    prerequisites = listify(item.get("prerequisites"))
    context = str(item.get("current_project_context", "")).strip()
    relationships = normalize_relationships(item.get("relationships"))
    questions = listify(item.get("socratic_questions"))
    body = str(item.get("body", "")).strip()

    lines: list[str] = []
    if not existing:
        aliases = listify(item.get("aliases"))
        alias_json = json.dumps(aliases, ensure_ascii=False)
        lines.extend(
            [
                "---",
                f"type: teach-me/{item_type}",
                f"mastery: {mastery}",
                f"created: {today()}",
                f"updated: {today()}",
                f"aliases: {alias_json}",
                "---",
                "",
                f"# {title}",
                "",
            ]
        )

    lines.extend(
        [
            f"## Learning Event - {today()}",
            "",
        ]
    )
    if phase:
        lines.extend(["**Phase:** " + phase, ""])
    if project_name:
        lines.extend(["**Project:** " + project_name, ""])
    if one_line:
        lines.extend(["### One-Line Meaning", "", one_line, ""])
    why = str(item.get("why_it_matters", "")).strip()
    if why and why != one_line:
        lines.extend(["### Why It Matters", "", why, ""])
    if first_principles:
        lines.extend(["### First Principles", ""])
        lines.extend(f"- {entry}" for entry in first_principles)
        lines.append("")
    if prerequisites:
        lines.extend(["### Prerequisites", ""])
        lines.extend(f"- {wikilink(entry)}" for entry in prerequisites)
        lines.append("")
    if context:
        lines.extend(["### In This Project", "", context, ""])
    if relationships:
        lines.extend(["### Relationships", ""])
        for rel in relationships:
            lines.append(f"- {wikilink(rel['target'])}: {rel['relation']}")
        lines.append("")
    if questions:
        lines.extend(["### Socratic Questions", ""])
        lines.extend(f"- {question}" for question in questions)
        lines.append("")
    review_prompt = str(item.get("review_prompt", "")).strip()
    if review_prompt:
        lines.extend(["### Review Prompt", "", review_prompt, ""])
    if body:
        lines.extend(["### Notes", "", body, ""])
    return "\n".join(lines).rstrip() + "\n"


def merge_project(existing: list[str], project_name: str) -> list[str]:
    projects = list(existing or [])
    if project_name and project_name not in projects:
        projects.append(project_name)
    return projects


def add_graph_edges(state: dict[str, Any], source: str, relationships: list[dict[str, str]]) -> None:
    existing = {
        (edge.get("source"), edge.get("relation"), edge.get("target"))
        for edge in state.setdefault("graph_edges", [])
    }
    for rel in relationships:
        edge = {"source": source, "relation": rel["relation"], "target": rel["target"]}
        key = (edge["source"], edge["relation"], edge["target"])
        if key not in existing:
            state["graph_edges"].append(edge)
            existing.add(key)


def add_graph_edge(state: dict[str, Any], source: str, relation: str, target: str) -> None:
    source = source.strip()
    target = target.strip()
    relation = relation.strip() or "related"
    if not source or not target:
        return
    add_graph_edges(state, source, [{"relation": relation, "target": target}])


def clamp_float(value: Any, default: float = 0.5) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def normalize_evidence(raw: Any, fallback: dict[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict):
                summary = str(entry.get("summary", "")).strip()
                kind = str(entry.get("type", "observation")).strip() or "observation"
                if summary:
                    evidence.append(
                        {
                            "type": kind,
                            "summary": summary,
                            "timestamp": str(entry.get("timestamp") or now_iso()),
                        }
                    )
            else:
                text = str(entry).strip()
                if text:
                    evidence.append(
                        {
                            "type": "observation",
                            "summary": text,
                            "timestamp": now_iso(),
                        }
                    )
    elif isinstance(raw, str) and raw.strip():
        evidence.append(
            {"type": "observation", "summary": raw.strip(), "timestamp": now_iso()}
        )
    if not evidence and fallback.get("summary"):
        evidence.append(
            {
                "type": str(fallback.get("type", "observation")),
                "summary": str(fallback["summary"]),
                "timestamp": now_iso(),
            }
        )
    return evidence


def update_knowledge_tree_node(
    state: dict[str, Any],
    title: str,
    data: dict[str, Any],
    *,
    project_name: str = "",
    source: str = "capture",
    note: str = "",
) -> None:
    title = title.strip()
    if not title:
        return
    tree = state.setdefault("knowledge_tree", {})
    current = tree.get(title, {})
    mastery = str(data.get("mastery") or data.get("assessed_mastery") or "unknown")
    if mastery not in MASTERY_ORDER:
        mastery = "unknown"
    merged_mastery = mastery_max(str(current.get("mastery", "unknown")), mastery)
    prerequisites = sorted(
        set(listify(current.get("prerequisites")) + listify(data.get("prerequisites")))
    )
    gaps = sorted(set(listify(current.get("gaps")) + listify(data.get("gaps"))))
    probes = sorted(set(listify(current.get("probes")) + listify(data.get("probes"))))
    misconceptions = sorted(
        set(listify(current.get("misconceptions")) + listify(data.get("misconceptions")))
    )
    evidence = list(current.get("evidence", []))
    evidence.extend(
        normalize_evidence(
            data.get("evidence"),
            {
                "type": source,
                "summary": data.get("why_it_matters")
                or data.get("one_line")
                or data.get("summary")
                or "",
            },
        )
    )
    node = {
        **current,
        "type": str(data.get("type") or current.get("type") or "concept"),
        "mastery": merged_mastery,
        "score": MASTERY_SCORE.get(merged_mastery, 0),
        "confidence": clamp_float(data.get("confidence", current.get("confidence", 0.5))),
        "prerequisites": prerequisites,
        "children": sorted(set(listify(current.get("children")))),
        "gaps": gaps,
        "probes": probes,
        "misconceptions": misconceptions,
        "evidence": evidence[-10:],
        "projects": merge_project(current.get("projects", []), project_name),
        "last_assessed": now_iso(),
        "needs_probe": bool(data.get("needs_probe", merged_mastery in {"unknown", "seen"})),
    }
    if note:
        node["note"] = note
    tree[title] = node

    for prereq in prerequisites:
        prereq_current = tree.get(prereq, {})
        prereq_mastery = str(prereq_current.get("mastery", "unknown"))
        if prereq_mastery not in MASTERY_ORDER:
            prereq_mastery = "unknown"
        tree[prereq] = {
            **prereq_current,
            "type": prereq_current.get("type", "concept"),
            "mastery": prereq_mastery,
            "score": MASTERY_SCORE.get(prereq_mastery, 0),
            "confidence": clamp_float(prereq_current.get("confidence", 0.25)),
            "prerequisites": listify(prereq_current.get("prerequisites")),
            "children": sorted(set(listify(prereq_current.get("children")) + [title])),
            "gaps": listify(prereq_current.get("gaps")),
            "probes": listify(prereq_current.get("probes")),
            "misconceptions": listify(prereq_current.get("misconceptions")),
            "evidence": prereq_current.get("evidence", [])[-10:],
            "projects": merge_project(prereq_current.get("projects", []), project_name),
            "last_assessed": prereq_current.get("last_assessed", now_iso()),
            "needs_probe": bool(prereq_current.get("needs_probe", True)),
        }
        add_graph_edge(state, prereq, "prerequisite_for", title)


def rewrite_knowledge_tree(config: dict[str, Any], state: dict[str, Any]) -> None:
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
                -clamp_float(pair[1].get("confidence", 0.0), 0.0),
                pair[0].lower(),
            ),
        )
        for title, node in weak[:20]:
            mastery = node.get("mastery", "unknown")
            confidence = clamp_float(node.get("confidence", 0.0), 0.0)
            needs_probe = "needs probe" if node.get("needs_probe") else "observed"
            lines.append(
                f"- {wikilink(title)} - {mastery}, confidence {confidence:.2f}, {needs_probe}"
            )

        lines.extend(["", "## Nodes", ""])
        for title in sorted(tree):
            node = tree[title]
            lines.extend(
                [
                    f"### {title}",
                    "",
                    f"- Mastery: {node.get('mastery', 'unknown')}",
                    f"- Confidence: {clamp_float(node.get('confidence', 0.0), 0.0):.2f}",
                    f"- Needs probe: {str(bool(node.get('needs_probe'))).lower()}",
                ]
            )
            prereqs = listify(node.get("prerequisites"))
            children = listify(node.get("children"))
            gaps = listify(node.get("gaps"))
            probes = listify(node.get("probes"))
            if prereqs:
                lines.append("- Prerequisites: " + ", ".join(wikilink(item) for item in prereqs))
            if children:
                lines.append("- Children: " + ", ".join(wikilink(item) for item in children))
            if gaps:
                lines.append("- Gaps: " + "; ".join(gaps))
            if probes:
                lines.append("- Probe questions: " + "; ".join(probes))
            evidence = node.get("evidence", [])[-3:]
            if evidence:
                lines.append("- Evidence:")
                for entry in evidence:
                    stamp = str(entry.get("timestamp", ""))[:10]
                    summary = str(entry.get("summary", "")).strip()
                    if summary:
                        lines.append(f"  - {stamp}: {summary}")
            lines.append("")
    (vault_path(config) / PROFILE_FOLDER / "Knowledge_Tree.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def rewrite_index(config: dict[str, Any], state: dict[str, Any]) -> None:
    vault = vault_path(config)
    concepts = state.get("concepts", {})
    captures = state.get("captures", [])[-10:]
    lines = [
        "# Teach Me Index",
        "",
        "This Obsidian vault is maintained by the Teach Me skill.",
        "",
        "## Maps",
        "",
        "- [[01_Knowledge_Graph]]",
        "",
        "## Recent Captures",
        "",
    ]
    if captures:
        for capture in reversed(captures):
            phase = capture.get("phase") or "learning capture"
            stamp = capture.get("timestamp", "")[:10]
            titles = ", ".join(wikilink(title) for title in capture.get("items", []))
            lines.append(f"- {stamp}: {phase} - {titles}")
    else:
        lines.append("- No captures yet.")
    lines.extend(["", "## Concepts", ""])
    if concepts:
        for title in sorted(concepts):
            data = concepts[title]
            mastery = data.get("mastery", "seen")
            lines.append(f"- {wikilink(title)} - {mastery}")
    else:
        lines.append("- No concepts yet.")
    lines.extend(["", "## Learning Profile", "", f"- [[{PROFILE_FOLDER}/Knowledge_Tree]]"])
    lines.append("")
    (vault / "00_Index.md").write_text("\n".join(lines), encoding="utf-8")


def mermaid_id(name: str, seen: dict[str, str]) -> str:
    if name in seen:
        return seen[name]
    base = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not base or base[0].isdigit():
        base = "n_" + base
    candidate = base
    i = 2
    used = set(seen.values())
    while candidate in used:
        candidate = f"{base}_{i}"
        i += 1
    seen[name] = candidate
    return candidate


def rewrite_graph(config: dict[str, Any], state: dict[str, Any]) -> None:
    edges = state.get("graph_edges", [])
    lines = ["# Knowledge Graph", ""]
    if not edges:
        lines.append("No captured relationships yet.")
    else:
        lines.extend(["## Edges", ""])
        for edge in edges:
            source = edge.get("source", "")
            relation = edge.get("relation", "related")
            target = edge.get("target", "")
            lines.append(f"- {wikilink(source)} -- {relation} --> {wikilink(target)}")
        lines.extend(["", "## Mermaid", "", "```mermaid", "graph TD"])
        ids: dict[str, str] = {}
        for edge in edges:
            source = str(edge.get("source", ""))
            target = str(edge.get("target", ""))
            relation = str(edge.get("relation", "related"))
            source_id = mermaid_id(source, ids)
            target_id = mermaid_id(target, ids)
            lines.append(f'  {source_id}["{source}"] -->|"{relation}"| {target_id}["{target}"]')
        lines.extend(["```", ""])
    (vault_path(config) / "01_Knowledge_Graph.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def cmd_switch_user(args: argparse.Namespace) -> int:
    top_config = load_config(create=True)
    user_id = args.user_id
    if switch_current_user(top_config, user_id):
        save_config(top_config)
        user_cfg = resolve_user_config(top_config, user_id)
        print(f"Switched to user '{user_id}'. Vault: {vault_path(user_cfg)}")
        return 0
    print(f"User '{user_id}' not found. Use `configure --add-user {user_id}` to create them.", file=sys.stderr)
    return 1


def cmd_configure(args: argparse.Namespace) -> int:
    top_config = load_config(create=True)

    if args.add_user:
        user_cfg = add_user(top_config, args.add_user, args.name, args.github, args.vault)
        if args.switch or not top_config.get("current_user"):
            switch_current_user(top_config, args.add_user)
    else:
        user_id = args.user
        if user_id and user_id not in top_config.get("users", {}):
            user_cfg = add_user(top_config, user_id, args.name, args.github, args.vault)
        else:
            user_cfg = resolve_user_config(top_config, user_id)

    if args.vault and not args.add_user:
        user_cfg["vault_path"] = str(Path(args.vault).expanduser())
    if args.language:
        user_cfg["language"] = args.language
    sync = git_sync_config(user_cfg)
    if args.git_remote:
        sync["remote"] = args.git_remote
        sync["enabled"] = True
    if args.git_branch:
        sync["branch"] = args.git_branch
    if args.enable_git_sync:
        sync["enabled"] = True
    if args.disable_git_sync:
        sync["enabled"] = False
    if args.auto_sync:
        sync["auto_sync"] = True
        sync["enabled"] = True
    if args.no_auto_sync:
        sync["auto_sync"] = False
    user_cfg["initialized"] = True

    persist_user_config(user_cfg)
    top_config["current_user"] = user_cfg["_user_id"]
    save_config(top_config)

    ensure_vault(user_cfg)
    if sync.get("enabled"):
        ensure_git_repo(user_cfg)

    style = read_style(user_cfg)
    style["language"] = user_cfg.get("language", "auto")
    write_json(style_path(user_cfg), style)
    rewrite_knowledge_tree(user_cfg, read_state(user_cfg))
    sync_result = auto_sync_vault(user_cfg, "configure")

    print(f"Teach Me configured for user '{user_cfg['_user_id']}'. Vault: {vault_path(user_cfg)}")
    if sync.get("enabled"):
        print(
            "Git sync: enabled, "
            f"remote={sync.get('remote') or '(local only)'}, "
            f"branch={sync.get('branch')}, "
            f"auto_sync={str(bool(sync.get('auto_sync'))).lower()}"
        )
    if sync_result is not None:
        print("Initial sync: " + json.dumps(sync_result, ensure_ascii=False))
    return 0


def format_context(config: dict[str, Any], brief: bool = True) -> str:
    initialized = bool(config.get("initialized"))
    lines = [
        "Teach Me learning context:",
        f"- user: {config.get('_user_id', 'default')}",
        f"- initialized: {str(initialized).lower()}",
        f"- default home: {TEACH_ME_HOME}",
        f"- vault: {vault_path(config)}",
        f"- note language: {config.get('language', 'auto')}",
        f"- max notes per phase: {config.get('max_notes_per_phase', 3)}",
    ]
    sync = git_sync_config(config)
    lines.append(
        "- git sync: enabled={enabled}, auto_sync={auto}, remote={remote}, branch={branch}".format(
            enabled=str(bool(sync.get("enabled"))).lower(),
            auto=str(bool(sync.get("auto_sync"))).lower(),
            remote=sync.get("remote") or "(none)",
            branch=sync.get("branch") or "main",
        )
    )
    if not initialized:
        lines.extend(
            [
                "- first-use rule: before writing learning notes, ask the user to confirm the vault path, note language, and whether to enable Git sync.",
                "- default choices: vault ~/.teach_me_skill/vault, language auto based on conversation, Git sync off unless the user provides a remote.",
                "- Git sync question: ask whether the user has a remote repository for cross-device vault sync; if yes, run configure with --git-remote <url> --auto-sync.",
            ]
        )
        return "\n".join(lines)

    ensure_vault(config)
    state = read_state(config)
    style = read_style(config)
    concepts = state.get("concepts", {})
    tree = state.get("knowledge_tree", {})
    total = len(concepts)
    weak_count = sum(1 for data in concepts.values() if data.get("mastery", "seen") in ("unknown", "seen"))
    due_today = sum(
        1
        for data in concepts.values()
        if data.get("next_review") and str(data.get("next_review")) <= today()
    )

    lines.extend(
        [
            "- teaching cadence: do not interrupt implementation; capture 1-3 high-value concepts at phase boundaries.",
            "- teaching baseline: before teaching a new domain, sketch a prerequisite ladder, probe obvious basics, and start at the first weak node.",
            "- capture command: python3 <teach-me-skill-dir>/scripts/teach_me.py capture",
            "- assessment command: python3 <teach-me-skill-dir>/scripts/teach_me.py assess",
            "- sync command: python3 <teach-me-skill-dir>/scripts/teach_me.py sync",
            "- style: analogy={analogy}, socratic={socratic}, code={code}, first_principles={fp}, verbosity={verbosity}".format(
                analogy=style.get("analogy_level", "medium"),
                socratic=style.get("socratic_level", "gentle"),
                code=style.get("code_example_level", "high"),
                fp=style.get("first_principles_level", "high"),
                verbosity=style.get("verbosity", "compact"),
            ),
            f"- speaking style: {style.get('speaking_style', 'friendly and direct')}",
            f"- teach me persona: {style.get('teach_me_persona', 'a patient tutor')}",
            "- feedback probes: format={fmt}, required={required}; ask mostly multiple-choice or true/false checks, occasional short-answer, and continue if the user skips.".format(
                fmt=style.get("probe_format", "mostly_choice"),
                required=str(bool(style.get("probe_required", False))).lower(),
            ),
            f"- portrait summary: {total} concepts, {weak_count} weak, {due_today} due today, {len(tree)} knowledge-tree nodes",
        ]
    )

    if brief:
        lines.append("- run `python3 <teach-me-skill-dir>/scripts/teach_me.py context --full` to see weak concepts, knowledge-tree nodes, and recent captures.")
        return "\n".join(lines)

    weak = sorted(
        concepts.items(),
        key=lambda pair: (
            MASTERY_SCORE.get(pair[1].get("mastery", "seen"), 1),
            pair[1].get("last_seen", ""),
        ),
    )[:8]
    recent = sorted(
        concepts.items(),
        key=lambda pair: pair[1].get("last_seen", ""),
        reverse=True,
    )[:8]
    weak_nodes = sorted(
        tree.items(),
        key=lambda pair: (
            MASTERY_SCORE.get(str(pair[1].get("mastery", "unknown")), 0),
            pair[1].get("last_assessed", ""),
        ),
    )[:8]

    if weak:
        lines.append("- weaker concepts: " + ", ".join(f"{name}({data.get('mastery', 'seen')})" for name, data in weak))
    if weak_nodes:
        lines.append("- knowledge-tree weak nodes: " + ", ".join(f"{name}({data.get('mastery', 'unknown')})" for name, data in weak_nodes))
    if recent:
        lines.append("- recent concepts: " + ", ".join(f"{name}({data.get('mastery', 'seen')})" for name, data in recent))
    return "\n".join(lines)


def cmd_context(args: argparse.Namespace) -> int:
    top_config = load_config(create=True)
    user_cfg = resolve_user_config(top_config, args.user)
    print(format_context(user_cfg, brief=not args.full))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    top_config = load_config(create=True)
    user_cfg = resolve_user_config(top_config, args.user)
    data = {
        "home": str(TEACH_ME_HOME),
        "config": str(CONFIG_PATH),
        "user": user_cfg.get("_user_id"),
        "initialized": bool(user_cfg.get("initialized")),
        "vault": str(vault_path(user_cfg)),
        "language": user_cfg.get("language", "auto"),
        "git_sync": git_sync_config(user_cfg),
    }
    if user_cfg.get("initialized"):
        ensure_vault(user_cfg)
        state = read_state(user_cfg)
        data["concept_count"] = len(state.get("concepts", {}))
        data["knowledge_tree_count"] = len(state.get("knowledge_tree", {}))
        data["capture_count"] = len(state.get("captures", []))
        data["assessment_count"] = len(state.get("assessments", []))
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    top_config = load_config(create=True)
    user_cfg = resolve_user_config(top_config, args.user)
    result = sync_vault(user_cfg, args.reason or "manual")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


def cmd_assess(args: argparse.Namespace) -> int:
    top_config = load_config(create=True)
    user_cfg = resolve_user_config(top_config, args.user)
    if not user_cfg.get("initialized"):
        print(
            "Teach Me is not initialized. Ask the user to confirm the vault path "
            "and language, then run `teach_me.py configure`.",
            file=sys.stderr,
        )
        return 2
    ensure_vault(user_cfg)
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Invalid assessment JSON: {exc}", file=sys.stderr)
        return 1

    nodes = payload.get("nodes", [])
    if not isinstance(nodes, list) or not nodes:
        print("No assessment nodes provided.", file=sys.stderr)
        return 1

    state = read_state(user_cfg)
    project = payload.get("project") or {}
    project_name = str(project.get("name", "")).strip()
    updated: list[str] = []
    for raw_node in nodes:
        if not isinstance(raw_node, dict):
            continue
        title = str(raw_node.get("title", "")).strip()
        if not title:
            continue
        update_knowledge_tree_node(
            state,
            title,
            raw_node,
            project_name=project_name,
            source="assessment",
        )
        updated.append(title)

    if not updated:
        print("No valid assessment nodes provided.", file=sys.stderr)
        return 1

    assessment = {
        "timestamp": now_iso(),
        "project": project,
        "domain": payload.get("domain", ""),
        "summary": payload.get("summary", ""),
        "nodes": updated,
        "questions": listify(payload.get("questions")),
    }
    state.setdefault("assessments", []).append(assessment)
    write_json(state_path(user_cfg), state)
    rewrite_knowledge_tree(user_cfg, state)
    rewrite_index(user_cfg, state)
    rewrite_graph(user_cfg, state)
    append_jsonl(events_path(user_cfg), {"type": "assessment", **assessment})
    sync_result = auto_sync_vault(user_cfg, "assessment")

    output = {
        "assessed": updated,
        "vault": str(vault_path(user_cfg)),
        "knowledge_tree": str(vault_path(user_cfg) / PROFILE_FOLDER / "Knowledge_Tree.md"),
    }
    if sync_result is not None:
        output["sync"] = sync_result
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def cmd_style(args: argparse.Namespace) -> int:
    top_config = load_config(create=True)
    user_cfg = resolve_user_config(top_config, args.user)
    if not user_cfg.get("initialized"):
        ensure_vault(user_cfg)
    style = read_style(user_cfg)
    updates = {
        "analogy_level": args.analogy,
        "socratic_level": args.socratic,
        "code_example_level": args.code,
        "first_principles_level": args.first_principles,
        "verbosity": args.verbosity,
        "language": args.language,
        "probe_format": args.probe_format,
        "speaking_style": args.speaking_style,
        "teach_me_persona": args.teach_me_persona,
    }
    for key, value in updates.items():
        if value:
            style[key] = value
    style["last_feedback_at"] = now_iso()
    write_json(style_path(user_cfg), style)
    sync_result = auto_sync_vault(user_cfg, "style")
    print(f"Teach Me style updated for user '{user_cfg['_user_id']}': {style_path(user_cfg)}")
    if sync_result is not None:
        print("Sync: " + json.dumps(sync_result, ensure_ascii=False))
    return 0


def cmd_log_event(args: argparse.Namespace) -> int:
    top_config = load_config(create=True)
    user_cfg = resolve_user_config(top_config, args.user)
    if not user_cfg.get("initialized"):
        return 0
    ensure_vault(user_cfg)
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}
    payload.setdefault("type", args.type)
    payload.setdefault("timestamp", now_iso())
    append_jsonl(events_path(user_cfg), payload)
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    top_config = load_config(create=True)
    user_cfg = resolve_user_config(top_config, args.user)
    if not user_cfg.get("initialized"):
        print(
            "Teach Me is not initialized. Ask the user to confirm the vault path "
            "and language, then run `teach_me.py configure`.",
            file=sys.stderr,
        )
        return 2
    ensure_vault(user_cfg)

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Invalid capture JSON: {exc}", file=sys.stderr)
        return 1

    items = payload.get("items", [])
    if not isinstance(items, list) or not items:
        print("No capture items provided.", file=sys.stderr)
        return 1

    max_notes = int(user_cfg.get("max_notes_per_phase", 3) or 3)
    allow_many = bool(payload.get("allow_many"))
    selected = items if allow_many else items[:max_notes]

    state = read_state(user_cfg)
    project = payload.get("project") or {}
    project_name = str(project.get("name", "")).strip()
    phase = str(payload.get("phase", "")).strip()
    captured_titles: list[str] = []

    for raw_item in selected:
        if not isinstance(raw_item, dict):
            continue
        title = str(raw_item.get("title", "")).strip()
        if not title:
            continue
        item_type = str(raw_item.get("type", "concept"))
        if item_type not in ITEM_FOLDERS:
            item_type = "concept"
            raw_item["type"] = item_type
        mastery = str(raw_item.get("mastery", "seen"))
        if mastery not in MASTERY_ORDER:
            mastery = "seen"
            raw_item["mastery"] = mastery

        path = note_path_for_item(user_cfg, raw_item)
        existing = path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        rendered = render_note(raw_item, payload, existing=existing)
        if existing:
            with path.open("a", encoding="utf-8") as f:
                f.write("\n" + rendered)
        else:
            path.write_text(rendered, encoding="utf-8")

        concepts = state.setdefault("concepts", {})
        current = concepts.get(title, {})
        requested_review_days = raw_item.get("next_review_days")
        try:
            requested_review_days = int(requested_review_days) if requested_review_days is not None else None
        except (TypeError, ValueError):
            requested_review_days = None
        merged_mastery = mastery_max(str(current.get("mastery", "unknown")), mastery)
        interval = review_days_for_mastery(merged_mastery, requested_review_days)
        next_review = (local_now().date() + timedelta(days=interval)).isoformat()
        concepts[title] = {
            **current,
            "type": item_type,
            "mastery": merged_mastery,
            "score": MASTERY_SCORE.get(merged_mastery, 1),
            "last_seen": now_iso(),
            "next_review": next_review,
            "review_interval_days": interval,
            "ease": float(current.get("ease", 2.5)),
            "projects": merge_project(current.get("projects", []), project_name),
            "note": str(path.relative_to(vault_path(user_cfg))),
            "importance": raw_item.get("importance"),
        }
        relationships = normalize_relationships(raw_item.get("relationships"))
        add_graph_edges(state, title, relationships)
        update_knowledge_tree_node(
            state,
            title,
            raw_item,
            project_name=project_name,
            source="capture",
            note=str(path.relative_to(vault_path(user_cfg))),
        )
        captured_titles.append(title)

    if not captured_titles:
        print("No valid capture items provided.", file=sys.stderr)
        return 1

    capture = {
        "timestamp": now_iso(),
        "project": project,
        "phase": phase,
        "language": payload.get("language", user_cfg.get("language", "auto")),
        "summary": payload.get("summary", ""),
        "items": captured_titles,
    }
    state.setdefault("captures", []).append(capture)
    write_json(state_path(user_cfg), state)
    rewrite_index(user_cfg, state)
    rewrite_graph(user_cfg, state)
    rewrite_knowledge_tree(user_cfg, state)
    append_jsonl(events_path(user_cfg), {"type": "capture", **capture})
    sync_result = auto_sync_vault(user_cfg, "capture")

    output = {
        "captured": captured_titles,
        "vault": str(vault_path(user_cfg)),
        "index": str(vault_path(user_cfg) / "00_Index.md"),
    }
    if sync_result is not None:
        output["sync"] = sync_result
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Teach Me runtime")
    parser.add_argument("--user", help="Target user ID (defaults to current_user)")
    sub = parser.add_subparsers(dest="command", required=True)

    configure = sub.add_parser("configure", help="Initialize or update Teach Me config")
    configure.add_argument("--vault", help="Obsidian vault path")
    configure.add_argument("--language", default="auto", help="auto, zh, en, etc.")
    configure.add_argument("--git-remote", help="Remote repository URL for vault sync")
    configure.add_argument("--git-branch", help="Git branch for vault sync")
    configure.add_argument("--enable-git-sync", action="store_true", help="Initialize and enable local vault git sync")
    configure.add_argument("--disable-git-sync", action="store_true", help="Disable vault git sync")
    configure.add_argument("--auto-sync", action="store_true", help="Automatically sync after capture/assess")
    configure.add_argument("--no-auto-sync", action="store_true", help="Disable automatic sync")
    configure.add_argument("--add-user", help="Add a new user with this ID")
    configure.add_argument("--name", help="Display name for the user")
    configure.add_argument("--github", help="GitHub username for the user")
    configure.add_argument("--switch", action="store_true", help="Switch to the configured user after setup")
    configure.set_defaults(func=cmd_configure)

    switch_user = sub.add_parser("switch-user", help="Switch the active user")
    switch_user.add_argument("user_id", help="User ID to activate")
    switch_user.set_defaults(func=cmd_switch_user)

    context = sub.add_parser("context", help="Print compact context for an agent")
    context.add_argument("--full", action="store_true", help="Include weak concepts, knowledge-tree nodes, and recent captures")
    context.add_argument("--brief", action="store_true", help="Print only summary (default)")
    context.set_defaults(func=cmd_context)

    status = sub.add_parser("status", help="Print runtime status JSON")
    status.set_defaults(func=cmd_status)

    sync = sub.add_parser("sync", help="Commit, pull --rebase, and push the vault if Git sync is enabled")
    sync.add_argument("--reason", default="manual", help="Short reason for the sync commit")
    sync.set_defaults(func=cmd_sync)

    assess = sub.add_parser("assess", help="Update the user's knowledge tree from JSON stdin")
    assess.set_defaults(func=cmd_assess)

    style = sub.add_parser("style", help="Update teaching style preferences")
    style.add_argument("--analogy", choices=["low", "medium", "high"])
    style.add_argument("--socratic", choices=["off", "gentle", "active"])
    style.add_argument("--code", choices=["low", "medium", "high"])
    style.add_argument("--first-principles", choices=["low", "medium", "high"])
    style.add_argument("--verbosity", choices=["brief", "compact", "detailed"])
    style.add_argument("--probe-format", choices=["mostly_choice", "mixed", "mostly_short"])
    style.add_argument("--language")
    style.add_argument("--speaking-style", help="Free-text speaking style, e.g. 'friendly coach'")
    style.add_argument("--teach-me-persona", help="Persona description, e.g. 'a patient tutor'")
    style.set_defaults(func=cmd_style)

    log_event = sub.add_parser("log-event", help="Append a JSON event from stdin")
    log_event.add_argument("--type", default="event")
    log_event.set_defaults(func=cmd_log_event)

    capture = sub.add_parser("capture", help="Capture learning notes from JSON stdin")
    capture.set_defaults(func=cmd_capture)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
