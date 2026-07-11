# Teaching Profile Initialization and Hook Boundaries

## Goal

Make the learner's explicitly chosen teaching profile distinct from vault
initialization, and reduce Teach Me hooks to evidence collection and phase
boundary decisions. A normal working prompt must not be classified through
keywords.

## Decisions

### Teaching profile state

- Keep vault setup (`config.initialized`) separate from teaching-profile setup.
- Add `profile_initialized: false` to the default style profile. A missing flag
  in an existing vault is treated as `false`.
- Runtime fallback fields remain available so context can be rendered, but do
  not imply user consent.
- An explicit `configure --teacher-style ...` or a style-setting command
  persists the selected profile and sets `profile_initialized: true`.
- `context` and `status` report the teaching-profile state independently.

### When setup is requested

- Do not interrupt ordinary implementation merely because the profile is
  missing.
- If a Stop decision finds learning-worthy work while the profile is unset,
  block once and request one concise style choice before any capture.
- The response must not configure or write a learning note in that same turn;
  explicit user consent is required.

### Hook boundary

- Remove `UserPromptSubmit` from Codex, Claude Code, and Kimi hook installers,
  snippets, documentation, and the shared hook entrypoint.
- Keep `PreToolUse`, `PostToolUse`, `PostToolUseFailure` where supported, and
  `Stop`.
- Stop scoring depends on tool evidence only. It no longer consumes prompt
  intent, broad work-keyword matches, manual-score thresholds, or prompt-level
  opt-out state.
- Explicit "teach me", "why", and "review" requests are handled by the Teach
  Me skill itself, not a hook.

### Exam boundary

- Do not add an Exam hook and never start a quiz from Stop.
- Explicit "quiz me" / "考考我" requests are handled by Teach Me Exam, which
  first collects scope, question style, and time budget.
- Teach Me documents this handoff so a review and an exam remain separate,
  opt-in flows.

## Documentation

- Update the Chinese and English README explanations and hook-support tables.
- Update both public Pages (`docs/index.html` and `docs/en/index.html`) to
  explain: tool hooks observe actual work; Stop decides whether to review;
  skills handle explicit teaching and exam requests; exams are never automatic.
- Keep the public-page copy owner-adjacent, practical, and bilingual.

## Regression tests

1. Existing style profiles without `profile_initialized` report an unset
   teaching profile.
2. Explicit profile configuration persists the flag and profile fields.
3. A learning-worthy Stop decision with an unset profile requests setup and
   does not allow a capture path.
4. Hook installers and snippets register only tool and Stop events.
5. A `UserPromptSubmit` payload is ignored by the shared entrypoint.
6. A tool-backed Stop review still occurs without any prompt event.

## Non-goals

- No automatic exams.
- No prompt keyword classifier.
- No changes to vault note schema beyond style-profile state.
