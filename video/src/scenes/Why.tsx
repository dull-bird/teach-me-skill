import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { theme } from "../theme";
import { Sparkle, SoftBlobBackground } from "../components/Decor";

const FadeIcon: React.FC<{ x: number; y: number; emoji: string; phase: number }> = ({ x, y, emoji, phase }) => {
  const frame = useCurrentFrame();
  const t = (Math.sin(frame * 0.05 + phase) + 1) / 2;
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y + t * 10,
        fontSize: 46,
        opacity: 0.35 + t * 0.25,
      }}
    >
      {emoji}
    </div>
  );
};

export const Why: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const badgeOpacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const textOpacity = interpolate(frame, [10, 26], [0, 1], { extrapolateRight: "clamp" });
  const textY = interpolate(frame, [10, 26], [16, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      <SoftBlobBackground />
      <FadeIcon x={200} y={200} emoji="❓" phase={0} />
      <FadeIcon x={1650} y={220} emoji="⏳" phase={1.5} />
      <FadeIcon x={220} y={820} emoji="💭" phase={3} />
      <FadeIcon x={1680} y={800} emoji="❓" phase={2.2} />
      <Sparkle x={960} y={140} phase={1.8} />

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", padding: "0 260px" }}>
        <div
          style={{
            opacity: badgeOpacity,
            marginBottom: 26,
            display: "inline-flex",
            padding: "8px 22px",
            borderRadius: 999,
            border: `2px solid ${theme.line}`,
            background: theme.accentSoft,
            color: theme.accentInk,
            fontFamily: theme.sans,
            fontWeight: 700,
            fontSize: 26,
            letterSpacing: 2,
          }}
        >
          WHY
        </div>
        <div
          style={{
            opacity: textOpacity,
            transform: `translateY(${textY}px)`,
            fontFamily: theme.sans,
            fontWeight: 650,
            fontSize: 44,
            lineHeight: 1.65,
            color: theme.ink,
            textAlign: "center",
          }}
        >
          {text}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
