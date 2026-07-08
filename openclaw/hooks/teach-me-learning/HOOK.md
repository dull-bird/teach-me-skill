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

This hook pairs with the `teach-me` skill.

- `message:received`: detect development-like prompts or manual teaching
  triggers and store a compact per-session flag.
- `agent:bootstrap`: inject Teach Me context into the agent bootstrap when the
  latest message is development-related or explicitly asks to learn.

Enable with:

```bash
openclaw hooks enable teach-me-learning
```
