# Obsidian Vault Format

Teach Me creates a standard Obsidian-compatible folder under
`~/.teach_me_skill/vault` by default. A different user may configure another
path, but state stays under the selected vault's `.teach-me/` directory.

## Directory Layout

```text
vault/
├── .obsidian/
│   ├── app.json
│   └── appearance.json
├── .teach-me/
│   ├── learning-state.json
│   ├── style-profile.json
│   ├── events.jsonl
│   └── sessions/
├── 00_Index.md
├── 01_Knowledge_Graph.md
├── 02_Concepts/
├── 03_Algorithmic_Ideas/
├── 04_Project_Maps/
├── 05_Socratic_Questions/
├── 06_Reviews/
└── 07_Learning_Profile/
    └── Knowledge_Tree.md
```

## Note Rules

- Use ordinary Markdown files.
- Use Obsidian wikilinks such as `[[dependency graph]]`.
- Keep one durable concept per note when possible.
- Append new learning events instead of deleting prior notes.
- Keep common technical names in English when they are the standard term.
- Store machine-readable state in `.teach-me/`, not in visible note folders.
- Keep `07_Learning_Profile/Knowledge_Tree.md` generated from runtime state; do
  not hand-edit it as the source of truth.

## Concept Note Shape

```md
---
type: teach-me/concept
mastery: seen
created: 2026-07-08
updated: 2026-07-08
---

# dependency graph

## One-Line Meaning

A dependency graph is a map of which files or modules rely on which others.

## First Principles

- Programs are split into smaller files.
- Import statements create relationships between files.
- Tools can follow those relationships to know what is affected by a change.

## In This Project

Vite uses this idea to serve modules and rebuild changed parts quickly.

## Relationships

- [[Vite]] uses this idea.
- [[incremental rebuild]] depends on it.

## Socratic Questions

- If one imported file changes, how could a tool avoid rebuilding everything?
```

## Knowledge Graph

`01_Knowledge_Graph.md` may contain both a readable edge list and a Mermaid
graph. The graph is generated from captured relationships and can be rewritten
by the runtime.

## Knowledge Tree

`07_Learning_Profile/Knowledge_Tree.md` is the human-readable learner model. It
tracks prerequisite concepts, observed mastery, confidence, gaps,
misconceptions, probe questions, and evidence. Use it to decide where to begin
the next explanation.
