# Teach Me

Teach Me is an Agent Skill for development learning. It helps Claude Code,
Codex, OpenClaw, and Kimi Code CLI turn meaningful coding work into durable
Obsidian notes, concept maps, and review prompts.

Teach Me is intentionally conservative. Prompt hooks inject compact learning
context for obvious learning tasks. Tool hooks observe what the agent actually
did. Stop hooks can ask the agent for one short review pass at a natural phase
boundary, even when the user's original prompt did not contain development
keywords.

Teach Me also keeps a learner model. Before teaching a new domain, the agent
should sketch prerequisite concepts, probe obvious basics, and start from the
first weak or unknown node instead of jumping into mid-level details. After
teaching, it should ask a small optional feedback probe, usually
multiple-choice or true/false, so the knowledge tree can adapt without blocking
the user.

## Install

```bash
git clone https://github.com/dull-bird/teach-me-skill.git
cd teach-me-skill
./install.sh
```

Optional hooks:

```bash
./claude-code/install-hook.sh
./codex/install-hook.sh
./openclaw/install-hook.sh
./kimi/install-hook.sh
```

Codex, Claude Code, and Kimi Code CLI hooks install:

- `UserPromptSubmit`: inject compact learning context for explicit learning or development prompts.
- `PreToolUse`: observe planned tool operations.
- `PostToolUse`: observe successful tool results.
- `Stop`: at turn end, score the observed work and request one Teach Me review pass only when it looks useful.

The Codex installer also adds `~/.teach_me_skill` to
`[sandbox_workspace_write].writable_roots` once, so later learner-model and vault
updates do not repeatedly ask for workspace-outside write approval. Codex may
still ask for hook trust once after the hook command changes.

OpenClaw's bundled `HOOK.md` integration covers `message:received` and
`agent:bootstrap`. OpenClaw's internal `command:stop` is user cancellation, not
natural agent finalization; a true "before final answer" review requires an
OpenClaw plugin using `before_agent_finalize`.

## First Configuration

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure --language auto
```

The default vault path is `~/.teach_me_skill/vault`.

Before writing the first learning note, Teach Me asks the user to confirm:

- vault path
- note language
- whether Git sync should be enabled

Git sync is off by default unless the user provides a remote repository.

## Learner Model

Use `assess` to update the knowledge tree without writing a full note:

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py assess < assessment.json
```

The generated profile lives at:

```text
~/.teach_me_skill/vault/07_Learning_Profile/Knowledge_Tree.md
```

## Optional Git Sync

For cross-device use, connect a local vault Git remote:

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure \
  --language auto \
  --git-remote git@github.com:user/teach-me-vault.git \
  --auto-sync
```

Manual sync:

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py sync
```

Without `--git-remote`, you can still use `--enable-git-sync` for local version
history only.

## Tests

```bash
python3 -m unittest -v tests.test_teach_me_hook
```

## GitHub Pages

The project page static site lives under `docs/` and can be deployed directly by
the included GitHub Actions workflow.

## License

MIT
