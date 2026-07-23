# Teach Me English Promo Video Design

## Goal

Produce a standalone English version of the existing Teach Me promotional video
for an English-speaking audience, using a natural American product-introduction
voice while preserving the current visual language and narrative arc.

## Audience and Voice

- Audience: developers, students, and early-career knowledge workers who use
  coding agents and want to retain understanding rather than only ship output.
- Voice: first-person project-author voice; practical, calm, and specific.
- Localization rule: adapt meaning and cadence for spoken American English.
  Do not translate Chinese narration word-for-word.

## Deliverables

1. An English segment manifest with spoken narration, scene ids, pauses, and
   regenerated cue timings.
2. An English audio track assembled from generated segment audio.
3. An English Remotion composition whose captions and scene copy are English.
4. A rendered MP4 placed in `video/out/` without overwriting the Chinese render.

## Architecture

The Chinese promo remains the default `TeachMePromo` composition and continues
to use the existing narration manifest. The English version is an explicitly
named sibling composition (`TeachMePromoEnglish`) that receives English segment
metadata and renders English-only scene components/copy.

The narration build pipeline remains data-driven: a new English input segment
file feeds the existing manifest builder (extended with a locale/input-output
option if required). The generated English manifest becomes the single timing
source for English captions and audio sequencing.

## Localization Decisions

- Keep the existing scene order and visual concepts to preserve the proven
  narrative structure.
- Replace all audience-facing Chinese text: captions, UI labels, quiz answers,
  workflow labels, badges, and CTA copy.
- Preserve product names and commands such as `Teach Me`, `Teach Me Check`,
  `Git`, and `rebase`.
- Reword lines to fit the available visual beat; narration duration is derived
  from actual generated audio rather than assumed from the Chinese edit.
- Do not imply Git sync is on by default. English copy must state that it is
  optional.

## Audio and Timing

- Generate English narration with the repository's existing audio script after
  extending it for a U.S. English voice/locale as needed.
- Assemble audio with the existing manifest tooling.
- Calculate composition duration from the English manifest instead of reusing
  the Chinese frame count.
- If English audio changes the total duration, scene component timing continues
  to derive from segment ids and the manifest, so the visual sequence expands or
  contracts only at narration boundaries.

## Verification

- Run the focused manifest/build validation for the English input.
- Type-check or render Remotion's English composition.
- Render `TeachMePromoEnglish` to a separate MP4.
- Inspect a representative set of frames: opening hook, workflow/skill section,
  quiz/vault UI, and final CTA.
- Confirm the render contains no Chinese audience-facing copy and does not
  modify the Chinese manifest or default composition.

## Out of Scope

- Re-designing the visual identity or Chinese video.
- Publishing the rendered video externally.
- Adding subtitles as a separate `.srt` export unless the existing pipeline
  already produces one as part of the English asset flow.
