# Teach Me Runtime Schemas

The runtime accepts JSON on stdin for `capture` and stores JSON state in the
vault's `.teach-me/` directory.

## Capture Payload

```json
{
  "project": {
    "name": "teach-me-skill",
    "path": "/absolute/path/to/project"
  },
  "phase": "Implemented hook installation",
  "language": "auto",
  "summary": "The useful idea is separating deterministic hook logic from AI judgment.",
  "allow_many": false,
  "items": [
    {
      "type": "concept",
      "title": "dependency graph",
      "aliases": ["module graph"],
      "importance": 8,
      "mastery": "seen",
      "why_it_matters": "It explains fast rebuilds in modern frontend tools.",
      "one_line": "A graph of which modules depend on which other modules.",
      "first_principles": [
        "A large program is split into files.",
        "Imports create directed relationships.",
        "Following those relationships reveals the affected surface of a change."
      ],
      "current_project_context": "Vite can update only affected modules during development.",
      "relationships": [
        {"target": "Vite", "relation": "uses"},
        {"target": "incremental rebuild", "relation": "enables"}
      ],
      "socratic_questions": [
        "What would be slower if the tool did not remember import relationships?"
      ],
      "review_prompt": "Explain why a dependency graph helps hot reload.",
      "next_review_days": 2,
      "body": "Optional extra Markdown."
    }
  ]
}
```

## Item Types

- `concept`: goes to `02_Concepts/`
- `algorithmic_idea`: goes to `03_Algorithmic_Ideas/`
- `project_map`: goes to `04_Project_Maps/`

Unknown types are treated as `concept`.

## Learning State

```json
{
  "version": 1,
  "concepts": {
    "dependency graph": {
      "type": "concept",
      "mastery": "seen",
      "score": 1,
      "last_seen": "2026-07-08T20:10:00+08:00",
      "next_review": "2026-07-10",
      "review_interval_days": 2,
      "ease": 2.5,
      "projects": ["teach-me-skill"],
      "note": "02_Concepts/dependency-graph.md"
    }
  },
  "graph_edges": [
    {"source": "dependency graph", "relation": "enables", "target": "incremental rebuild"}
  ]
}
```

## Style Profile

```json
{
  "version": 1,
  "language": "auto",
  "analogy_level": "medium",
  "socratic_level": "gentle",
  "code_example_level": "high",
  "first_principles_level": "high",
  "verbosity": "compact",
  "last_feedback_at": null
}
```
