#!/usr/bin/env python3
"""Idempotently register Teach Me hooks in ~/.codex/config.toml."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


CONFIG_PATH = Path(os.path.expanduser("~/.codex/config.toml"))
TEACH_ME_HOME = str(Path(os.path.expanduser("~/.teach_me_skill")))
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
[[hooks.PreToolUse.hooks]]
type = "command"
command = "{HOOK_COMMAND}"

[[hooks.PostToolUse]]
[[hooks.PostToolUse.hooks]]
type = "command"
command = "{HOOK_COMMAND}"

[[hooks.Stop]]
[[hooks.Stop.hooks]]
type = "command"
command = "{HOOK_COMMAND}"
"""


def feature_section_span(text: str) -> tuple[int, int] | None:
    match = re.search(r"^\[features\]\s*$", text, re.MULTILINE)
    if not match:
        return None
    next_section = re.search(r"^\[[^\]]+\]\s*$", text[match.end() :], re.MULTILINE)
    end = match.end() + next_section.start() if next_section else len(text)
    return match.start(), end


def section_span(text: str, section: str) -> tuple[int, int] | None:
    match = re.search(rf"^\[{re.escape(section)}\]\s*$", text, re.MULTILINE)
    if not match:
        return None
    next_section = re.search(r"^\[[^\]]+\]\s*$", text[match.end() :], re.MULTILINE)
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


def toml_string_values(list_body: str) -> list[str]:
    values: list[str] = []
    for match in re.finditer(r'"(?:\\.|[^"\\])*"|\'[^\']*\'', list_body):
        token = match.group(0)
        if token.startswith('"'):
            try:
                values.append(json.loads(token))
            except json.JSONDecodeError:
                continue
        else:
            values.append(token[1:-1])
    return values


def ensure_writable_root(text: str, root: str = TEACH_ME_HOME) -> str:
    """Allow Teach Me to update its local learner vault after one setup step."""
    root = str(Path(root).expanduser())
    root_expr = json.dumps(root)
    span = section_span(text, "sandbox_workspace_write")
    if span is None:
        prefix = "" if text.endswith("\n") or not text else "\n"
        return (
            text
            + prefix
            + "[sandbox_workspace_write]\n"
            + f"writable_roots = [{root_expr}]\n"
        )

    start, end = span
    section = text[start:end]
    match = re.search(
        r"^(\s*writable_roots\s*=\s*)\[(.*?)\]",
        section,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        section = section.rstrip() + f"\nwritable_roots = [{root_expr}]\n"
        return text[:start] + section + text[end:]

    roots = toml_string_values(match.group(2))
    if root in roots:
        return text
    roots.append(root)
    replacement = match.group(1) + "[" + ", ".join(json.dumps(item) for item in roots) + "]"
    section = section[: match.start()] + replacement + section[match.end() :]
    return text[:start] + section + text[end:]


def is_main_hook_table(line: str) -> bool:
    return bool(re.match(r"^\s*\[\[hooks\.[^.]+]]\s*$", line))


def is_top_table(line: str) -> bool:
    return bool(re.match(r"^\s*\[[^\[].*]\s*$", line))


def remove_existing_teach_me_hooks(text: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if is_main_hook_table(line):
            end = index + 1
            while end < len(lines):
                if is_main_hook_table(lines[end]) or is_top_table(lines[end]):
                    break
                end += 1
            block = lines[index:end]
            if any(MARKER in item for item in block):
                index = end
                continue
            output.extend(block)
            index = end
            continue
        output.append(line)
        index += 1
    result = "\n".join(output)
    return result + ("\n" if text.endswith("\n") and result else "")


def install(text: str) -> str:
    text = ensure_hooks_feature(remove_existing_teach_me_hooks(text))
    text = ensure_writable_root(text)
    if not text.endswith("\n"):
        text += "\n"
    return text.rstrip() + "\n" + HOOK_BLOCK


def uninstall(text: str) -> str:
    return remove_existing_teach_me_hooks(text)


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
        print(f"  Added Codex writable root for Teach Me: {TEACH_ME_HOME}")
        print("  Codex may still ask for hook trust approval once after hook changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
