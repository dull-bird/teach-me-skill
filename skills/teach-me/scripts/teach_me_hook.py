#!/usr/bin/env python3
"""Hook entrypoint for Teach Me tool evidence and phase-boundary decisions."""

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
    active_goal_session,
    add_user,
    append_jsonl,
    events_path,
    load_config,
    now_iso,
    quiet_window_elapsed,
    read_state,
    read_style,
    resolve_user_config,
    save_config,
    teaching_profile_initialized,
    USERS_DIR,
)


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


def is_file_writer(tool: str) -> bool:
    lowered = tool.lower()
    return any(k in lowered for k in ("write", "edit", "replace", "patch", "save", "create"))


def extract_content_excerpt(input_value: Any, tool: str, limit: int = 1500) -> str:
    """Extract a meaningful excerpt of new content from write/edit tools."""
    if not isinstance(input_value, dict):
        return ""
    lowered = tool.lower()

    # Edit/Replace tools: show the replacement, which is the actual change
    for key in ("new_string", "newString", "new", "replacement", "content"):
        value = input_value.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:limit]

    # Write/Create tools: show beginning of the written content
    for key in ("content", "text", "data"):
        value = input_value.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:limit]

    return ""


def extract_content_diff(input_value: Any, tool: str, limit: int = 1200) -> str:
    """For edit tools, return a mini diff of old -> new."""
    if not isinstance(input_value, dict):
        return ""
    old = ""
    new = ""
    for key in ("old_string", "oldString", "old"):
        value = input_value.get(key)
        if isinstance(value, str):
            old = value.strip()
            break
    for key in ("new_string", "newString", "new", "replacement", "content"):
        value = input_value.get(key)
        if isinstance(value, str):
            new = value.strip()
            break
    if old or new:
        text = f"--- old\n{old[:limit]}\n+++ new\n{new[:limit]}"
        return text[: limit * 2 + 30]
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

    # Research / reading / searching. Weighted higher than a bare "tool use"
    # fallback because reading-only phases (importing a book/PDF, working
    # through docs, discussing an article) have no write/verify/build
    # evidence at all — without this, conceptually important but code-free
    # work would almost never cross the auto-review threshold.
    if RESEARCH_RE.search(command) or any(k in lowered_tool for k in ("read", "search", "fetch", "grep", "glob", "web", "open", "browse")):
        tags.add("research")
        score += 2

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
    activity = f"{command}\n{file_path}".replace("\\", "/").lower()
    if "/skills/teach-me/skill.md" in activity or "/skills/teach-me/scripts/teach_me.py" in activity:
        score, tags = 0, []
    phase = {
        "PreToolUse": "pre",
        "PostToolUse": "post",
        "PostToolUseFailure": "failure",
    }.get(event, "tool")
    data: dict[str, Any] = {
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
    }
    if is_file_writer(tool):
        data["content_excerpt"] = extract_content_excerpt(input_value, tool)[:1500]
        data["content_diff"] = extract_content_diff(input_value, tool)[:1200]
    append_event(user_cfg, data)


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


def has_new_scored_work_since_last_block(events: list[dict[str, Any]], payload: dict[str, Any]) -> bool:
    """Allow another review only after meaningful new work in the same scope.

    Some clients do not expose a Stop re-entrancy flag. This event-based
    fallback prevents repeated blocks after a review while allowing a later
    phase to request a new review when the user resumed work.
    """
    scoped = [event for event in events if same_scope(event, payload)]
    last_block_index = max(
        (
            index
            for index, event in enumerate(scoped)
            if event.get("type") == "stop_decision" and event.get("decision") == "block"
        ),
        default=None,
    )
    if last_block_index is None:
        return True
    return any(
        event.get("type") == "tool" and int(event.get("score") or 0) > 0
        for event in scoped[last_block_index + 1 :]
    )


def modified_files(events: list[dict[str, Any]], payload: dict[str, Any]) -> list[str]:
    """Collect file paths that were written or edited in the current scope."""
    scoped = [event for event in events if same_scope(event, payload)]
    files: list[str] = []
    seen: set[str] = set()
    for event in scoped:
        if event.get("type") != "tool":
            continue
        tags = event.get("signal_tags", []) or []
        if "modification" not in tags:
            continue
        path = str(event.get("file_path") or "").strip()
        if path and path not in seen:
            seen.add(path)
            files.append(path)
    return files[-8:]


def score_stop(payload: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    scoped = [event for event in events if same_scope(event, payload)]
    tags: set[str] = set()
    reasons: list[str] = []
    score = 0

    for event in scoped:
        if event.get("type") == "tool" and event.get("phase") == "pre":
            continue
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

    if {"modification", "verification"} <= tags or {"modification", "build"} <= tags:
        threshold = 6
    else:
        threshold = 7

    return {
        "score": score,
        "threshold": threshold,
        "tags": sorted(tags),
        "reasons": reasons[-6:],
        "modified_files": modified_files(events, payload),
        "should_block": score >= threshold and bool(tags),
    }


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
    """Full review prompt written to the event log for audit/debugging."""
    skill_dir = Path(__file__).resolve().parent.parent
    evidence = evidence_summary(assessment)
    user_id = config.get("_user_id", "default")
    user_flag = f" --user {user_id}" if user_id != "default" else ""
    if not config.get("initialized"):
        return f"""Teach Me review requires first-use confirmation.
Follow `{skill_dir}/SKILL.md`. STOP: defaults are not consent. In this turn, do not run `configure`, `capture`, or write any note. Your entire user-facing response must only present one concise setup choice and wait for an explicit reply: (1) default balanced tutor, (2) implementation coach, (3) general-principles mentor, (4) Socratic tutor with one focused question, or (5) a free-text custom style. Also mention default vault/language and optional Git sync. Only after the user's next message explicitly chooses settings may you run `python3 {skill_dir}/scripts/teach_me.py configure ...{user_flag}` and treat setup as complete.

Detection evidence:
{evidence}
"""

    if not teaching_profile_initialized(read_style(config)):
        return f"""Teach Me teaching-profile setup is required before review.
Follow `{skill_dir}/SKILL.md`. Do not teach, assess, capture, or write notes in this turn. Ask the user to choose exactly one style: (1) default balanced tutor, (2) implementation coach, (3) general-principles mentor, (4) Socratic tutor, or (5) custom. Explain that runtime fallback values are not a confirmed teaching preference. Wait for an explicit reply, then run `python3 {skill_dir}/scripts/teach_me.py configure --teacher-style <choice>{user_flag}`.

Detection evidence:
{evidence}
"""

    modified = assessment.get("modified_files", [])
    modified_hint = ""
    if modified:
        modified_hint = "\nFiles created or edited in this phase:\n" + "\n".join(f"- {p}" for p in modified)
        modified_hint += "\nRead these files (or the conversation transcript) to understand the substance before teaching."

    prompt = f"""Teach Me review required at this phase boundary.
Follow `{skill_dir}/SKILL.md` and first run `python3 {skill_dir}/scripts/teach_me.py context --full{user_flag}`. Review the actual work and teach exactly one core mechanism by default from the learner's first weak prerequisite in 1-2 plain sentences; add a second only when essential. Never present tool steps as knowledge. Ask zero or one optional, single-part follow-up; skip it when the user requested brevity. Capture or assess only after teaching when warranted.

Begin your entire user-facing response with `🌱 [领域：<知识领域>]`, using one of AI, 数据库, 数学, 物理, 软件工程, 产品设计, or 通用. If the actual work identifies a project, append ` [项目：<当前项目名>]`. This header is required for every Teach Me lesson, whether it was requested directly or triggered at Stop.

Detection evidence:
{evidence}{modified_hint}
"""
    if os.environ.get("TEACH_ME_CONTEXT_MODE", "short").lower() == "expanded":
        prompt += "\nExpanded A/B instructions: distinguish mechanisms from commands; map prerequisites; connect to prior knowledge; honor teacher profile and knowledge focus; teach before capture; skip purely mechanical work; never ask a multi-part question.\n"
    return prompt


def build_stop_reason(config: dict[str, Any], assessment: dict[str, Any]) -> str:
    """Compact pointer returned to the agent as the blocking reason.

    The full workflow and audit trail live in SKILL.md and the event log.
    """
    skill_dir = Path(__file__).resolve().parent.parent
    if not config.get("initialized"):
        return f"Teach Me review requires setup. Read and follow `{skill_dir}/SKILL.md`."
    if not teaching_profile_initialized(read_style(config)):
        return f"Teach Me teaching-profile setup required. Read and follow `{skill_dir}/SKILL.md`; ask for one explicit style choice before teaching or capture."

    return f"Teach Me review required. Read and follow `{skill_dir}/SKILL.md`."


def handle_stop(payload: dict[str, Any]) -> int:
    if boolish(payload.get("stop_hook_active") or payload.get("stopHookActive")):
        return 0

    user_cfg = ensure_user(payload)
    events = load_events(user_cfg)
    goal = active_goal_session(read_state(user_cfg), cwd(payload))
    if goal is not None:
        # A goal-end session deliberately absorbs ordinary phase reviews. It
        # either waits for explicit completion or, when the opt-in window has
        # elapsed, asks the agent to generate one accumulated project summary.
        if quiet_window_elapsed(goal) and not goal.get("summary_requested_at"):
            goal_id = str(goal.get("id") or "")
            user_id = user_cfg.get("_user_id", "default")
            user_flag = f" --user {user_id}" if user_id != "default" else ""
            reason = (
                "Teach Me quiet-window summary is ready. Read and follow "
                f"`{Path(__file__).resolve().parent.parent}/SKILL.md`, then run "
                f"`python3 {Path(__file__).resolve().parent}/teach_me.py goal summary --id {goal_id}{user_flag}` "
                "and use its prompt_for_ai to write one coherent paragraph plus exactly 5 knowledge points."
            )
            append_event(
                user_cfg,
                {
                    "type": "stop_decision",
                    **event_context(payload),
                    "decision": "request_goal_summary",
                    "goal_id": goal_id,
                    "quiet_window_minutes": int(goal.get("quiet_window_minutes") or 0),
                    "reason": reason,
                    "user_id": user_id,
                },
            )
            is_codex = bool(payload.get("transcript_path") is not None or "codex" in cwd(payload).lower())
            if is_codex:
                print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
            else:
                print(json.dumps({"hookSpecificOutput": {"permissionDecision": "deny", "permissionDecisionReason": reason}}, ensure_ascii=False))
            return 0

        append_event(
            user_cfg,
            {
                "type": "stop_decision",
                **event_context(payload),
                "decision": "defer_goal_end",
                "goal_id": goal.get("id"),
                "quiet_window_minutes": int(goal.get("quiet_window_minutes") or 0),
                "user_id": user_cfg.get("_user_id", "default"),
            },
        )
        return 0

    if not has_new_scored_work_since_last_block(events, payload):
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
        output = {"decision": "block", "reason": reason}
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


def main() -> int:
    payload = load_payload()
    debug_payload_path = os.environ.get("TEACH_ME_DEBUG_PAYLOAD_PATH")
    if debug_payload_path:
        debug_path = Path(debug_payload_path).expanduser()
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        with debug_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    event = event_name(payload)

    if event in TOOL_EVENTS or tool_name(payload):
        maybe_log_tool_event(payload)
        return 0

    if event in STOP_EVENTS:
        return handle_stop(payload)

    return 0


if __name__ == "__main__":
    sys.exit(main())
