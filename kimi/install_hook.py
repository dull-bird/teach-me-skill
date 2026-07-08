#!/usr/bin/env python3
"""Idempotently register Teach Me hooks in ~/.kimi/config.toml.

Kimi Code CLI documents hooks as repeated [[hooks]] tables, but older configs in
the wild may use a single inline `hooks = [...]` array. This installer preserves
the existing shape to avoid producing invalid TOML with both forms.
"""

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
DEFS = [
    ("UserPromptSubmit", None),
    ("PreToolUse", "*"),
    ("PostToolUse", "*"),
    ("Stop", "*"),
]


def inline_entry(event: str, matcher: str | None) -> str:
    matcher_part = f', matcher = "{matcher}"' if matcher else ""
    return f'{{ event = "{event}"{matcher_part}, command = "{HOOK_COMMAND}" }}'


def table_entry(event: str, matcher: str | None) -> str:
    lines = ["[[hooks]]", f'event = "{event}"']
    if matcher:
        lines.append(f'matcher = "{matcher}"')
    lines.append(f'command = "{HOOK_COMMAND}"')
    return "\n".join(lines)


def find_inline_hooks_span(text: str) -> tuple[int, int] | None:
    match = re.search(r"^hooks\s*=\s*\[", text, re.MULTILINE)
    if not match:
        return None
    start = match.end() - 1
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return match.start(), index + 1
    return None


def remove_marker_inline_entries(inner: str) -> str:
    entries = [part.strip() for part in re.split(r",\s*(?=\{)", inner.strip()) if part.strip()]
    kept = [entry for entry in entries if MARKER not in entry]
    return ",\n  ".join(kept)


def remove_marker_tables(text: str) -> str:
    pattern = re.compile(r"\n*\[\[hooks]]\n(?:(?!\n\[\[|\n\[[^\[]).*\n?)*", re.MULTILINE)
    output = text
    for match in reversed(list(pattern.finditer(text))):
        block = match.group(0)
        if MARKER in block:
            output = output[: match.start()] + output[match.end() :]
    return output


def uninstall(text: str) -> str:
    span = find_inline_hooks_span(text)
    if span:
        start, end = span
        prefix = "hooks = ["
        inner = text[start + len(prefix) : end - 1]
        cleaned = remove_marker_inline_entries(inner)
        replacement = "hooks = [\n  " + cleaned + "\n]" if cleaned else "hooks = []"
        text = text[:start] + replacement + text[end:]
    return remove_marker_tables(text)


def install(text: str) -> str:
    text = uninstall(text)
    span = find_inline_hooks_span(text)
    if span:
        start, end = span
        prefix = "hooks = ["
        inner = text[start + len(prefix) : end - 1]
        cleaned = remove_marker_inline_entries(inner)
        entries = [entry for entry in [cleaned, *[inline_entry(*item) for item in DEFS]] if entry]
        replacement = "hooks = [\n  " + ",\n  ".join(entries) + "\n]"
        return text[:start] + replacement + text[end:]

    if text and not text.endswith("\n"):
        text += "\n"
    text += "\n".join(table_entry(event, matcher) for event, matcher in DEFS) + "\n"
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
    print(f"{action} Teach Me hooks in {CONFIG_PATH}")
    if not args.uninstall:
        print(f"  UserPromptSubmit + PreToolUse(*) + PostToolUse(*) + Stop(*) -> {HOOK_COMMAND}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
