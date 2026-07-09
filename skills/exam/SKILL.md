---
name: exam
description: Generate adaptive quizzes and tests from the Teach Me learner portrait. Use when the user asks to be tested, quizzed, or wants an exam on topics in their vault.
---

# Teach Me Exam

Turn the user's captured concepts and knowledge-tree nodes into adaptive quizzes, tests, and hands-on exams. The skill plans what to test and records results; the AI agent composes the actual questions and collects answers.

## When to use

Trigger this skill when the user says anything like:

- “考考我”
- “给我出套卷子”
- “我要做题”
- “quiz me”
- “test me”
- “来场考试”
- “检测一下我学得怎么样”

## How it works

1. **Collect preferences with a form** — Use `AskUserQuestion` to ask for scope, question style, and exam size. The AI estimates time and picks fixed formats automatically.
2. **Plan** — Run `exam.py plan` to select weak concepts and assign formats.
3. **Generate questions** — Use the `prompt_for_ai` field from the plan to compose the actual exam paper.
   - **Pure-knowledge questions** test the concept directly.
   - **Project-applied questions** provide context from the user's notes/projects and test the underlying knowledge; do **not** assume the user remembers implementation details.
4. **Collect answers** —
   - **True/false and multiple-choice** can be delivered through another `AskUserQuestion` form.
   - **Short-answer and coding questions** must be collected in the chat, because `AskUserQuestion` only supports selecting predefined options; its free-text "Other" field is too small and hard to edit for multi-line answers or code.
5. **Grade** — After the user finishes, run `exam.py grade` with the results to update mastery and record the session.

## Commands

```bash
# Plan a 15-minute test
python3 ~/.codex/skills/exam/scripts/exam.py plan --time 15

# Plan a focused Python quiz
python3 ~/.codex/skills/exam/scripts/exam.py plan --time 10 --topic Python --type quiz

# Plan with specific formats
python3 ~/.codex/skills/exam/scripts/exam.py plan --time 30 --formats mcq,short,coding

# Record graded results
python3 ~/.codex/skills/exam/scripts/exam.py grade < results.json

# View history and stats
python3 ~/.codex/skills/exam/scripts/exam.py history
python3 ~/.codex/skills/exam/scripts/exam.py stats
python3 ~/.codex/skills/exam/scripts/exam.py topics
```

All commands support `--user <user_id>` and `--json`.

## Exam types

| Type | Time budget | Questions | Default formats |
|------|-------------|-----------|-----------------|
| `quiz` | ≤ 10 min | 4 | tf, mcq |
| `test` | 11–30 min | 7 | tf, mcq, short |
| `exam` | > 30 min | 12 | tf, mcq, short, coding |

## Question formats

- `mcq` — Multiple choice
- `tf` — True / false
- `short` — Short answer / explanation
- `coding` — Hands-on coding task (user writes code in editor and pastes it back)

## Grading JSON format

```json
{
  "session_id": "exam-20260709-105855",
  "results": [
    {
      "name": "PDF page tree",
      "format": "short",
      "correct": true,
      "confidence": 0.8,
      "notes": "User explained parent-child structure correctly"
    },
    {
      "name": "Python decorator",
      "format": "coding",
      "correct": true,
      "confidence": 0.9,
      "notes": "Implementation correct, timing explanation solid"
    }
  ]
}
```

Mastery update rules:

- `correct` + `confidence >= 0.8` → bump mastery up one level
- `correct` + low confidence → keep current mastery
- `incorrect` → drop one level and mark `needs_probe`

## AskUserQuestion preference form

When the user asks for an exam, use `AskUserQuestion` to collect setup preferences:

1. **Scope** — `Weak areas only`, `Specific project / topic`, `Everything`
2. **Question style** — `Pure knowledge`, `Project-applied (I give context)`
3. **Exam size** — `Quiz (~5 min)`, `Test (~15 min)`, `Exam (~30+ min)`

Then call `exam.py plan --time <minutes> [--topic <topic>] [--type <type>] [--formats <formats>]`.

## Delivering the exam

- If the plan contains **only** true/false and multiple-choice questions, you may present all questions in a single `AskUserQuestion` form.
- If the plan contains **short-answer or coding questions**, present those in the chat. Tell the user to type or paste their answer in the next message. Do **not** use `AskUserQuestion` for these, because its free-text "Other" field is too small and hard to edit for multi-line answers or code.
- For coding questions, explicitly instruct the user to write code in their editor and paste it back into the chat.

### Option labels in `AskUserQuestion`

Do **not** wrap choices in `A/B/C/D` or `对/错` labels. The UI already adds `[1]`, `[2]`, etc. Use the option text itself as the `label`:

- True/false: labels are `对` and `错` (descriptions are optional).
- Multiple choice: labels are the actual answer texts, e.g. `主执行路径`, `主路径失败时使用的备选路径`.

This avoids the redundant `A` + `[1]` rendering.

## Project-applied questions

When the user chooses **Project-applied**, generate questions like word problems:

- Provide the relevant project context or note excerpt.
- Ask about the underlying concept, trade-off, or principle.
- Do **not** ask the user to recall specific file paths, function names, or implementation details unless those details are given in the question.

Example:

> In the inkwell project, the native shell uses a Qt WebChannel + JSON-line stdio Node host so that the React side panel can reuse the existing AgentSession. What problem does this layering solve, compared to running the agent logic directly inside the Qt main process?

## Natural-language follow-ups

Offer these examples to the user:

- “再给我出一道”
- “换一道难的”
- “这个知识点再考一次”
- “查看我的考试统计”
