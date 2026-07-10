import React from "react";
import { AbsoluteFill, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Video } from "remotion";
import { theme } from "../theme";
import { Cloud, Flower, SoftBlobBackground, Sparkle } from "../components/Decor";

export const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const logoScale = spring({ frame, fps, config: { damping: 12, mass: 0.6 }, durationInFrames: 20 });
  const textOpacity = interpolate(frame, [10, 26], [0, 1], { extrapolateRight: "clamp" });
  const ctaOpacity = interpolate(frame, [30, 46], [0, 1], { extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [durationInFrames - 20, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      <SoftBlobBackground />
      <Cloud x={140} y={120} scale={0.9} phase={1} />
      <Cloud x={1580} y={780} scale={1.1} phase={3} />
      <Flower x={1700} y={160} scale={1} phase={0.6} color="#e79a9a" />
      <Sparkle x={300} y={780} phase={2.4} />

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ transform: `scale(${logoScale})`, display: "flex", alignItems: "center", gap: 22 }}>
          <Video src={staticFile("seedling.webm")} style={{ width: 88, height: 88 }} />
          <div style={{ fontFamily: theme.serif, fontSize: 72, color: theme.ink }}>Teach Me</div>
        </div>

        <div
          style={{
            opacity: textOpacity,
            marginTop: 24,
            fontFamily: theme.sans,
            fontSize: 32,
            fontWeight: 650,
            color: theme.accentInk,
          }}
        >
          做事，顺便学明白
        </div>

        <div
          style={{
            opacity: ctaOpacity,
            marginTop: 42,
            fontFamily: theme.sans,
            fontSize: 26,
            color: theme.muted,
            letterSpacing: 0.5,
          }}
        >
          github.com/dull-bird/teach-me-skill
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
