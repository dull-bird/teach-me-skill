# Teach Me Runtime Schemas

The runtime accepts JSON on stdin for `capture` and stores JSON state in the
vault's `.teach-me/` directory.

## Config

`~/.teach_me_skill/config.json` may include optional Git sync settings:

```json
{
  "version": 2,
  "current_user": "default",
  "users": {
    "default": {
      "name": "Default User",
      "github": null,
      "vault_path": "~/.teach_me_skill/vault",
      "language": "auto",
      "max_notes_per_phase": 3,
      "linked_vaults": [
        {
          "path": "/path/to/obsidian/vault",
          "project": "My Obsidian",
          "linked_at": "2026-07-09T10:00:00"
        }
      ],
      "git_sync": {
        "enabled": true,
        "remote": "git@github.com:user/teach-me-vault.git",
        "branch": "main",
        "auto_sync": true
      },
      "initialized": true
    }
  }
}
```

Git sync is opt-in. If `auto_sync` is true, the runtime attempts to commit,
pull --rebase, and push after `assess`, `capture`, and `style`.

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
      "confidence": 0.7,
      "prerequisites": ["module", "import statement"],
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
      "gaps": ["The user may not yet connect import statements to graph edges."],
      "probes": ["What would happen if a changed file had no importers?"],
      "misconceptions": ["A dependency graph is not limited to package dependencies."],
      "evidence": [
        {"type": "observation", "summary": "The user asked why only one changed file can trigger a rebuild."}
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

`importance` (0-10) should reflect the value-rubric's Concept importance dimension
scaled up (0/1/2 → roughly 0-2/3-6/7-10): how foundational or field-defining the
idea is on its own merit, not how much tool activity produced it. A concept read
from a book with zero file edits can still score high here.

## Item Types

- `concept`: goes to `02_Concepts/`
- `algorithmic_idea`: goes to `03_Algorithmic_Ideas/`
- `project_map`: goes to `04_Project_Maps/`

Unknown types are treated as `concept`.

## Assessment Payload

Use `assess` when you learned something about the user's level but do not need
to write a full note yet. It updates `.teach-me/learning-state.json` and the
generated `07_Learning_Profile/Knowledge_Tree.md`.

```json
{
  "project": {
    "name": "teach-me-skill",
    "path": "/absolute/path/to/project"
  },
  "domain": "mihomo proxy routing",
  "summary": "The user asked basic questions after a fallback explanation, so the proxy stack needs a foundation sweep.",
  "nodes": [
    {
      "title": "mihomo",
      "type": "concept",
      "mastery": "seen",
      "confidence": 0.4,
      "prerequisites": ["proxy"],
      "gaps": ["May not have a crisp model of a local proxy daemon."],
      "probes": ["What does mihomo do between your browser and the remote server?"],
      "evidence": [
        {"type": "question", "summary": "Asked what mysub.yaml contains."}
      ],
      "needs_probe": true
    },
    {
      "title": "proxy node",
      "mastery": "unknown",
      "confidence": 0.25,
      "prerequisites": ["proxy server"],
      "probes": ["Which fields does a node need to connect to a server?"]
    }
  ],
  "questions": [
    "Can the user distinguish a proxy node from a proxy group?"
  ]
}
```

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
  "knowledge_tree": {
    "proxy node": {
      "type": "concept",
      "mastery": "unknown",
      "score": 0,
      "confidence": 0.25,
      "prerequisites": ["proxy server"],
      "children": ["proxy group"],
      "gaps": ["The user has not yet defined what a node is."],
      "probes": ["Which fields does a node need to connect to a server?"],
      "misconceptions": [],
      "evidence": [
        {
          "type": "question",
          "summary": "Asked what mysub.yaml contains.",
          "timestamp": "2026-07-08T20:10:00+08:00"
        }
      ],
      "projects": ["mihomo"],
      "last_assessed": "2026-07-08T20:10:00+08:00",
      "needs_probe": true
    }
  },
  "graph_edges": [
    {"source": "dependency graph", "relation": "enables", "target": "incremental rebuild"}
  ],
  "assessments": [],
  "imports": [
    {
      "import_id": "import-20260709-100000",
      "timestamp": "2026-07-09T10:00:00",
      "source_type": "pdf",
      "detected_type": "pdf",
      "path": "/path/to/file.pdf",
      "project": "Book Name",
      "phase": "external import",
      "pages": "1-10",
      "status": "ok",
      "extracted_length": 15420,
      "extracted_items": ["event sourcing", "CQRS"]
    },
    {
      "import_id": "import-20260709-110000",
      "timestamp": "2026-07-09T11:00:00",
      "source_type": "obsidian",
      "detected_type": "obsidian",
      "path": "/path/to/obsidian/vault",
      "project": "My Obsidian",
      "phase": "external import",
      "status": "ok",
      "extracted_length": 45200,
      "note_count": 12,
      "skipped_count": 4,
      "note_paths": ["Projects/web-ui.md", "Readings/event-sourcing.md"],
      "skipped_paths": [".obsidian/workspace.json", ".teach-me/learning-state.json"],
      "extracted_items": ["event sourcing", "CQRS"]
    }
  ]
}
```

Import `status` values:

- `ok` — text was extracted successfully.
- `fallback_encoding` — text was extracted using a fallback encoding.
- `no_extractor` — the source needs a parser that is not installed (e.g., PDF without `pymupdf`/`pypdf`).
- `unreadable` — the source could not be read at all.
- `self_import` — the Obsidian vault path is inside the current Teach Me vault.
- `no_content` — the Obsidian vault contained no importable Markdown after filtering.

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
  "probe_format": "mostly_choice",
  "probe_required": false,
  "last_feedback_at": null
}
```

Probe format values:

- `mostly_choice`: prefer multiple-choice and true/false probes.
- `mixed`: use choice, true/false, and short-answer probes evenly.
- `mostly_short`: ask more short-answer probes for advanced users.
