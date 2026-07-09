import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { Sparkle, SoftBlobBackground } from "../components/Decor";
import { CaptionBar } from "../components/CaptionBar";

const TREE = [
  "vault/",
  "├── 00_Index.md",
  "├── 01_Knowledge_Graph.md",
  "├── 02_Concepts/",
  "├── 03_Algorithmic_Ideas/",
  "├── 04_Project_Maps/",
  "├── 06_Reviews/",
  "├── 07_Learning_Profile/",
  "│   └── Knowledge_Tree.md",
  "└── .teach-me/",
  "    ├── learning-state.json",
  "    └── events.jsonl",
];

export const VaultPanel: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cardScale = spring({ frame, fps, config: { damping: 14, mass: 0.7 }, durationInFrames: 26 });
  const badgeOpacity = interpolate(frame, [20, 36], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      <SoftBlobBackground />
      <Sparkle x={160} y={160} phase={0.6} />
      <Sparkle x={1730} y={860} phase={2.5} />

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", paddingBottom: 170 }}>
        <div style={{ transform: `scale(${cardScale})`, display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div
            style={{
              width: 620,
              background: theme.card,
              border: `2px solid ${theme.line}`,
              borderRadius: 18,
              overflow: "hidden",
              boxShadow: "0 30px 70px rgba(30,25,15,0.14)",
            }}
          >
            <div
              style={{
                padding: "14px 22px",
                background: theme.paper2,
                borderBottom: `1px solid ${theme.line}`,
                fontFamily: theme.mono,
                fontSize: 16,
                color: theme.muted,
              }}
            >
              ~/.teach_me_skill/vault
            </div>
            <pre
              style={{
                margin: 0,
                padding: "24px 26px",
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
                fontSize: 19,
                lineHeight: 1.7,
                color: theme.body,
                whiteSpace: "pre",
              }}
            >
              {TREE.join("\n")}
            </pre>
          </div>

          <div
            style={{
              opacity: badgeOpacity,
              marginTop: 22,
              display: "flex",
              gap: 14,
            }}
          >
            {["本地优先", "纯 Markdown", "Git 同步可选"].map((label) => (
              <span
                key={label}
                style={{
                  padding: "8px 18px",
                  borderRadius: 999,
                  border: `2px solid ${theme.line}`,
                  background: theme.accentSoft,
                  color: theme.accentInk,
                  fontFamily: theme.sans,
                  fontWeight: 700,
                  fontSize: 18,
                }}
              >
                {label}
              </span>
            ))}
          </div>
        </div>
      </AbsoluteFill>

      <CaptionBar text={text} />
    </AbsoluteFill>
  );
};
