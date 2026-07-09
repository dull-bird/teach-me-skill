# Teach Me Recap

A spaced-repetition review companion for Teach Me. It turns your captured concepts, algorithmic ideas, and project maps into active-recall prompts and schedules the next review based on how well you remember them.

## Review method

Recap uses three mechanisms together:

1. **Spaced repetition (SM-2-like)** — items become due on a schedule that expands when you remember them and contracts when you forget.
2. **Active recall** — you are shown the title and a hint, then asked to explain the concept in your own words before seeing the note.
3. **Socratic probes** — if a knowledge-tree node has `probes`, gaps, or prerequisites, Recap uses them to deepen the review.

## When to use

Trigger this skill when the user says anything like:

- “帮我复习一下”
- “Teach Me 复习”
- “今天该复习什么？”
- “考考我”
- “recap” / “review”
- “我最近学了什么？”
- “这个词我还记不记得？”

## How to use

Start a review session:

```bash
python3 ~/.codex/skills/recap/scripts/recap.py next
```

The script prints the next due item in a recall-friendly format. After the user answers, record the result:

```bash
python3 ~/.codex/skills/recap/scripts/recap.py rate "Concept Name" good
```

Quality levels:

- `again` / `0` — complete blank or wrong
- `hard` / `3` — struggled but recalled
- `good` / `4` — recalled with effort
- `easy` / `5` — recalled instantly

Continue with `next` until nothing is due. You can also run a non-interactive summary:

```bash
python3 ~/.codex/skills/recap/scripts/recap.py due     # list due items
python3 ~/.codex/skills/recap/scripts/recap.py stats   # review statistics
python3 ~/.codex/skills/recap/scripts/recap.py manual  # operation manual
```

## Presenting a review item

When running `next`, present only:

- The item title
- Its type (concept / algorithmic idea / project map)
- A short hint: the first paragraph of the note, or a Socratic probe, or a prerequisite question
- The instruction: “先尝试用自己的话解释，然后告诉我你记得多少。”

Do **not** reveal the full note until the user has attempted to recall.

## Recording a review

After the user responds, choose the closest quality and run `rate`. Update rules:

- `again` — schedule the item for tomorrow; ease drops.
- `hard` — small interval increase; ease drops slightly.
- `good` — normal SM-2 interval increase.
- `easy` — larger interval increase; ease rises.

Then move to the next item or report that the session is complete.

## Natural-language follow-ups

Offer these examples to the user:

- “再给我出一道”
- “这个我忘了，标为 again”
- “这个很简单，标为 easy”
- “今天先复习到这儿”
- “把复习间隔改成每天/每周提醒”
- “给我看看哪些概念最薄弱”

## Rules

- Only use the Python standard library.
- Only read and update `~/.teach_me_skill/vault/.teach-me/learning-state.json` and the vault notes.
- Never create fake review history.
- If nothing is due, say so warmly and suggest reviewing weak items anyway.
- Keep the tone light; a missed item is a signal, not a failure.
