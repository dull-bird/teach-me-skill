import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { Sparkle, SoftBlobBackground } from "../components/Decor";

type Locale = "zh" | "en";

const BADGES: Record<Locale, string[]> = {
  zh: ["本地优先", "纯 Markdown", "Git 同步可选", "多用户隔离"],
  en: ["Local-first", "Plain Markdown", "Git sync optional", "Multi-user"],
};

const PROFILE_TITLE: Record<Locale, string> = {
  zh: "你的学习画像",
  en: "Your learning profile",
};

const PROFILE_ITEMS: Record<Locale, { label: string; value: string | number }[]> = {
  zh: [
    { label: "rebase 掌握度", value: 72 },
    { label: "偏好教学风格", value: "代码示例 + 类比" },
    { label: "薄弱前置知识", value: "git reflog" },
    { label: "下次复习", value: "3 天后" },
  ],
  en: [
    { label: "rebase mastery", value: 72 },
    { label: "preferred style", value: "code + analogy" },
    { label: "weak prerequisite", value: "git reflog" },
    { label: "next review", value: "in 3 days" },
  ],
};

const TREE = [
  "vault/",
  "├── 00_Index.md",
  "├── 01_Knowledge_Graph.md",
  "├── 02_Concepts/",
  "├── 03_Algorithmic_Ideas/",
  "├── 04_Project_Maps/",
  "├── 05_Socratic_Questions/",
  "├── 06_Reviews/",
  "├── 07_Learning_Profile/",
  "│   ├── Knowledge_Tree.md",
  "│   ├── learning-state.json",
  "│   └── style-profile.json",
  "└── .teach-me/",
  "    └── events.jsonl",
];

export const VaultPanel: React.FC<{ text: string; locale?: Locale }> = ({ text, locale = "zh" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cardScale = spring({ frame, fps, config: { damping: 14, mass: 0.7 }, durationInFrames: 26 });
  const badgeOpacity = interpolate(frame, [20, 36], [0, 1], { extrapolateRight: "clamp" });
  const profileOpacity = interpolate(frame, [36, 52], [0, 1], { extrapolateRight: "clamp" });

  const profileItems = PROFILE_ITEMS[locale];
  const badges = BADGES[locale];
  const profileTitle = PROFILE_TITLE[locale];

  return (
    <AbsoluteFill>
      <SoftBlobBackground />
      <Sparkle x={160} y={160} phase={0.6} />
      <Sparkle x={1730} y={860} phase={2.5} />

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", paddingBottom: 130 }}>
        <div style={{ transform: `scale(${cardScale})`, display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div style={{ display: "flex", gap: 28, alignItems: "flex-start" }}>
            <div
              style={{
                width: 560,
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
                  padding: "22px 26px",
                  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
                  fontSize: 17,
                  lineHeight: 1.65,
                  color: theme.body,
                  whiteSpace: "pre",
                }}
              >
                {TREE.join("\n")}
              </pre>
            </div>

            <div
              style={{
                opacity: profileOpacity,
                width: 320,
                padding: "26px 28px",
                borderRadius: 18,
                background: theme.card,
                border: `2px solid ${theme.line}`,
                boxShadow: "0 30px 70px rgba(30,25,15,0.14)",
              }}
            >
              <div
                style={{
                  fontFamily: theme.sans,
                  fontWeight: 700,
                  fontSize: 18,
                  color: theme.accentInk,
                  marginBottom: 18,
                }}
              >
                {profileTitle}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {profileItems.map((item) => (
                  <div key={item.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontFamily: theme.sans, fontSize: 15, color: theme.muted }}>{item.label}</span>
                    <span style={{ fontFamily: theme.sans, fontWeight: 700, fontSize: 15, color: theme.ink }}>
                      {typeof item.value === "number" ? (
                        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span
                            style={{
                              display: "inline-block",
                              width: 80,
                              height: 8,
                              borderRadius: 4,
                              background: theme.line,
                              overflow: "hidden",
                            }}
                          >
                            <span
                              style={{
                                display: "block",
                                width: `${item.value}%`,
                                height: "100%",
                                background: theme.accent,
                              }}
                            />
                          </span>
                          {item.value}%
                        </span>
                      ) : (
                        item.value
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div
            style={{
              opacity: badgeOpacity,
              marginTop: 24,
              display: "flex",
              gap: 14,
            }}
          >
            {badges.map((label) => (
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
    </AbsoluteFill>
  );
};
