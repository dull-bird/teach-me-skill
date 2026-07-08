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

Teach Me must behave like a tutor with a growing learner model, not only a
recap writer. When a new domain appears, build a small prerequisite ladder,
estimate the user's current level from the conversation, and start teaching at
the first weak or unknown node. Do not jump into mid-level mechanisms if basic
terms are probably unclear.

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
- Ask whether they want Git sync for cross-device learning state. Default is
  off. If they already have a remote repository, ask for the URL and enable
  auto-sync. If they do not have one or are busy, skip it and continue.

After the user confirms, run:

```bash
python3 <teach-me-skill-dir>/scripts/teach_me.py configure --language auto
```

Use `--vault <path>` if the user chooses a different vault path.

Use Git sync options only when the user explicitly opts in:

```bash
python3 <teach-me-skill-dir>/scripts/teach_me.py configure \
  --language auto \
  --git-remote git@github.com:user/teach-me-vault.git \
  --auto-sync
```

If the user wants local-only versioning without a remote, use
`--enable-git-sync` without `--git-remote`.

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

## Learner Modeling

Before teaching a domain that may be unfamiliar, do a quick baseline scan:

1. Name the domain, for example `mihomo proxy routing`.
2. Sketch 5-10 prerequisite concepts from basic to advanced, for example
   `proxy`, `proxy node`, `subscription provider`, `config.yaml`,
   `proxy group`, `selector`, `url-test`, `fallback`.
3. Infer what the user likely knows from their wording, prior notes, and
   questions. Mark uncertain basics as `unknown` or `seen`, not `explained`.
4. Ask 1-3 short calibration questions only when useful, or inline a short
   "foundation sweep" before the main explanation.
5. Teach from the first weak prerequisite upward, then connect it to the
   specific bug or implementation detail.

Use the runtime to update the knowledge tree when you learn the user's level:

```bash
python3 <teach-me-skill-dir>/scripts/teach_me.py assess <<'JSON'
{
  "project": {"name": "project-name", "path": "/absolute/project/path"},
  "domain": "mihomo proxy routing",
  "summary": "The user asked what mysub.yaml contains, so basic proxy configuration terms need a foundation sweep.",
  "nodes": [
    {
      "title": "mihomo",
      "mastery": "seen",
      "confidence": 0.4,
      "prerequisites": ["proxy"],
      "gaps": ["May not yet have a crisp model of what a local proxy daemon does."],
      "probes": ["What does mihomo do between your browser and the remote server?"],
      "evidence": ["Asked for basic definitions after fallback explanation."]
    },
    {
      "title": "proxy node",
      "mastery": "unknown",
      "confidence": 0.25,
      "prerequisites": ["proxy server"],
      "probes": ["What fields would you expect a node to need: name, server, port, password, protocol?"]
    }
  ],
  "questions": [
    "Can you explain the difference between a proxy node and a proxy group?"
  ]
}
JSON
```

The knowledge tree is allowed to grow even when no full concept note is worth
writing. Use it to avoid repeating what the user already knows and to revisit
weak prerequisites later.

## Active Feedback Loop

Do not wait only for the user to volunteer confusion. After a useful explanation
or concept capture, ask one small, optional probe to update the knowledge tree.

Default probe style:

- Mostly multiple-choice or true/false checks.
- Occasional short-answer questions when the concept is important or ambiguous.
- Make the probe explicitly optional; the user may skip because they are busy.
- If the user skips, continue normally and do not treat silence as evidence of
  understanding.
- If the user answers, update the knowledge tree with `assess`: promote mastery
  only when the answer demonstrates it; otherwise record the gap or
  misconception.

Good probe examples:

```text
Quick optional check: in `mysub.yaml`, is a node closer to:
A. one concrete server entry
B. a routing policy group
C. the whole mihomo process
You can skip this.
```

```text
True or false, optional: `fallback` chooses by priority order, while `url-test`
chooses by measured latency.
```

```text
Short answer, optional: why is hardcoding subscription node names brittle?
```

## What To Capture

Prefer concept-first notes. Capture these categories:

- Concepts: named ideas such as `Vue reactivity`, `dependency graph`,
  `esbuild`, `event delegation`, `schema validation`.
- Algorithmic ideas: reusable reasoning such as state lifting, incremental
  recomputation, topological ordering, cache invalidation, optimistic updates,
  diffing, debouncing, parsing, normalization, idempotency.
- Project maps: how components, modules, services, routes, build tools, and data
  flows relate inside the current project.
- Learner-model updates: prerequisite concepts, current mastery, gaps,
  misconceptions, probes, and evidence about the user's understanding.

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
- Ask 1-2 gentle, optional probes after important captures, mostly as
  multiple-choice or true/false questions.

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
      "confidence": 0.7,
      "prerequisites": ["module", "import statement"],
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
      "gaps": [
        "The user may not yet connect imports to graph edges."
      ],
      "probes": [
        "What changes if a file has no importers?"
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
