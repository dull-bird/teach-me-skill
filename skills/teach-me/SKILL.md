---
name: teach-me
description: Development learning companion that turns meaningful coding work into durable learning notes. Use when coding, debugging, reviewing, refactoring, building frontend/backend/mobile projects, explaining architecture, or when the user asks "teach me", "教我", "复盘", "原理", "grill me", "考我". Also use after completing a meaningful development phase to decide whether to write 1-3 high-value Obsidian notes, update concept mastery, and ask gentle Socratic questions without interrupting the user's flow.
---

# Teach Me

## Operating Principle

Help the user accumulate transferable software knowledge while you do the work.
Do not turn every action into a lesson. Work normally during implementation, then
at a natural phase boundary decide whether the work produced knowledge worth
capturing.

Use the local runtime in `scripts/teach_me.py` for configuration, Obsidian note
creation, mastery state updates, and event logging. Hooks may inject a compact
Teach Me context. If hooks are not installed and the task is development-related,
run:

```bash
python3 skills/teach-me/scripts/teach_me.py context
```

If the skill is installed in an agent skill directory, use the installed path
shown in hook context instead.

## First Use

If Teach Me is not initialized, ask the user once before writing learning notes:

- Confirm the default vault path: `~/.teach_me_skill/vault`
- Confirm note language: `auto` means infer from the conversation language and
  keep technical terms in their common English form

After the user confirms, run:

```bash
python3 <teach-me-skill-dir>/scripts/teach_me.py configure --language auto
```

Use `--vault <path>` if the user chooses a different vault path.

## When To Capture

At the end of a meaningful phase, score the work with this rubric:

- Novelty: the user is unlikely to already understand it.
- Transferability: it helps with future projects, not only this file.
- Project relevance: it explains how the current project actually works.
- Hidden complexity: it reveals a mechanism that is easy to miss.
- Future bug risk: misunderstanding it could cause bugs later.
- Algorithmic value: it captures a reasoning pattern, data flow, tradeoff,
  architecture pattern, state model, dependency graph, caching strategy, parsing
  approach, concurrency idea, or other reusable design thought.
- User confusion signal: the user asked "why", used uncertain wording, asked for
  review, or manually triggered teaching.

Default behavior:

- Score 8 or more: capture a full note.
- Score 5-7: capture a compact note only if it is among the top 1-3 items.
- Score below 5: do not teach; at most log a lightweight event.
- Manual trigger: teach even if the current phase is small.

Capture 1-3 core items by default. Capture more only when several items are
clearly high-value and distinct.

Read `references/value-rubric.md` when you need sharper judgment.

## What To Capture

Prefer concept-first notes. Capture these categories:

- Concepts: named ideas such as `Vue reactivity`, `dependency graph`,
  `esbuild`, `event delegation`, `schema validation`.
- Algorithmic ideas: reusable reasoning such as state lifting, incremental
  recomputation, topological ordering, cache invalidation, optimistic updates,
  diffing, debouncing, parsing, normalization, idempotency.
- Project maps: how components, modules, services, routes, build tools, and data
  flows relate inside the current project.

Tool names are signals, not the target. Do not capture `npm install` merely
because a command ran. Capture the underlying idea if it matters.

Read `references/obsidian-format.md` before changing the vault format. Read
`references/schemas.md` before producing JSON for the runtime.

## Teaching Style

Infer language from the user conversation unless the configured language is not
`auto`. Keep common technical names in English when that is clearer.

Default style:

- Explain from first principles.
- Tie the idea to the current project.
- Use a few code-level examples when useful.
- Use analogies at a medium level, then adapt based on feedback.
- Ask 1-2 gentle Socratic questions after important captures.

Occasionally ask for style feedback after valuable notes, not every time:

```text
This explanation used first principles plus project examples. For future notes,
should I use more analogies, fewer analogies and more code, more questions, or
keep this style?
```

If the user answers, update the style profile with:

```bash
python3 <teach-me-skill-dir>/scripts/teach_me.py style --analogy medium --code high --socratic gentle
```

Adjust flags to match the answer.

## Capture Workflow

At a phase boundary:

1. Decide whether there are 1-3 high-value items.
2. If none, say nothing about Teach Me unless the user asked.
3. If Teach Me is uninitialized, ask for first-use confirmation before capture.
4. Build a JSON payload following `references/schemas.md`.
5. Run:

```bash
python3 <teach-me-skill-dir>/scripts/teach_me.py capture <<'JSON'
{
  "project": {"name": "project-name", "path": "/absolute/project/path"},
  "phase": "Short description of the completed phase",
  "language": "auto",
  "summary": "One-sentence learning summary.",
  "items": [
    {
      "type": "concept",
      "title": "dependency graph",
      "importance": 8,
      "mastery": "seen",
      "why_it_matters": "It explains how build tools know what must be rebuilt.",
      "first_principles": [
        "A program is split across files.",
        "Imports create edges between those files.",
        "A build tool can follow those edges to decide what changed."
      ],
      "current_project_context": "Vite follows imports from the entry file to serve and rebuild modules.",
      "relationships": [
        {"target": "Vite", "relation": "uses"},
        {"target": "incremental rebuild", "relation": "enables"}
      ],
      "socratic_questions": [
        "If one imported file changes, how could a build tool avoid rebuilding everything?"
      ]
    }
  ]
}
JSON
```

6. In the final response, keep the teaching report short:

```text
Teach Me captured 2 notes: [[dependency graph]], [[state lifting]].
```

Include the actual explanation in the user-facing answer only when the user
manually asked to be taught now.

## Mastery Updates

Use these mastery levels:

`unknown -> seen -> explained -> practiced -> transferable -> confident`

Do not over-promote mastery because you wrote a note. A concept usually starts
at `seen`, moves to `explained` when the user can restate it, and moves to
`practiced` only after the user applies it.

The runtime stores Anki-like review fields (`next_review`,
`review_interval_days`, `ease`) while keeping the mastery vocabulary simple.
