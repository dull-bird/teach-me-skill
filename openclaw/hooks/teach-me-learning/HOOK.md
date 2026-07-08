---
name: teach-me-learning
description: "Inject Teach Me learning context for development tasks and explicit teaching requests."
homepage: https://github.com/local/teach-me-skill
metadata:
  {
    "openclaw":
      {
        "events": ["message:received", "agent:bootstrap"],
        "install": [{ "id": "bundled", "kind": "bundled", "label": "teach-me-skill" }],
      },
  }
---

# Teach Me Learning Hook

This OpenClaw internal hook pairs with the `teach-me` skill.

- `message:received`: detect development-like prompts and manual teaching triggers, then store a compact per-session flag.
- `agent:bootstrap`: inject Teach Me context into the agent bootstrap when the latest message is development-related or explicitly asks to learn.

Enable with:

```bash
openclaw hooks enable teach-me-learning
```

## Stop Hook Note

OpenClaw internal hooks do not provide the same natural turn-end `Stop` gate as
Codex, Claude Code, and Kimi Code CLI. OpenClaw's internal `command:stop` event
observes the user issuing `/stop`; it is cancellation lifecycle, not a hook that
fires when the agent is about to send its final answer.

To implement Teach Me's automatic turn-end review in OpenClaw, use an OpenClaw
plugin typed hook with `before_agent_finalize`. That plugin hook can inspect the
natural final answer and request one more model pass. This bundled internal hook
therefore stays limited to prompt-time context injection.
