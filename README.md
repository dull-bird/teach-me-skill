# Teach Me

Teach Me is an Agent Skill for development learning. It helps Claude Code,
Codex, OpenClaw, and Kimi Code CLI turn meaningful coding work into durable
Obsidian notes, concept maps, and review prompts.

It is intentionally conservative: hooks inject compact learning context and log
lightweight tool events, while the agent decides at natural phase boundaries
whether there is knowledge worth capturing.

Teach Me also keeps a learner model. Before teaching a new domain, the agent
should sketch the prerequisite concept tree, probe obvious basics, and start at
the first weak or unknown node instead of jumping into mid-level details.
After teaching, it should ask a small optional feedback probe, usually
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

First configuration:

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure --language auto
```

The default vault path is `~/.teach_me_skill/vault`.

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

For cross-device use, connect the local vault to a Git remote:

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

Git sync is opt-in. Without `--git-remote`, you can still use
`--enable-git-sync` for local version history only.

## GitHub Pages

The project page is a static site under `docs/` and can be deployed directly by
the included GitHub Actions workflow.

## License

MIT
