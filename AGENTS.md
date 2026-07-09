# Teach Me Project Instructions

## Public Page Voice

When editing `docs/index.html` or `docs/en/index.html`, write as the project
author introducing my own tool. Do not write in an AI assistant voice.

Use this tone:

- First-person or owner-adjacent when useful: "我希望它...", "我需要的是..."
- Concrete benefits over hype.
- Plain Chinese first. Keep English only where it is a real technical term or
  command.
- Sell the practical points: local-first Markdown vault, prerequisite scanning,
  dynamic knowledge tree, optional feedback probes, optional Git sync.
- Keep the public site bilingual: `docs/index.html` is Chinese,
  `docs/en/index.html` is English. Each page should use the flow diagram in its
  own language.

Avoid:

- Generic AI marketing language such as "empower", "智能化赋能", "revolutionary",
  "seamless AI experience".
- Overexplaining implementation internals above the fold.
- Claiming the tool teaches perfectly. It should be described as a practical
  learning companion that improves through feedback.

## Product Principles

- Teach Me should not interrupt implementation.
- Before teaching a new domain, it should scan prerequisite concepts and probe
  the user's baseline.
- Feedback probes should be optional. Prefer multiple-choice and true/false;
  use short-answer occasionally.
- Git sync is opt-in. Never imply a vault is pushed remotely by default.
- Public copy must match the current implementation: Prompt hooks inject
  context, tool hooks collect evidence, Stop hooks score the phase boundary, and
  the runtime writes the vault.
