import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { Sparkle, SoftBlobBackground } from "../components/Decor";
import { CaptionBar } from "../components/CaptionBar";

/**
 * Shows the four-skill workflow diagram, Ken-Burns panned toward a
 * different region depending on `focus` so two consecutive narration
 * beats (steps 3-4, then the four skills) don't look like a static slide.
 */
export const WorkflowPanel: React.FC<{ text: string; focus: "steps" | "skills" }> = ({ text, focus }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const cardScale = spring({ frame, fps, config: { damping: 14, mass: 0.7 }, durationInFrames: 26 });

  const panScale = interpolate(frame, [0, durationInFrames], [1, 1.14], { extrapolateRight: "clamp" });
  const panTarget = focus === "steps" ? { x: -90, y: -10 } : { x: 60, y: 30 };
  const panX = interpolate(frame, [0, durationInFrames], [0, panTarget.x], { extrapolateRight: "clamp" });
  const panY = interpolate(frame, [0, durationInFrames], [0, panTarget.y], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      <SoftBlobBackground />
      <Sparkle x={140} y={140} phase={0.8} />
      <Sparkle x={1750} y={900} phase={2.6} />

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", paddingBottom: 190 }}>
        <div
          style={{
            transform: `scale(${cardScale})`,
            background: theme.card,
            border: `2px solid ${theme.line}`,
            borderRadius: 24,
            padding: 20,
            overflow: "hidden",
            width: 1100,
            height: 610,
          }}
        >
          <div
            style={{
              width: "100%",
              height: "100%",
              overflow: "hidden",
              borderRadius: 12,
              transform: `scale(${panScale}) translate(${panX}px, ${panY}px)`,
            }}
          >
            <Img src={staticFile("workflow.png")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          </div>
        </div>
      </AbsoluteFill>

      <CaptionBar text={text} />
    </AbsoluteFill>
  );
};
