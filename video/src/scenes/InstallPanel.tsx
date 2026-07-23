import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { Sparkle, SoftBlobBackground } from "../components/Decor";

const LINES = [
  "git clone https://github.com/dull-bird/teach-me-skill.git",
  "cd teach-me-skill",
  "./install.sh",
  "./claude-code/install-hook.sh",
];

export const InstallPanel: React.FC<{ text: string; locale?: "zh" | "en" }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cardScale = spring({ frame, fps, config: { damping: 14, mass: 0.7 }, durationInFrames: 26 });

  return (
    <AbsoluteFill>
      <SoftBlobBackground />
      <Sparkle x={160} y={160} phase={0.7} />
      <Sparkle x={1720} y={860} phase={2.2} />

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", paddingBottom: 170 }}>
        <div
          style={{
            transform: `scale(${cardScale})`,
            width: 1040,
            background: theme.card,
            border: `2px solid ${theme.line}`,
            borderRadius: 18,
            overflow: "hidden",
            boxShadow: "0 30px 70px rgba(30,25,15,0.14)",
          }}
        >
          <div
            style={{
              display: "flex",
              gap: 9,
              padding: "16px 20px",
              background: theme.paper2,
              borderBottom: `1px solid ${theme.line}`,
            }}
          >
            <span style={{ width: 14, height: 14, borderRadius: "50%", background: theme.coral }} />
            <span style={{ width: 14, height: 14, borderRadius: "50%", background: "#c8a24a" }} />
            <span style={{ width: 14, height: 14, borderRadius: "50%", background: theme.accent }} />
          </div>
          <div style={{ padding: "30px 32px" }}>
            {LINES.map((line, i) => {
              const charCount = Math.round(
                interpolate(frame, [i * 22 + 6, i * 22 + 6 + line.length * 1.1], [0, line.length], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                })
              );
              const visible = line.slice(0, charCount);
              return (
                <div
                  key={i}
                  style={{
                    fontFamily: theme.mono,
                    fontSize: 24,
                    lineHeight: 1.9,
                    color: theme.body,
                    whiteSpace: "pre",
                  }}
                >
                  <span style={{ color: theme.accentInk }}>$ </span>
                  {visible}
                </div>
              );
            })}
          </div>
        </div>
      </AbsoluteFill>

    </AbsoluteFill>
  );
};
