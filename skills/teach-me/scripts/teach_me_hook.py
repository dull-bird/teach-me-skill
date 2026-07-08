#!/usr/bin/env python3
"""Hook entrypoint for Teach Me.

The hook is intentionally conservative. Prompt hooks inject compact learning
context for obvious learning work. Tool hooks collect evidence. Stop hooks use
that evidence to request exactly one short Teach Me review when a turn appears
learning-worthy.
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

TOOL_EVENTS = {"PreToolUse", "PostToolUse", "PostToolUseFailure"}
STOP_EVENTS = {"Stop"}

TEST_RE = re.compile(
    r"\b(pytest|unittest|npm\s+test|pnpm\s+test|yarn\s+test|go\s+test|cargo\s+test|vitest|jest|playwright)\b",
    re.IGNORECASE,
)
BUILD_RE = re.compile(
    r"\b(npm\s+run\s+build|pnpm\s+build|yarn\s+build|vite\s+build|mdbook\s+build|make|cargo\s+build|go\s+build)\b",
    re.IGNORECASE,
)
TYPECHECK_RE = re.compile(
    r"\b(tsc|mypy|ruff|eslint|biome|prettier|black|cargo\s+clippy|cargo\s+fmt)\b",
    re.IGNORECASE,
)
GIT_RE = re.compile(r"\bgit\s+(diff|status|show|log|grep|blame)\b", re.IGNORECASE)
RESEARCH_RE = re.compile(
    r"\b(rg|grep|sed|find|opencli|curl|context7|scholar|semantic-scholar)\b",
    re.IGNORECASE,
)
ERROR_RE = re.compile(
    r"\b(traceback|exception|error|failed|failure|timeout|panic|segmentation fault|报错|失败)\b",
    re.IGNORECASE,
)
PASS_RE = re.compile(r"\b(passed|passing|success|successful|complete|通过|完成)\b", re.IGNORECASE)
FINISH_RE = re.compile(
    r"(done|fixed|implemented|verified|completed|tests?\s+pass|build\s+passed|已完成|已修复|已实现|测试通过|构建通过|验证通过|完成|修复|实现|通过)",
    re.IGNORECASE,
)


def load_payload() -> dict[str, Any]:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def event_name(payload: dict[str, Any]) -> str:
    event = (
        payload.get("hook_event_name")
        or payload.get("hookEventName")
        or payload.get("event")
        or ""
    )
    return str(event)


def get_prompt(payload: dict[str, Any]) -> str:
    for key in ("prompt", "user_prompt", "userPrompt", "message"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    messages = payload.get("messages")
    if isinstance(messages, list) and messages:
        last = messages[-1]
        if isinstance(last, dict):
            content = last.get("content")
            if isinstance(content, str):
                return content
    return ""


def includes_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def is_manual(prompt: str) -> bool:
    return includes_any(prompt, MANUAL_TRIGGERS)


def is_dev_like(prompt: str) -> bool:
    return includes_any(prompt, DEV_SIGNALS)


def session_id(payload: dict[str, Any]) -> str:
    return str(payload.get("session_id") or payload.get("sessionId") or "")


def turn_id(payload: dict[str, Any]) -> str:
    return str(
        payload.get("turn_id")
        or payload.get("turnId")
        or payload.get("prompt_id")
        or payload.get("promptId")
        or ""
    )


def cwd(payload: dict[str, Any]) -> str:
    return str(payload.get("cwd") or payload.get("working_directory") or "")


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def tool_name(payload: dict[str, Any]) -> str:
    value = (
        payload.get("tool_name")
        or payload.get("toolName")
        or payload.get("tool")
        or payload.get("name")
        or ""
    )
    if isinstance(value, dict):
        value = value.get("name", "")
    return str(value)


def tool_input(payload: dict[str, Any]) -> Any:
    for key in ("tool_input", "toolInput", "input", "arguments", "args"):
        if key in payload:
            return payload[key]
    return {}


def tool_response(payload: dict[str, Any]) -> Any:
    for key in ("tool_response", "toolResponse", "response", "result", "output"):
        if key in payload:
            return payload[key]
    return {}


def compact_json(value: Any, limit: int = 700) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except TypeError:
            text = str(value)
    return text.replace("\n", "\\n")[:limit]


def extract_command(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    for key in ("command", "cmd", "script"):
        item = value.get(key)
        if isinstance(item, str):
            return item
    return ""


def extract_file_path(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    for key in ("file_path", "filePath", "path", "filename", "target_file"):
        item = value.get(key)
        if isinstance(item, str):
            return item
    return ""


def classify_tool(tool: str, command: str, file_path: str, output: str) -> tuple[int, list[str]]:
    tags: set[str] = set()
    score = 0
    lowered_tool = tool.lower()
    combined = f"{command}\n{file_path}\n{output}"

    if lowered_tool in {"edit", "write", "multiedit", "apply_patch", "applypatch"}:
        tags.add("file_edit")
        score += 4

    if TEST_RE.search(command) or re.search(r"\b\d+\s+passed\b", output, re.IGNORECASE):
        tags.add("test")
        score += 4

    if BUILD_RE.search(command):
        tags.add("build")
        score += 3

    if TYPECHECK_RE.search(command):
        tags.add("quality_check")
        score += 3

    if GIT_RE.search(command):
        tags.add("repo_inspection")
        score += 2

    if RESEARCH_RE.search(command) or lowered_tool in {"web", "web.run", "search", "read", "open"}:
        tags.add("investigation")
        score += 1

    if ERROR_RE.search(combined):
        tags.add("debug_signal")
        score += 3

    if PASS_RE.search(output) and tags:
        tags.add("verified")
        score += 1

    if not tags and lowered_tool not in {"bash", "shell", ""}:
        tags.add("tool_use")
        score += 1

    return score, sorted(tags)


def event_context(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "session_id": session_id(payload),
        "turn_id": turn_id(payload),
        "cwd": cwd(payload),
    }


def append_event(config: dict[str, Any], data: dict[str, Any]) -> None:
    append_jsonl(events_path(config), {"timestamp": now_iso(), **data})


def maybe_log_prompt_event(payload: dict[str, Any], prompt: str, manual: bool, dev_like: bool) -> None:
    config = load_config(create=True)
    append_event(
        config,
        {
            "type": "prompt",
            **event_context(payload),
            "manual": manual,
            "dev_like": dev_like,
            "prompt": prompt[:500],
            "score": 4 if manual else (2 if dev_like else 0),
            "signal_tags": ["manual"] if manual else (["dev_like"] if dev_like else []),
        },
    )


def maybe_log_tool_event(payload: dict[str, Any]) -> None:
    config = load_config(create=True)
    event = event_name(payload)
    input_value = tool_input(payload)
    response_value = tool_response(payload)
    tool = tool_name(payload)
    command = extract_command(input_value)
    file_path = extract_file_path(input_value)
    response_text = compact_json(response_value)
    score, tags = classify_tool(tool, command, file_path, response_text)
    phase = {
        "PreToolUse": "pre",
        "PostToolUse": "post",
        "PostToolUseFailure": "failure",
    }.get(event, "tool")
    append_event(
        config,
        {
            "type": "tool",
            "phase": phase,
            **event_context(payload),
            "tool_name": tool,
            "command": command[:500],
            "file_path": file_path[:500],
            "input_excerpt": compact_json(input_value),
            "output_excerpt": response_text,
            "score": score,
            "signal_tags": tags,
        },
    )


def load_events(config: dict[str, Any], limit: int = 500) -> list[dict[str, Any]]:
    path = events_path(config)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    events: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    return events


def same_scope(event: dict[str, Any], payload: dict[str, Any]) -> bool:
    current_turn = turn_id(payload)
    current_session = session_id(payload)
    current_cwd = cwd(payload)
    if current_turn:
        return event.get("turn_id") == current_turn
    if current_session:
        return event.get("session_id") == current_session
    if current_cwd:
        return event.get("cwd") == current_cwd
    return not (current_turn or current_session or current_cwd)


def already_blocked(events: list[dict[str, Any]], payload: dict[str, Any]) -> bool:
    return any(
        event.get("type") == "stop_decision"
        and event.get("decision") == "block"
        and same_scope(event, payload)
        for event in events
    )


def score_stop(payload: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    scoped = [event for event in events if same_scope(event, payload)]
    tags: set[str] = set()
    reasons: list[str] = []
    score = 0

    for event in scoped:
        event_score = int(event.get("score") or 0)
        score += event_score
        for tag in event.get("signal_tags", []) or []:
            tags.add(str(tag))
        if event.get("type") == "tool" and event_score:
            tool = str(event.get("tool_name") or "tool")
            command = str(event.get("command") or event.get("file_path") or "").strip()
            if command:
                reasons.append(f"{tool}: {command[:120]}")
            else:
                reasons.append(tool)

    last_message = str(payload.get("last_assistant_message") or payload.get("lastAssistantMessage") or "")
    if FINISH_RE.search(last_message):
        score += 2
        tags.add("phase_boundary")
    if ERROR_RE.search(last_message) and scoped:
        score += 1
        tags.add("debug_signal")

    if "manual" in tags:
        threshold = 4
    elif {"file_edit", "test"} <= tags or {"file_edit", "build"} <= tags:
        threshold = 6
    else:
        threshold = 6

    return {
        "score": score,
        "threshold": threshold,
        "tags": sorted(tags),
        "reasons": reasons[-6:],
        "should_block": score >= threshold and bool(tags),
    }


def build_additional_context(prompt: str, manual: bool) -> str:
    config = load_config(create=True)
    context = format_context(config)
    skill_dir = Path(__file__).resolve().parent.parent
    lines = [
        context,
        f"- installed skill dir: {skill_dir}",
        "- use skill only for development learning or explicit teaching requests.",
        "- valuable captures include concepts, algorithmic ideas, architecture/data-flow models, project maps; not just tool names.",
        "- when teaching new domain, first map prerequisite concepts and probe user's baseline before explaining mid-level mechanisms.",
        "- after teaching, ask one small optional feedback probe; prefer multiple-choice or true/false, and continue if user skips.",
        "- update knowledge tree with `teach_me.py assess` when you learn what the user does or does not understand.",
        "- final response should stay concise unless user explicitly asked for teaching now.",
    ]
    if manual:
        lines.append(
            "- manual teaching trigger detected: teach now, start with a quick baseline scan, include gentle Socratic questions."
        )
    return "\n".join(lines)


def evidence_summary(assessment: dict[str, Any]) -> str:
    lines = [
        f"- score: {assessment['score']} / threshold {assessment['threshold']}",
        f"- signals: {', '.join(assessment['tags']) or 'none'}",
    ]
    reasons = assessment.get("reasons") or []
    if reasons:
        lines.append("- evidence:")
        lines.extend(f"  - {reason}" for reason in reasons)
    return "\n".join(lines)


def build_stop_review_prompt(config: dict[str, Any], assessment: dict[str, Any]) -> str:
    skill_dir = Path(__file__).resolve().parent.parent
    evidence = evidence_summary(assessment)
    if not config.get("initialized"):
        return f"""Teach Me detected a learning-worthy phase at turn end.

Before writing any learning notes, ask the user to confirm:
- vault path, default `~/.teach_me_skill/vault`
- note language, default `auto`
- whether to enable Git sync; default off unless the user provides a remote

Do not write notes yet. Keep the confirmation concise. Prefix the user-visible
message with `🌱`. Detection evidence:
{evidence}

Teach Me skill dir: {skill_dir}
"""

    return f"""Teach Me detected a learning-worthy phase at turn end.

Continue with a short Teach Me review before the final response:
1. Decide whether this phase deserves 1-3 durable learning notes.
2. Prefer concepts, algorithmic ideas, project maps, hidden complexity, or future bug-risk lessons over tool-name summaries.
3. If useful, run `python3 {skill_dir}/scripts/teach_me.py capture` or `assess` with focused JSON.
4. If no note is actually worth writing after inspection, say that briefly and finish normally.
5. Ask at most one optional quick probe only when it would improve the learner model.
6. Prefix any user-visible Teach Me review, note-capture summary, or setup confirmation with `🌱`.

Detection evidence:
{evidence}
"""


def build_stop_reason() -> str:
    return "🌱"


def handle_stop(payload: dict[str, Any]) -> int:
    if boolish(payload.get("stop_hook_active") or payload.get("stopHookActive")):
        return 0

    config = load_config(create=True)
    events = load_events(config)
    if already_blocked(events, payload):
        return 0

    assessment = score_stop(payload, events)
    decision = "block" if assessment["should_block"] else "allow"
    review_prompt = build_stop_review_prompt(config, assessment) if assessment["should_block"] else ""
    append_event(
        config,
        {
            "type": "stop_decision",
            **event_context(payload),
            "decision": decision,
            "score": assessment["score"],
            "threshold": assessment["threshold"],
            "signal_tags": assessment["tags"],
            "review_prompt": review_prompt,
            "reasons": assessment.get("reasons", []),
        },
    )

    if not assessment["should_block"]:
        return 0

    reason = build_stop_reason()
    output = {
        "decision": "block",
        "reason": reason,
        "systemMessage": "🌱",
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


def handle_prompt(payload: dict[str, Any]) -> int:
    prompt = get_prompt(payload)
    manual = is_manual(prompt)
    dev_like = is_dev_like(prompt)
    maybe_log_prompt_event(payload, prompt, manual, dev_like)
    if not manual and not dev_like:
        return 0
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": build_additional_context(prompt, manual),
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


def main() -> int:
    payload = load_payload()
    event = event_name(payload)

    if event in TOOL_EVENTS or tool_name(payload):
        maybe_log_tool_event(payload)
        return 0

    if event in STOP_EVENTS:
        return handle_stop(payload)

    return handle_prompt(payload)


if __name__ == "__main__":
    sys.exit(main())
