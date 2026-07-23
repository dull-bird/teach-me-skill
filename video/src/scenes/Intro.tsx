import React from "react";
import { AbsoluteFill, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Video } from "remotion";
import { theme } from "../theme";
import { Cloud, Flower, Sparkle, SoftBlobBackground } from "../components/Decor";

const AGENTS = ["Claude Code", "Codex", "Kimi Code CLI", "OpenClaw"];

const TAGLINE: Record<"zh" | "en", string> = {
  zh: "做事，顺便学明白",
  en: "Work, and actually learn.",
};

export const Intro: React.FC<{ locale?: "zh" | "en" }> = ({ locale = "zh" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame, fps, config: { damping: 12, mass: 0.6 }, durationInFrames: 24 });
  const logoRotate = interpolate(frame, [0, 24], [-14, 0], { extrapolateRight: "clamp" });

  const titleOpacity = interpolate(frame, [12, 30], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [12, 30], [18, 0], { extrapolateRight: "clamp" });

  const tagOpacity = interpolate(frame, [26, 44], [0, 1], { extrapolateRight: "clamp" });
  const tagY = interpolate(frame, [26, 44], [14, 0], { extrapolateRight: "clamp" });

  const chipsOpacity = interpolate(frame, [52, 70], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      <SoftBlobBackground />
      <Cloud x={110} y={90} scale={1.1} phase={0} />
      <Cloud x={1600} y={140} scale={0.9} phase={2} />
      <Flower x={220} y={820} scale={1.2} phase={1} color="#e79a9a" />
      <Flower x={1660} y={760} scale={1} phase={3} color="#f2b880" />
      <Sparkle x={520} y={260} phase={0.5} />
      <Sparkle x={1400} y={300} phase={2.2} />
      <Sparkle x={860} y={840} phase={4} />

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ transform: `scale(${logoScale}) rotate(${logoRotate}deg)`, marginBottom: 18 }}>
          <Video src={staticFile("seedling.webm")} style={{ width: 150, height: 150 }} />
        </div>

        <div
          style={{
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
            fontFamily: theme.serif,
            fontSize: 118,
            color: theme.ink,
            fontWeight: 400,
          }}
        >
          Teach&nbsp;Me
        </div>

        <div
          style={{
            opacity: tagOpacity,
            transform: `translateY(${tagY}px)`,
            marginTop: 22,
            fontFamily: theme.sans,
            fontSize: 42,
            fontWeight: 650,
            color: theme.accentInk,
            letterSpacing: 2,
          }}
        >
          {TAGLINE[locale]}
        </div>

        <div style={{ opacity: chipsOpacity, marginTop: 34, display: "flex", gap: 12 }}>
          {AGENTS.map((a) => (
            <span
              key={a}
              style={{
                padding: "9px 20px",
                borderRadius: 999,
                border: `2px solid ${theme.line}`,
                background: theme.card,
                color: theme.muted,
                fontFamily: theme.sans,
                fontWeight: 650,
                fontSize: 20,
              }}
            >
              {a}
            </span>
          ))}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
