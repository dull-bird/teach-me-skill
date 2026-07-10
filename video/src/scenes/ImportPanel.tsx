import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { Sparkle, SoftBlobBackground } from "../components/Decor";

const SOURCES = [
  { emoji: "📕", label: "书 / PDF" },
  { emoji: "🌐", label: "网页 / URL" },
  { emoji: "🗂️", label: "Obsidian" },
  { emoji: "📄", label: "Markdown" },
  { emoji: "📚", label: "EPUB / Word" },
];

const SourceChip: React.FC<{ emoji: string; label: string; delay: number }> = ({ emoji, label, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 13, mass: 0.6 }, durationInFrames: 18 });
  return (
    <div
      style={{
        transform: `scale(${s})`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
        width: 170,
        padding: "20px 12px",
        borderRadius: 18,
        background: theme.card,
        border: `2px solid ${theme.line}`,
        boxShadow: "0 18px 40px rgba(30,25,15,0.10)",
      }}
    >
      <div style={{ fontSize: 40 }}>{emoji}</div>
      <div style={{ fontFamily: theme.sans, fontWeight: 700, fontSize: 17, color: theme.ink, textAlign: "center" }}>
        {label}
      </div>
    </div>
  );
};

export const ImportPanel: React.FC<{ text: string }> = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const arrowOpacity = interpolate(frame, [50, 66], [0, 1], { extrapolateRight: "clamp" });
  const vaultScale = spring({ frame: frame - 66, fps, config: { damping: 12 }, durationInFrames: 18 });

  return (
    <AbsoluteFill>
      <SoftBlobBackground />
      <Sparkle x={150} y={150} phase={0.3} />
      <Sparkle x={1740} y={860} phase={2.4} />

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", paddingBottom: 140 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 40 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {SOURCES.map((s, i) => (
              <SourceChip key={s.label} {...s} delay={i * 8} />
            ))}
          </div>

          <div
            style={{
              opacity: arrowOpacity,
              fontSize: 54,
              color: theme.accent,
              fontFamily: theme.sans,
            }}
          >
            →
          </div>

          <div
            style={{
              transform: `scale(${vaultScale})`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 14,
              width: 280,
              padding: "40px 24px",
              borderRadius: 22,
              background: theme.accentSoft,
              border: `2px solid color-mix(in srgb, ${theme.accent} 40%, ${theme.line})`,
            }}
          >
            <div style={{ fontSize: 60 }}>📓</div>
            <div style={{ fontFamily: theme.serif, fontSize: 26, color: theme.accentInk, textAlign: "center" }}>
              你的 Teach Me Vault
            </div>
            <div
              style={{
                marginTop: 6,
                fontFamily: theme.sans,
                fontSize: 16,
                color: theme.muted,
                textAlign: "center",
                lineHeight: 1.5,
              }}
            >
              先读一遍
              <br />
              再问熟不熟
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
