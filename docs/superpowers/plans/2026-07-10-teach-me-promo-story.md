# Teach Me Promo Story Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recommended) superpowers:executing-plans implement plan task-by-task.

**Goal:** Turn the Teach Me promo into a complete AI-era learning story with deliberate narration pauses and uncropped full-screen key images.

**Architecture:** Treat every narrated thought as a separate audio segment, so the narration builder can add an intentional silence after each semantic beat and emit matching subtitle entries. Keep the Remotion scene sequence driven by the generated manifest; update the two image scenes to use `objectFit: "contain"` without overlay UI.

**Tech Stack:** TypeScript, React, Remotion, Node.js, FFmpeg, Aliyun TTS.

## Global Constraints

- Preserve English pronunciation tokens `Teach Me`, `Git`, and `GitHub` in the TTS input.
- Keep the product claims aligned with the implemented hooks, vault, review, assessment, and opt-in Git sync.
- Show `story.jpg` and `workflow.png` completely, without cropping or text overlays.

### Task 1: Rewrite narration into semantic beats

**Files:**
- Modify: `video/narration/segments.json`
- Modify: `video/narration/build_manifest.mjs`

- [ ] Replace feature-list narration with the causal story: AI execution, black-box dependence, human judgment, Teach Me's response, and concrete product flow.
- [ ] Split each narrated thought into an independent TTS segment and configure a per-segment pause.
- [ ] Emit subtitle cues from the same segment data so caption timing matches audio timing.

### Task 2: Present key images without cropping

**Files:**
- Modify: `video/src/scenes/StoryPanel.tsx`
- Modify: `video/src/scenes/WorkflowPanel.tsx`

- [ ] Render each key image full-screen with `objectFit: "contain"`.
- [ ] Remove gradients, labels, cards, and other overlays that conceal image content.

### Task 3: Generate and validate the completed video

**Files:**
- Generate: `video/public/narration.mp3`
- Generate: `video/src/data/manifest.json`
- Generate: `video/out/subtitles.srt`
- Generate: `video/out/teach-me-promo.mp4`

- [ ] Regenerate all TTS clips and the manifest.
- [ ] Run TypeScript validation and render the composition.
- [ ] Inspect still frames during both key-image scenes and verify the subtitle timing data.
