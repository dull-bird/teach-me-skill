# Teach Me Exam — Operation Manual

## Overview

Teach Me Exam turns the user's learning portrait into adaptive quizzes and tests. It does not generate natural-language questions by itself; it selects concepts, assigns formats, and records results. The AI agent uses the generated plan to compose the actual exam paper.

## Files

- `~/.teach_me_skill/config.json` — user config (v2 multi-user)
- `~/.teach_me_skill/vault/.teach-me/learning-state.json` — learner state
- `~/.teach_me_skill/vault/07_Learning_Profile/Knowledge_Tree.md` — generated knowledge tree
- `~/.teach_me_skill/vault/07_Learning_Profile/Exam_History.md` — generated exam history
- `~/.teach_me_skill/vault/00_Index.md` — generated index

## User interaction flow

1. **Collect preferences with `AskUserQuestion`** — Ask for scope, question style, and exam size. The AI estimates time and picks fixed formats automatically.
2. **Generate a plan** — Run `exam.py plan` with the collected parameters.
3. **Deliver questions** —
   - True/false and multiple-choice questions may be delivered through a second `AskUserQuestion` form.
   - Short-answer and coding questions must be delivered in the chat; `AskUserQuestion`'s "Other" field is too small and hard to edit for multi-line answers or pasted code.
   - Project-applied questions must provide context from the user's notes; do not assume the user remembers implementation details.
   - In `AskUserQuestion`, use option text as labels. Do not add `A/B/C/D` wrappers; the UI already numbers options.
4. **Record results** — After the user finishes, run `exam.py grade`.

## Planning an exam

```bash
python3 exam.py plan --time 15
python3 exam.py plan --time 30 --topic Python
python3 exam.py plan --type quiz --formats mcq,tf
```

The plan JSON includes:

- `session_id` — unique exam identifier
- `time_budget_minutes`
- `type` — quiz / test / exam
- `formats` — list of question formats
- `concepts` — selected concepts with assigned formats
- `prompt_for_ai` — a ready-to-use prompt for the AI to generate the paper

## Time-to-type mapping

- ≤ 10 minutes → `quiz` (4 questions, tf + mcq)
- 11–30 minutes → `test` (7 questions, tf + mcq + short)
- > 30 minutes → `exam` (12 questions, all formats)

## Recording results

Pipe a JSON payload to `exam.py grade`:

```bash
echo '{
  "plan": { "session_id": "exam-20260709-105855", "type": "test" },
  "results": [
    { "name": "PDF page tree", "format": "short", "correct": true, "confidence": 0.8 }
  ]
}' | python3 exam.py grade
```

The command updates mastery, schedules the next review, and rewrites Markdown files.

## Viewing history

```bash
python3 exam.py history    # all sessions
python3 exam.py stats      # aggregate statistics
python3 exam.py topics     # available topic filters
```

## Mastery update rules

- Correct with confidence ≥ 0.8 → mastery increases by one level
- Correct with low confidence → mastery stays the same
- Incorrect → mastery drops by one level; `needs_probe` is set on knowledge-tree nodes

Levels (weakest to strongest): `unknown → seen → explained → practiced → transferable → confident`.

## Per-user support

All commands accept `--user <user_id>` to target a specific user's vault.

## Error codes

- `0` — success
- `1` — bad input / missing data
- `2` — Teach Me not initialized
