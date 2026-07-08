#!/usr/bin/env python3
"""Idempotently register the Teach Me UserPromptSubmit hook in ~/.kimi/config.toml."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


CONFIG_PATH = Path(os.path.expanduser("~/.kimi/config.toml"))
HOOK_COMMAND = "python3 " + os.path.expanduser(
    "~/.agents/skills/teach-me/scripts/teach_me_hook.py"
)
MARKER = "teach-me/scripts/teach_me_hook.py"
HOOK_ENTRY = '{ event = "UserPromptSubmit", command = "%s" }' % HOOK_COMMAND


def find_hooks_span(text: str) -> tuple[int, int] | None:
    match = re.search(r"^hooks\s*=\s*\[", text, re.MULTILINE)
    if not match:
        return None
    start = match.end() - 1
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "[":
            depth += 1
        elif text[index] == "]":
            depth -= 1
            if depth == 0:
                return match.start(), index + 1
    return None


def install(text: str) -> str:
    if MARKER in text:
        return text
    span = find_hooks_span(text)
    if span is None:
        if text and not text.endswith("\n"):
            text += "\n"
        return text + f"hooks = [\n  {HOOK_ENTRY}\n]\n"
    start, end = span
    inner = text[start + len("hooks = ["):end - 1].strip()
    new_inner = f"{inner},\n  {HOOK_ENTRY}" if inner else f"\n  {HOOK_ENTRY}\n"
    return text[:start] + "hooks = [" + new_inner + "]" + text[end:]


def uninstall(text: str) -> str:
    if MARKER not in text:
        return text
    text = re.sub(r",?\s*\{\s*event\s*=\s*\"UserPromptSubmit\"\s*,\s*command\s*=\s*\"[^\"]*teach-me/scripts/teach_me_hook\.py\"\s*\}", "", text)
    text = re.sub(r"hooks\s*=\s*\[\s*\]\s*", "", text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = CONFIG_PATH.read_text(encoding="utf-8") if CONFIG_PATH.exists() else ""
    text = uninstall(text) if args.uninstall else install(text)
    CONFIG_PATH.write_text(text, encoding="utf-8")
    action = "Removed" if args.uninstall else "Installed"
    print(f"{action} Teach Me hook in {CONFIG_PATH}")
    if not args.uninstall:
        print(f"  UserPromptSubmit -> {HOOK_COMMAND}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
