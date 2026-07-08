#!/usr/bin/env python3
"""Idempotently register Teach Me hooks in ~/.claude/settings.json."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


SETTINGS_PATH = Path(os.path.expanduser("~/.claude/settings.json"))
HOOK_COMMAND = "python3 " + os.path.expanduser(
    "~/.claude/skills/teach-me/scripts/teach_me_hook.py"
)
MARKER = "teach-me/scripts/teach_me_hook.py"
DEFS = [("UserPromptSubmit", None), ("PreToolUse", "Bash")]


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        sys.exit(f"Refusing to touch unparseable {path}: {exc}")


def block_has_marker(block: dict) -> bool:
    return any(MARKER in hook.get("command", "") for hook in block.get("hooks", []))


def install(settings: dict) -> dict:
    hooks = settings.setdefault("hooks", {})
    for event, matcher in DEFS:
        group = hooks.setdefault(event, [])
        if any(block_has_marker(block) for block in group):
            continue
        block = {"hooks": [{"type": "command", "command": HOOK_COMMAND}]}
        if matcher is not None:
            block["matcher"] = matcher
        group.append(block)
    return settings


def uninstall(settings: dict) -> dict:
    hooks = settings.get("hooks", {})
    for event, _matcher in DEFS:
        group = hooks.get(event, [])
        group[:] = [block for block in group if not block_has_marker(block)]
        if not group:
            hooks.pop(event, None)
    if not hooks:
        settings.pop("hooks", None)
    return settings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()

    settings = load_settings(SETTINGS_PATH)
    settings = uninstall(settings) if args.uninstall else install(settings)
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    action = "Removed" if args.uninstall else "Installed"
    print(f"{action} Teach Me hooks in {SETTINGS_PATH}")
    if not args.uninstall:
        print(f"  UserPromptSubmit + PreToolUse(Bash) -> {HOOK_COMMAND}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
