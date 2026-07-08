#!/usr/bin/env python3
"""Hook entrypoint for Teach Me.

The hook is intentionally conservative: it injects compact learning context for
development-like prompts and manual teaching triggers, and logs Bash tool events
when supported. It does not decide learning captures itself.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from teach_me import (  # noqa: E402
    append_jsonl,
    events_path,
    format_context,
    load_config,
    now_iso,
)


MANUAL_TRIGGERS = [
    "teach me",
    "grill me",
    "explain",
    "why",
    "教我",
    "讲讲",
    "解释",
    "原理",
    "复盘",
    "知识点",
    "知识图谱",
    "考我",
    "苏格拉底",
]

DEV_SIGNALS = [
    "code",
    "coding",
    "debug",
    "bug",
    "frontend",
    "backend",
    "refactor",
    "review",
    "test",
    "build",
    "vite",
    "vue",
    "react",
    "svelte",
    "next.js",
    "nuxt",
    "node",
    "typescript",
    "javascript",
    "python",
    "go",
    "rust",
    "api",
    "database",
    "schema",
    "algorithm",
    "architecture",
    "component",
    "hook",
    "代码",
    "开发",
    "项目",
    "前端",
    "后端",
    "调试",
    "报错",
    "实现",
    "修复",
    "重构",
    "评审",
    "测试",
    "构建",
    "算法",
    "架构",
    "组件",
    "页面",
    "接口",
    "数据库",
    "状态",
    "依赖",
]


def load_payload() -> dict[str, Any]:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}


def get_prompt(payload: dict[str, Any]) -> str:
    candidates = [
        payload.get("prompt"),
        payload.get("message"),
        payload.get("content"),
        (payload.get("context") or {}).get("content")
        if isinstance(payload.get("context"), dict)
        else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return ""


def is_manual(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(trigger in lowered or trigger in prompt for trigger in MANUAL_TRIGGERS)


def is_dev_like(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(signal in lowered or signal in prompt for signal in DEV_SIGNALS)


def is_pre_tool(payload: dict[str, Any]) -> bool:
    event = str(
        payload.get("hook_event_name")
        or payload.get("hookEventName")
        or payload.get("event")
        or ""
    )
    tool_name = str(payload.get("tool_name") or payload.get("toolName") or "")
    return event == "PreToolUse" or bool(tool_name)


def maybe_log_tool_event(payload: dict[str, Any]) -> None:
    config = load_config(create=True)
    if not config.get("initialized"):
        return
    tool_name = str(payload.get("tool_name") or payload.get("toolName") or "")
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    command = ""
    if isinstance(tool_input, dict):
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
    elif isinstance(tool_input, str):
        command = tool_input
    if tool_name and tool_name.lower() not in {"bash", "shell"}:
        return
    if command and not re.search(
        r"\b(npm|pnpm|yarn|node|vite|tsc|pytest|go|cargo|python|pip|make|docker|git)\b",
        command,
    ):
        return
    append_jsonl(
        events_path(config),
        {
            "type": "tool",
            "timestamp": now_iso(),
            "tool_name": tool_name or "Bash",
            "command": command[:500],
        },
    )


def build_additional_context(prompt: str, manual: bool) -> str:
    config = load_config(create=True)
    context = format_context(config)
    skill_dir = Path(__file__).resolve().parent.parent
    lines = [
        context,
        f"- installed skill dir: {skill_dir}",
        "- use this skill only for development learning or explicit teaching requests.",
        "- valuable captures include concepts, algorithmic ideas, architecture/data-flow models, and project maps; not just tool names.",
        "- final response should stay concise unless the user explicitly asked for teaching now.",
    ]
    if manual:
        lines.append("- manual teaching trigger detected: teach now and include gentle Socratic questions.")
    return "\n".join(lines)


def main() -> int:
    payload = load_payload()
    if is_pre_tool(payload):
        maybe_log_tool_event(payload)
        return 0

    prompt = get_prompt(payload)
    manual = is_manual(prompt)
    if not manual and not is_dev_like(prompt):
        return 0

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": build_additional_context(prompt, manual),
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
