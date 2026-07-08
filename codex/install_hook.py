#!/usr/bin/env python3
"""Idempotently register Teach Me hooks in ~/.codex/config.toml."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


CONFIG_PATH = Path(os.path.expanduser("~/.codex/config.toml"))
HOOK_COMMAND = "python3 " + os.path.expanduser(
    "~/.codex/skills/teach-me/scripts/teach_me_hook.py"
)
MARKER = "teach-me/scripts/teach_me_hook.py"
HOOK_BLOCK = f"""
[[hooks.UserPromptSubmit]]
[[hooks.UserPromptSubmit.hooks]]
type = "command"
command = "{HOOK_COMMAND}"

[[hooks.PreToolUse]]
matcher = "Bash"
[[hooks.PreToolUse.hooks]]
type = "command"
command = "{HOOK_COMMAND}"
"""


def feature_section_span(text: str) -> tuple[int, int] | None:
    match = re.search(r"^\[features\]\s*$", text, re.MULTILINE)
    if not match:
        return None
    next_section = re.search(r"^\[[^\]]+\]\s*$", text[match.end():], re.MULTILINE)
    end = match.end() + next_section.start() if next_section else len(text)
    return match.start(), end


def ensure_hooks_feature(text: str) -> str:
    span = feature_section_span(text)
    if span is None:
        prefix = "" if text.endswith("\n") or not text else "\n"
        return text + prefix + "[features]\nhooks = true\n"

    start, end = span
    section = text[start:end]
    if re.search(r"^\s*hooks\s*=", section, re.MULTILINE):
        section = re.sub(r"^(\s*hooks\s*=\s*).*$", r"\1true", section, flags=re.MULTILINE)
    else:
        section = section.rstrip() + "\nhooks = true\n"
    return text[:start] + section + text[end:]


def install(text: str) -> str:
    text = ensure_hooks_feature(text)
    if MARKER in text:
        return text
    if not text.endswith("\n"):
        text += "\n"
    return text + HOOK_BLOCK


def uninstall(text: str) -> str:
    if MARKER not in text:
        return text
    # Remove only exact blocks produced by this installer.
    pattern = re.escape(HOOK_BLOCK.strip()).replace(re.escape(HOOK_COMMAND), r".*teach-me/scripts/teach_me_hook\.py")
    return re.sub(r"\n*" + pattern + r"\n*", "\n", text, flags=re.DOTALL)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = CONFIG_PATH.read_text(encoding="utf-8") if CONFIG_PATH.exists() else ""
    text = uninstall(text) if args.uninstall else install(text)
    CONFIG_PATH.write_text(text, encoding="utf-8")

    action = "Removed" if args.uninstall else "Installed"
    print(f"{action} Teach Me hooks in {CONFIG_PATH}")
    if not args.uninstall:
        print(f"  UserPromptSubmit + PreToolUse(Bash) -> {HOOK_COMMAND}")
        print("  Codex may ask for hook trust approval on first use.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
