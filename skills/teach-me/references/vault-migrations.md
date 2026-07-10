# Teach Me Vault Schema Migrations

Teach Me keeps a machine-readable schema version inside each vault so that older
vaults can be aligned when the runtime changes the shape of its state, generated
system notes, folder layout, or note frontmatter.

## Where the version lives

The canonical version is stored in `.teach-me/learning-state.json`:

```json
{
  "version": 1,
  "vault_schema_version": 1,
  "concepts": {},
  "knowledge_tree": {},
  "graph_edges": [],
  "captures": [],
  "assessments": [],
  "imports": []
}
```

- `version` is the legacy field and is kept for backwards compatibility.
- `vault_schema_version` is the authoritative schema version for the whole
  vault: state files, generated system notes, folder layout, and note
  frontmatter conventions.

The runtime also exposes the target version through the constant
`VAULT_SCHEMA_VERSION` in `scripts/teach_me.py`.

## When to bump the schema version

Bump `VAULT_SCHEMA_VERSION` whenever a release makes a **backwards-incompatible**
change to any of the following:

- The shape of `learning-state.json` (renamed/removed keys, new required keys).
- The shape of `style-profile.json`.
- Generated system notes (`00_Index.md`, `01_Knowledge_Graph.md`,
  `07_Learning_Profile/Knowledge_Tree.md`).
- The folder layout for concept/idea/project notes.
- Teach Me note frontmatter keys or values.

Purely additive changes that old runtimes can ignore do **not** require a bump.

## Migration policy

1. **Deterministic migrations live in code.** If a transformation can be done
   safely without AI judgment, add it to `VAULT_MIGRATIONS` in
   `scripts/teach_me.py`.
2. **Judgment-required migrations use the AI adapter.** If a change is too
   complex or risky to automate (e.g., merging two note formats, re-interpreting
   old frontmatter, splitting one concept into two), the runtime raises
   `UnsupportedVaultSchemaError` and the AI follows the adapter prompt below.
3. **Never silently rewrite user notes.** Always back up, ask when uncertain, and
   preserve every concept, mastery score, review date, relationship, and import
   record.

## Version history

| Version | Date | Summary |
| --- | --- | --- |
| 1 | Baseline | Multi-user config, `learning-state.json` with concepts/knowledge_tree/graph_edges/captures/assessments/imports, generated system notes `00_Index.md` / `01_Knowledge_Graph.md` / `07_Learning_Profile/Knowledge_Tree.md`, note frontmatter `type: teach-me/{concept\|algorithmic_idea\|project_map}` with `mastery`, `created`, `updated`, `aliases`. |

## How to migrate

First try the runtime:

```bash
python3 <teach-me-skill-dir>/scripts/teach_me.py migrate
```

Use `--dry-run` to preview:

```bash
python3 <teach-me-skill-dir>/scripts/teach_me.py migrate --dry-run
```

Check the current version:

```bash
python3 <teach-me-skill-dir>/scripts/teach_me.py vault-version
```

If the runtime returns exit code `3` and prints `UnsupportedVaultSchemaError`,
use the AI adapter prompt below.

---

## AI adapter prompt: align an old vault to a new schema

Use this prompt when the runtime reports an unsupported vault schema version and
you need to rewrite the vault manually.

```text
You are aligning a Teach Me vault from schema version {old_version} to {new_version}.

Read these files in order:
1. `references/vault-migrations.md` — version history and breaking changes.
2. `.teach-me/learning-state.json` — the machine state.
3. `00_Index.md`, `01_Knowledge_Graph.md`, `07_Learning_Profile/Knowledge_Tree.md`.
4. Every note in `02_Concepts/`, `03_Algorithmic_Ideas/`, `04_Project_Maps/`,
   `05_Socratic_Questions/`, and `06_Reviews/`.

Rules:
- Preserve every concept title, mastery level, review schedule (`next_review`,
  `review_interval_days`, `ease`), project association, and relationship.
- Do not drop import records, captures, assessments, events, or style settings.
- Convert old frontmatter keys to the new keys exactly as documented in
  `references/vault-migrations.md`.
- Keep note file paths stable. If the folder layout changed, move files and
  update `learning-state.json` `note` references accordingly, using the same
  `slugify` rules the runtime uses.
- Rewrite `00_Index.md`, `01_Knowledge_Graph.md`, and
  `07_Learning_Profile/Knowledge_Tree.md` from the updated state so they match
  the new generated-note format.
- Update `.teach-me/learning-state.json`:
  - set `vault_schema_version` to {new_version}
  - keep `version` as-is for backwards compatibility
- After rewriting, run `teach_me.py vault-version` to confirm the vault now
  reports the target version.
- If you cannot safely transform something (missing required field, ambiguous
  merge, possible data loss), stop and ask the user before overwriting.

Output a short report:
- old version → new version
- how many notes were rewritten or moved
- any fields/notes that required judgment or that you skipped
```

Replace `{old_version}` and `{new_version}` with the actual numbers before
running the prompt.
