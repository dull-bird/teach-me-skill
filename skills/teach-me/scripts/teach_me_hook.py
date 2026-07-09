#!/usr/bin/env python3
"""Hook entrypoint for Teach Me.

The hook is intentionally conservative. Prompt hooks inject compact learning
context for obvious learning work. Tool hooks collect evidence. Stop hooks use
that evidence to request exactly one short Teach Me review when a turn appears
learning-worthy.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from teach_me import (  # noqa: E402
    add_user,
    append_jsonl,
    events_path,
    format_context,
    load_config,
    now_iso,
    resolve_user_config,
    save_config,
    USERS_DIR,
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

WORK_SIGNALS = [
    # coding / software
    "code", "coding", "debug", "bug", "frontend", "backend", "refactor", "review",
    "test", "build", "vite", "vue", "react", "svelte", "next.js", "nuxt", "node",
    "typescript", "javascript", "python", "go", "rust", "api", "database", "schema",
    "algorithm", "architecture", "component", "hook",
    # general tool / computer work
    "tool", "tools", "computer", "file", "files", "folder", "document", "data",
    "spreadsheet", "slide", "image", "video", "audio", "design", "draw", "write",
    "analysis", "analyze", "research", "search", "browse", "download", "upload",
    "install", "configure", "setup", "run", "execute", "command", "script",
    # Chinese
    "代码", "开发", "项目", "前端", "后端", "调试", "报错", "实现", "修复", "重构",
    "评审", "测试", "构建", "算法", "架构", "组件", "页面", "接口", "数据库", "状态",
    "依赖",
    "工具", "电脑", "文件", "文件夹", "文档", "数据", "表格", "幻灯片", "图片",
    "视频", "音频", "设计", "画图", "写作", "分析", "研究", "搜索", "浏览",
    "下载", "上传", "安装", "配置", "设置", "运行", "执行", "命令", "脚本",
]

TOOL_EVENTS = {"PreToolUse", "PostToolUse", "PostToolUseFailure"}
STOP_EVENTS = {"Stop"}

VERIFY_RE = re.compile(
    r"\b(pytest|unittest|npm\s+test|pnpm\s+test|yarn\s+test|go\s+test|cargo\s+test|vitest|jest|playwright|test|check|verify|validate)\b",
    re.IGNORECASE,
)
BUILD_RE = re.compile(
    r"\b(build|compile|make|npm\s+run|pnpm\s+build|yarn\s+build|vite\s+build|mdbook\s+build|cargo\s+build|go\s+build)\b",
    re.IGNORECASE,
)
QUALITY_RE = re.compile(
    r"\b(lint|format|typecheck|tsc|mypy|ruff|eslint|biome|prettier|black|cargo\s+clippy|cargo\s+fmt)\b",
    re.IGNORECASE,
)
RESEARCH_RE = re.compile(
    r"\b(rg|grep|sed|find|opencli|curl|context7|scholar|semantic-scholar|search|lookup)\b",
    re.IGNORECASE,
)
ERROR_RE = re.compile(
    r"\b(traceback|exception|error|failed|failure|timeout|panic|segmentation fault|not found|cannot|unable|报错|失败|错误)\b",
    re.IGNORECASE,
)
PASS_RE = re.compile(r"\b(passed|passing|success|successful|complete|ok|通过|完成)\b", re.IGNORECASE)
FINISH_RE = re.compile(
    r"(done|fixed|implemented|verified|completed|tests?\s+pass|build\s+passed|finished|已完成|已修复|已实现|测试通过|构建通过|验证通过|完成|修复|实现|通过)",
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


def is_work_like(prompt: str) -> bool:
    return includes_any(prompt, WORK_SIGNALS)


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


def git_user() -> str:
    """Try to identify the current user from git config."""
    for key in ("user.email", "user.name"):
        try:
            result = subprocess.run(
                ["git", "config", key],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
    return ""


def github_user_from_git(value: str) -> str | None:
    """Extract GitHub username from git email/name if possible."""
    if not value:
        return None
    if "@users.noreply.github.com" in value:
        # e.g. dull-bird@users.noreply.github.com -> dull-bird
        return value.split("@")[0]
    if value.endswith("@github.com"):
        return value.split("@")[0]
    return None


def resolve_user_id(payload: dict[str, Any]) -> str:
    """Determine active user from payload, env, git config, or config default.

    Git config is only used if the extracted GitHub user already exists in the
    config, so that machines with a global git identity do not auto-switch
    away from the current user.
    """
    user_id = payload.get("user_id") or payload.get("userId")
    if user_id:
        return str(user_id)

    env_user = os.environ.get("TEACH_ME_USER")
    if env_user:
        return env_user

    top_config = load_config(create=True)
    users = top_config.get("users", {})

    git = git_user()
    gh = github_user_from_git(git)
    if gh and gh in users:
        return gh

    return str(top_config.get("current_user", "default"))


def ensure_user(payload: dict[str, Any]) -> dict[str, Any]:
    """Return resolved user config, creating the user if necessary."""
    top_config = load_config(create=True)
    user_id = resolve_user_id(payload)
    if user_id not in top_config.get("users", {}):
        add_user(top_config, user_id, name=user_id)
        save_config(top_config)
    return resolve_user_config(top_config, user_id)


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

    # Creation / modification of files, data, or documents
    if any(k in lowered_tool for k in ("write", "edit", "replace", "patch", "save", "create")):
        tags.add("modification")
        score += 4

    # Verification / testing / quality checks (generic, not only code)
    if VERIFY_RE.search(command) or re.search(r"\b\d+\s+passed\b|\b\d+\s+failed\b", output, re.IGNORECASE):
        tags.add("verification")
        score += 4

    if BUILD_RE.search(command):
        tags.add("build")
        score += 3

    if QUALITY_RE.search(command):
        tags.add("quality_check")
        score += 3

    # Research / reading / searching
    if RESEARCH_RE.search(command) or any(k in lowered_tool for k in ("read", "search", "fetch", "grep", "glob", "web", "open", "browse")):
        tags.add("research")
        score += 1

    # Errors and failures are strong learning signals across all domains
    if ERROR_RE.search(combined):
        tags.add("error_signal")
        score += 3

    if PASS_RE.search(output) and tags:
        tags.add("verified")
        score += 1

    # Any non-shell tool use is a signal
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


def maybe_log_prompt_event(payload: dict[str, Any], prompt: str, manual: bool, work_like: bool) -> None:
    user_cfg = ensure_user(payload)
    append_event(
        user_cfg,
        {
            "type": "prompt",
            **event_context(payload),
            "manual": manual,
            "work_like": work_like,
            "user_id": user_cfg.get("_user_id", "default"),
            "prompt": prompt[:500],
            "score": 4 if manual else (2 if work_like else 0),
            "signal_tags": ["manual"] if manual else (["work_like"] if work_like else []),
        },
    )


def maybe_log_tool_event(payload: dict[str, Any]) -> None:
    user_cfg = ensure_user(payload)
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
        user_cfg,
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
            "user_id": user_cfg.get("_user_id", "default"),
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
    elif {"modification", "verification"} <= tags or {"modification", "build"} <= tags:
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


def build_additional_context(prompt: str, manual: bool, user_cfg: dict[str, Any]) -> str:
    context = format_context(user_cfg)
    skill_dir = Path(__file__).resolve().parent.parent
    lines = [
        context,
        f"- installed skill dir: {skill_dir}",
        "- use skill for any tool-based work: coding, writing, design, data analysis, configuration, research, etc.",
        "- valuable captures include concepts, algorithmic ideas, workflows, hidden mechanisms, project maps; not just tool names.",
        "- when teaching a new domain, first map prerequisite concepts and probe the user's baseline before explaining mid-level mechanisms.",
        "- after teaching, ask one small optional feedback probe; prefer multiple-choice or true/false, and continue if user skips.",
        "- update knowledge tree with `teach_me.py assess --user <id>` when you learn what the user does or does not understand.",
        "- final response should teach something: explain the idea, ask a follow-up, then mention captured notes.",
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
    user_id = config.get("_user_id", "default")
    user_flag = f" --user {user_id}" if user_id != "default" else ""
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

Before finishing, do a short Teach Me review that actually teaches the user something:
1. Identify the 1-3 most valuable concepts, algorithmic ideas, hidden mechanisms, or bug-risk lessons from this phase.
2. In 1-2 plain sentences, explain the core idea to the user as if teaching a beginner. Connect it to something they already know if possible.
3. Ask one short, concrete follow-up: a Socratic question, a true/false check, or "要不要我展开讲讲？". Do not just announce that you wrote a note.
4. If the user wants to go deeper, explain missing prerequisites first (e.g. "什么是 Canvas", "什么是状态驱动动画"). Never make the user dig through the vault to learn.
5. Only after teaching, if a durable note is warranted, run `python3 {skill_dir}/scripts/teach_me.py capture{user_flag}` or `assess{user_flag}`.
6. If nothing is worth capturing after reflection, say so briefly and finish normally.
7. Prefix the user-visible teaching message with `🌱`.

Detection evidence:
{evidence}
"""


def build_stop_reason(config: dict[str, Any], assessment: dict[str, Any]) -> str:
    return "🌱 " + build_stop_review_prompt(config, assessment)


def handle_stop(payload: dict[str, Any]) -> int:
    if boolish(payload.get("stop_hook_active") or payload.get("stopHookActive")):
        return 0

    user_cfg = ensure_user(payload)
    events = load_events(user_cfg)
    if already_blocked(events, payload):
        return 0

    assessment = score_stop(payload, events)
    decision = "block" if assessment["should_block"] else "allow"
    review_prompt = build_stop_review_prompt(user_cfg, assessment) if assessment["should_block"] else ""
    append_event(
        user_cfg,
        {
            "type": "stop_decision",
            **event_context(payload),
            "decision": decision,
            "score": assessment["score"],
            "threshold": assessment["threshold"],
            "signal_tags": assessment["tags"],
            "review_prompt": review_prompt,
            "reasons": assessment.get("reasons", []),
            "user_id": user_cfg.get("_user_id", "default"),
        },
    )

    if not assessment["should_block"]:
        return 0

    reason = build_stop_reason(user_cfg, assessment)
    # Codex 在 Stop payload 里会带 transcript_path，Kimi 没有；据此选择输出格式
    is_codex = bool(payload.get("transcript_path") is not None or "codex" in cwd(payload).lower())
    if is_codex:
        # Codex Stop 识别 decision=block + reason
        output = {"decision": "block", "reason": reason, "systemMessage": "🌱"}
    else:
        # Kimi Code CLI 识别 hookSpecificOutput.permissionDecision=deny
        output = {
            "hookSpecificOutput": {
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    print(json.dumps(output, ensure_ascii=False))
    return 0


def handle_prompt(payload: dict[str, Any]) -> int:
    prompt = get_prompt(payload)
    manual = is_manual(prompt)
    work_like = is_work_like(prompt)
    user_cfg = ensure_user(payload)
    maybe_log_prompt_event(payload, prompt, manual, work_like)
    if not manual and not work_like:
        return 0

    context = build_additional_context(prompt, manual, user_cfg)
    user_id = user_cfg.get("_user_id", "default")
    is_codex = bool(payload.get("transcript_path") is not None or "codex" in cwd(payload).lower())

    if manual:
        # Direct teaching trigger: block the turn and ask the agent to teach now.
        skill_dir = Path(__file__).resolve().parent.parent
        user_flag = f" --user {user_id}" if user_id != "default" else ""
        reason = f"""🌱 User explicitly asked for teaching/review.

{context}

Do a short Teach Me session right now:
1. Look up related concepts in the user's vault (run `python3 {skill_dir}/scripts/teach_me.py context{user_flag}` if you need the current state).
2. Briefly explain the core idea in plain language, matching the user's speaking style.
3. Ask one short follow-up question (Socratic, true/false, or "要不要我展开讲讲？").
4. If the user wants deeper explanation, cover missing prerequisites first.
5. Capture or assess only if the conversation reveals new understanding worth saving.
"""
        if is_codex:
            output = {"decision": "block", "reason": reason, "systemMessage": "🌱"}
        else:
            output = {
                "hookSpecificOutput": {
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        print(json.dumps(output, ensure_ascii=False))
        return 0

    # Work-like prompt: just inject context for later Stop-hook review.
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
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
