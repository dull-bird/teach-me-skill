# Hook Test Coverage Design

## Goal

Add regression coverage for the Teach Me hook's externally observable event
contract without changing production behavior. The tests must run the actual
hook script as a subprocess against a temporary `TEACH_ME_HOME`, so they cover
stdin parsing, stdout response shape, config loading, and event persistence.

## Scope

The work extends `tests/test_teach_me_hook.py` in four areas:

1. **Prompt events**: manual learning requests inject context, ordinary prompts
   remain silent, and an uninitialized runtime never authorizes implicit setup.
2. **Tool events**: pre- and post-tool payloads record evidence in
   `events.jsonl`, including edit, verification, build, and failure signals.
3. **Stop events**: weak evidence remains silent; strong evidence produces one
   correctly shaped review block for initialized and uninitialized runtimes;
   an already-active or already-blocked Stop event does not loop.
4. **Malformed optional data**: omitted optional identifiers and non-dictionary
   tool inputs/responses do not crash the hook or create malformed event rows.

## Test Design

Each test creates a new temporary home. Initialized cases use the existing
`write_initialized_config` helper; all other cases start from the runtime's
uninitialized default. The existing `run_hook`, `parse_stdout`, and
`read_events` helpers remain the only execution and assertion boundary.

Tests assert observable output and persisted records rather than private helper
calls. They check only stable portions of human-readable review text and exact
protocol fields where the hook contract requires them.

## Out of Scope

- No production hook changes.
- No installer, public-site, or video asset changes.
- No changes to the existing `video/public/narration.mp3` worktree edit.

## Verification

Run the focused module with:

```bash
python3 -m unittest -v tests.test_teach_me_hook
```

Then run the repository's complete Python test suite if the focused module is
green:

```bash
python3 -m unittest discover -v tests
```
