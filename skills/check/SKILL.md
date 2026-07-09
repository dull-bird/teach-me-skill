# Teach Me Check

A lightweight diagnostic companion for the Teach Me skill. It reads the local Teach Me configuration and vault, tells the user what is installed, where the vault lives, what is inside, and what can be done next — all in natural language.

## When to use

Trigger this skill when the user says anything like:

- “Teach Me 装好了吗？”
- “检查 Teach Me 配置”
- “我的 vault 在哪？”
- “Teach Me 状态怎么样？”
- “teach me check” / “check teach me”
- “Teach Me 有没有记录？”
- “怎么改 vault 路径？”
- “怎么开启 Git sync？”

## How to use

Run the diagnostic script:

```bash
python3 ~/.codex/skills/check/scripts/check_me.py report
```

The script prints a natural-language report. Pass `--json` if you need structured data:

```bash
python3 ~/.codex/skills/check/scripts/check_me.py report --json
```

Present the report to the user in a friendly, concise way. Do not dump raw JSON unless the user explicitly asks for it.

## What to report

Always cover these items:

1. **Installation status** — which agent hooks are registered (Claude Code, Codex, Kimi, OpenClaw).
2. **Configuration** — vault path, note language, max notes per phase.
3. **Vault contents** — counts of concepts, algorithmic ideas, project maps, Socratic questions, reviews, and the knowledge-tree size.
4. **Recent activity** — how many events (prompts, tool calls, captures, assessments) were recorded recently.
5. **Git sync** — whether it is enabled, the remote/branch, and whether auto-sync is on.
6. **Next actions** — one or two concrete suggestions the user can ask for in natural language.

## Natural-language follow-ups

After the report, explicitly tell the user they can speak naturally to change things. Examples to offer:

- “把 Teach Me vault 改到 `~/Documents/Teach-Me`”
- “把笔记语言改成英文/中文/自动”
- “开启 Git sync 到 `github.com/user/repo.git`”
- “关闭自动同步”
- “给我看看最近的学习记录”
- “帮我整理一下知识图谱”

These requests should be handled by running the existing `teach_me.py` commands, not by editing config files directly.

## Rules

- Do not install extra dependencies. The script only uses the Python standard library.
- Do not create a new vault or overwrite configuration unless the user explicitly asks.
- If Teach Me is not installed, explain that and offer to run the installer.
- Keep the report under a few short paragraphs; offer to expand any section if the user wants details.
