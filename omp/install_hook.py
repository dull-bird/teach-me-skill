#!/usr/bin/env python3
"""Idempotently register Teach Me hooks in Pi/OMP settings.json.

This targets the configuration file read by the @hsingjui/pi-hooks extension:
- Global: ~/.pi/agent/settings.json
- Project: .pi/settings.json

If the extension is not installed, run:
    omp install npm:@hsingjui/pi-hooks
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


# Path used by pi-hooks to load command hooks.
GLOBAL_SETTINGS_PATH = Path(os.path.expanduser("~/.pi/agent/settings.json"))
PROJECT_SETTINGS_PATH = Path(".pi/settings.json")

# Default skill location when installed by install.sh into the OMP home.
DEFAULT_SKILL_ROOT = Path(os.path.expanduser("~/.omp/skills"))
HOOK_SCRIPT_REL = "teach-me/scripts/teach_me_hook.py"
MARKER = "teach-me/scripts/teach_me_hook.py"
DEFS = [
    ("PreToolUse", "*"),
    ("PostToolUse", "*"),
    ("PostToolUseFailure", "*"),
    ("Stop", None),
]


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"Refusing to touch unparseable {path}: {exc}")


def block_has_marker(block: dict) -> bool:
    return any(MARKER in hook.get("command", "") for hook in block.get("hooks", []))


def remove_existing(settings: dict) -> dict:
    hooks = settings.get("hooks", {})
    for event in list(hooks):
        group = hooks.get(event, [])
        if isinstance(group, list):
            group[:] = [block for block in group if not block_has_marker(block)]
            if not group:
                hooks.pop(event, None)
    if not hooks:
        settings.pop("hooks", None)
    return settings


def hook_command(skill_root: Path) -> str:
    return f"python3 {skill_root / HOOK_SCRIPT_REL}"


def install(settings: dict, skill_root: Path) -> dict:
    settings = remove_existing(settings)
    hooks = settings.setdefault("hooks", {})
    command = hook_command(skill_root)
    for event, matcher in DEFS:
        block = {"hooks": [{"type": "command", "command": command}]}
        if matcher is not None:
            block["matcher"] = matcher
        hooks.setdefault(event, []).append(block)
    return settings


def uninstall(settings: dict) -> dict:
    return remove_existing(settings)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument(
        "--skill-root",
        type=Path,
        default=DEFAULT_SKILL_ROOT,
        help="Directory containing the installed teach-me skill",
    )
    parser.add_argument(
        "--project",
        action="store_true",
        help="Write to .pi/settings.json instead of ~/.pi/agent/settings.json",
    )
    args = parser.parse_args()

    target = PROJECT_SETTINGS_PATH if args.project else GLOBAL_SETTINGS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    settings = load_settings(target)
    settings = uninstall(settings) if args.uninstall else install(settings, args.skill_root)
    target.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    action = "Removed" if args.uninstall else "Installed"
    print(f"{action} Teach Me hooks in {target}")
    if not args.uninstall:
        print(f"  PreToolUse(*) + PostToolUse(*) + PostToolUseFailure(*) + Stop(*) -> {hook_command(args.skill_root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
