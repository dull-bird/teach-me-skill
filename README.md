# Teach Me

Teach Me is an Agent Skill for development learning. It helps Claude Code,
Codex, OpenClaw, and Kimi Code CLI turn meaningful coding work into durable
Obsidian notes, concept maps, and review prompts.

It is intentionally conservative: hooks inject compact learning context and log
lightweight tool events, while the agent decides at natural phase boundaries
whether there is knowledge worth capturing.

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

## GitHub Pages

The project page is a static site under `docs/` and can be deployed directly by
the included GitHub Actions workflow.

## License

MIT
