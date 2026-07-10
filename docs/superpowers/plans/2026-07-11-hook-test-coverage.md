# Hook Test Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add regression tests for prompt parsing, tool-failure evidence, and Stop output boundaries in the Teach Me hook.

**Architecture:** Tests execute `skills/teach-me/scripts/teach_me_hook.py` through the existing `run_hook` helper and isolate persistent state with `TemporaryDirectory`. Assertions use the public JSON response and `events.jsonl`, rather than importing private implementation helpers.

**Tech Stack:** Python 3 standard library `unittest`, `subprocess`, and temporary filesystem fixtures.

## Global Constraints

- Modify tests only; do not change `teach_me_hook.py` production behavior.
- Keep the existing `video/public/narration.mp3` worktree change untouched.
- Run the focused hook module before the full Python suite.
- Each new test must assert stable protocol fields or persisted event fields, not full generated prose.

---

### Task 1: Cover message-array prompt parsing

**Files:**
- Modify: `tests/test_teach_me_hook.py` after `test_manual_prompt_injects_context_without_blocking`
- Test: `tests/test_teach_me_hook.py`

**Interfaces:**
- Consumes: `run_hook(payload, home) -> subprocess.CompletedProcess[str]` and `parse_stdout(result) -> dict`
- Produces: Regression coverage that `get_prompt` recognizes a manual teaching trigger supplied in `payload["messages"][-1]["content"]`.

- [ ] **Step 1: Add the regression test**

```python
def test_messages_prompt_with_manual_trigger_injects_context(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = run_hook(
            {
                "hook_event_name": "UserPromptSubmit",
                "messages": [{"content": "请解释 Hook 的事件边界。"}],
                "session_id": "s-messages",
                "turn_id": "t-messages",
            },
            Path(tmp),
        )

    self.assertEqual(result.returncode, 0, result.stderr)
    context = parse_stdout(result)["hookSpecificOutput"]["additionalContext"]
    self.assertIn("requested teaching", context)
    self.assertIn("SKILL.md", context)
```

- [ ] **Step 2: Run the focused module**

Run: `python3 -m unittest -v tests.test_teach_me_hook`

Expected: the new message-array test and all existing hook tests pass.

- [ ] **Step 3: Commit the test addition**

```bash
git add tests/test_teach_me_hook.py
git commit -m "test: cover message-array hook prompts"
```

### Task 2: Cover failed tool events and non-dictionary payloads

**Files:**
- Modify: `tests/test_teach_me_hook.py` after `test_pre_and_post_tool_events_are_logged_even_before_initialization`
- Test: `tests/test_teach_me_hook.py`

**Interfaces:**
- Consumes: `read_events(home) -> list[dict]`
- Produces: Regression coverage that a `PostToolUseFailure` event preserves its phase and error signal even when tool input and response are scalar values.

- [ ] **Step 1: Add the regression test**

```python
def test_failed_tool_event_records_error_signal_for_scalar_payloads(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        result = run_hook(
            {
                "hook_event_name": "PostToolUseFailure",
                "tool_name": "Bash",
                "tool_input": "pytest tests/test_parser.py",
                "tool_response": "Command failed: exit status 1",
                "session_id": "s-failure",
                "turn_id": "t-failure",
                "cwd": "/repo",
            },
            home,
        )
        events = read_events(home)

    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(result.stdout, "")
    self.assertEqual(len(events), 1)
    self.assertEqual(events[0]["phase"], "failure")
    self.assertIn("error_signal", events[0]["signal_tags"])
    self.assertEqual(events[0]["command"], "")
```

- [ ] **Step 2: Run the focused module**

Run: `python3 -m unittest -v tests.test_teach_me_hook`

Expected: the new failure-event test and all existing hook tests pass.

- [ ] **Step 3: Commit the test addition**

```bash
git add tests/test_teach_me_hook.py
git commit -m "test: cover failed hook tool events"
```

### Task 3: Cover Codex Stop format for low-evidence events

**Files:**
- Modify: `tests/test_teach_me_hook.py` after `test_codex_stop_uses_decision_block_format`
- Test: `tests/test_teach_me_hook.py`

**Interfaces:**
- Consumes: a Stop payload with `transcript_path`, which selects the Codex output branch only when Stop review is needed.
- Produces: Regression coverage that a Codex-shaped Stop payload with weak evidence is silent rather than emitting an allow/block JSON response.

- [ ] **Step 1: Add the regression test**

```python
def test_codex_stop_with_weak_evidence_stays_silent(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        run_hook(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "pwd"},
                "session_id": "s-codex-weak",
                "turn_id": "t-codex-weak",
                "cwd": "/repo",
            },
            home,
        )
        result = run_hook(
            {
                "hook_event_name": "Stop",
                "session_id": "s-codex-weak",
                "turn_id": "t-codex-weak",
                "cwd": "/repo",
                "transcript_path": "/tmp/codex-transcript.jsonl",
                "stop_hook_active": False,
                "last_assistant_message": "当前目录是 /repo。",
            },
            home,
        )

    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(result.stdout, "")
```

- [ ] **Step 2: Run focused and full verification**

Run: `python3 -m unittest -v tests.test_teach_me_hook && python3 -m unittest discover -v tests`

Expected: both commands exit with status `0`; no test output reports failures or errors.

- [ ] **Step 3: Commit the completed test suite**

```bash
git add tests/test_teach_me_hook.py docs/superpowers/plans/2026-07-11-hook-test-coverage.md
git commit -m "test: expand hook regression coverage"
```
