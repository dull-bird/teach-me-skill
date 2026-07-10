# Seedling Single Playback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recommended) superpowers:executing-plans implement plan task-by-task.

**Goal:** Make the seedling animation play once wherever it appears in the promo video.

**Architecture:** Reuse the existing `seedling.webm` asset in both scenes, but rely on Remotion's default non-looping `Video` behavior rather than setting `loop`. After its 1.98-second animation completes, each scene keeps the final frame visible for the rest of its duration.

**Tech Stack:** React, Remotion, TypeScript.

## Global Constraints

- Change only the two seedling video instances.
- Preserve their size, positioning, scene timing, and existing entrance animations.
- Verify both locations after the source media has passed its 1.98-second duration.

### Task 1: Disable looping on both seedling instances

**Files:**
- Modify: `video/src/scenes/Intro.tsx:36`
- Modify: `video/src/scenes/Outro.tsx:28`

- [ ] Remove the `loop` prop from each `Video` instance.
- [ ] Run TypeScript validation.
- [ ] Render a later frame from each scene and verify the seedling is no longer restarting.
