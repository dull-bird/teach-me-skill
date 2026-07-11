# Teaching Profile and Hook Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require explicit teaching-profile consent, remove prompt-based hook routing, make all Teach Me teaching output visibly typed and project-aware, and present a compact Check report table.

**Architecture:** `teach_me.py` owns persistent profile state and teaching metadata vocabulary. `teach_me_hook.py` observes only tools and Stop boundaries; it asks for profile consent only after learning-worthy evidence. Skills own explicit teaching and exam intent. Check consumes the same persisted state to render a Markdown table.

**Tech Stack:** Python 3 standard library, unittest, Markdown, static bilingual HTML.

## Global Constraints

- `config.initialized` means vault setup only; `style-profile.json.profile_initialized` means explicit teaching-style consent.
- Missing profile flags in an existing vault are unconfigured.
- Normal work must never depend on prompt-keyword classification.
- Every Teach Me teaching response begins with `🌱` and an explicit knowledge-domain tag; project context is optional and stable across project renames through a stored project identity.
- Exams stay explicit and opt-in; Stop never starts an exam.

---

### Task 1: Persist teaching-profile consent and metadata vocabulary

**Files:**
- Modify: `skills/teach-me/scripts/teach_me.py`
- Test: `tests/test_teacher_preferences.py`

**Interfaces:**
- Produces `teaching_profile_initialized(style: dict[str, Any]) -> bool`.
- Produces `normalize_teaching_metadata(payload: dict[str, Any]) -> dict[str, str]` with `knowledge_domain`, `project_id`, and `project_name`.

- [ ] **Step 1: Add failing CLI tests** for a legacy style profile lacking `profile_initialized`, explicit `configure --teacher-style default`, and `style --teacher-style coach`.
- [ ] **Step 2: Run** `python3 -m unittest -v tests.test_teacher_preferences` and confirm the new assertions fail because the flag and fields are absent.
- [ ] **Step 3: Add the default false flag, explicit-profile writes, context/status output, and a stable project identity** (canonical path when present, otherwise a normalized immutable first-seen ID). Preserve display names separately so a renamed project remains linked.
- [ ] **Step 4: Run** `python3 -m unittest -v tests.test_teacher_preferences` and confirm it passes.

### Task 2: Restrict hooks to tool evidence and Stop decisions

**Files:**
- Modify: `skills/teach-me/scripts/teach_me_hook.py`
- Modify: `codex/install_hook.py`, `claude-code/install_hook.py`, `kimi/install_hook.py`
- Modify: `codex/config-snippet.toml`, `claude-code/settings-snippet.json`
- Test: `tests/test_teach_me_hook.py`

**Interfaces:**
- `score_stop()` consumes only tool events and completion evidence.
- `build_stop_reason()` returns a profile-setup instruction when profile consent is missing.

- [ ] **Step 1: Add failing tests** that `UserPromptSubmit` produces no output, installers omit it, Stop still blocks after tool-backed work, and an unconfigured profile requests setup rather than capture.
- [ ] **Step 2: Run** `python3 -m unittest -v tests.test_teach_me_hook` and confirm each new test fails for the intended old behavior.
- [ ] **Step 3: Remove prompt parsing/logging and broad keyword scoring; retain tool and Stop events; use `teaching_profile_initialized` to choose the concise setup boundary.**
- [ ] **Step 4: Run** `python3 -m unittest -v tests.test_teach_me_hook` and confirm it passes.

### Task 3: Make teaching output visibly typed and project-aware

**Files:**
- Modify: `skills/teach-me/SKILL.md`
- Modify: `skills/teach-me/scripts/teach_me.py`
- Test: `tests/test_teacher_preferences.py`

**Interfaces:**
- Teach Me response header format: `🌱 [领域：<domain>] [项目：<display name>]` (project segment omitted when unknown).
- Accepted domains: `AI`, `数据库`, `数学`, `物理`, `软件工程`, `产品设计`, `通用`.

- [ ] **Step 1: Add failing tests** that capture metadata is normalized, saved with concepts/knowledge-tree nodes, and preserves a project identity when the display name changes.
- [ ] **Step 2: Run** `python3 -m unittest -v tests.test_teacher_preferences` and confirm failures.
- [ ] **Step 3: Implement metadata persistence and update the skill instructions so all manual and Stop-triggered teaching starts with the exact header and never labels purely mechanical work as a lesson. Add an explicit Exam handoff section.**
- [ ] **Step 4: Run** `python3 -m unittest -v tests.test_teacher_preferences` and confirm it passes.

### Task 4: Replace Check prose counts with clear tables

**Files:**
- Modify: `skills/check/scripts/check_me.py`
- Modify: `skills/check/SKILL.md`
- Test: `tests/test_check.py`

**Interfaces:**
- `check_me.py report` renders Chinese/English Markdown tables for configuration, teaching profile, vault learning data, and hook state.
- JSON report adds profile initialization, profile name, knowledge-domain counts, and project summaries.

- [ ] **Step 1: Add failing tests** for table headers, explicit profile status, domain/project counts, and JSON fields.
- [ ] **Step 2: Run** `python3 -m unittest -v tests.test_check` and confirm expected failures.
- [ ] **Step 3: Gather the new state fields and render small Markdown tables, retaining actionable natural-language follow-ups below them.**
- [ ] **Step 4: Run** `python3 -m unittest -v tests.test_check` and confirm it passes.

### Task 5: Explain the lifecycle publicly and verify the whole change

**Files:**
- Modify: `README.md`, `docs/index.html`, `docs/en/index.html`
- Test: `tests/test_teach_me_hook.py`, `tests/test_teacher_preferences.py`, `tests/test_check.py`

- [ ] **Step 1: Update bilingual copy** to distinguish explicit skill requests from automatic Tool + Stop review; explain profile consent, typed teaching headers, stable project association, and explicit-only Exam.
- [ ] **Step 2: Run targeted tests**: `python3 -m unittest -v tests.test_teacher_preferences tests.test_teach_me_hook tests.test_check`.
- [ ] **Step 3: Run the full suite**: `python3 -m unittest discover -v`.
- [ ] **Step 4: Inspect** `git diff --check` and the Markdown/HTML snippets to verify both languages contain the agreed boundaries and no `UserPromptSubmit` registration remains.
