import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { Sparkle, SoftBlobBackground } from "../components/Decor";

type Locale = "zh" | "en";

const COPY: Record<Locale, { question: string; options: string[]; header: string; progress: (correct: number) => string }> = {
  zh: {
    question: "你刚用 git rebase -i 压缩了几个提交。rebase 和 merge 的本质区别是什么？",
    options: [
      "rebase 会创建一个新的合并提交，merge 不会",
      "rebase 把提交逐个重放到新 base 上，生成全新的提交哈希；merge 保留双方历史，多一个合并提交",
      "rebase 只能用在本地分支，merge 只能用在远程分支",
      "两者效果完全等价，只是命令不同",
    ],
    header: "TEACH ME EXAM · 第 1 / 3 题",
    progress: (correct) => `答对 ${correct}`,
  },
  en: {
    question: "You just squashed a few commits with git rebase -i. What is the fundamental difference between rebase and merge?",
    options: [
      "rebase creates a new merge commit; merge does not",
      "rebase replays commits onto a new base, generating fresh commit hashes; merge keeps both histories and adds one merge commit",
      "rebase is only for local branches; merge is only for remote branches",
      "The two are exactly equivalent; only the command differs",
    ],
    header: "TEACH ME EXAM · 1 / 3",
    progress: (correct) => `${correct} correct`,
  },
};

const CORRECT = 1;
const LETTERS = ["A", "B", "C", "D"];

export const QuizPanel: React.FC<{ text: string; locale?: Locale }> = ({ text, locale = "zh" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const copy = COPY[locale];
  const cardScale = spring({ frame, fps, config: { damping: 14, mass: 0.7 }, durationInFrames: 26 });
  const revealFrame = 90; // when the "click" reveals the correct answer
  const revealT = spring({ frame: frame - revealFrame, fps, config: { damping: 12 }, durationInFrames: 16 });

  return (
    <AbsoluteFill>
      <SoftBlobBackground />
      <Sparkle x={150} y={150} phase={0.4} />
      <Sparkle x={1740} y={880} phase={2.1} />

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", paddingBottom: 170 }}>
        <div
          style={{
            transform: `scale(${cardScale})`,
            width: 1080,
            background: theme.card,
            border: `2px solid ${theme.line}`,
            borderRadius: 22,
            padding: 42,
            boxShadow: "0 30px 70px rgba(30,25,15,0.14)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: 22,
              fontFamily: theme.sans,
              fontWeight: 700,
              fontSize: 20,
              color: theme.muted,
              textTransform: "uppercase",
              letterSpacing: 1,
            }}
          >
            <span>{copy.header}</span>
            <span style={{ color: theme.accentInk }}>{copy.progress(frame >= revealFrame ? 1 : 0)}</span>
          </div>
          <div
            style={{
              fontFamily: theme.serif,
              fontSize: 34,
              lineHeight: 1.5,
              color: theme.ink,
              marginBottom: 26,
            }}
          >
            {copy.question}
          </div>
          <div style={{ display: "grid", gap: 14 }}>
            {copy.options.map((opt, i) => {
              const isCorrect = i === CORRECT;
              const revealed = frame >= revealFrame;
              const bg = revealed && isCorrect ? `color-mix(in srgb, #2d8a5f ${14 * revealT}%, ${theme.card})` : theme.paper;
              const border = revealed && isCorrect ? `2px solid #2d8a5f` : `2px solid ${theme.line}`;
              return (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 14,
                    padding: "16px 18px",
                    borderRadius: 14,
                    background: bg,
                    border,
                    fontFamily: theme.sans,
                    fontSize: 22,
                    lineHeight: 1.5,
                    color: theme.body,
                  }}
                >
                  <span
                    style={{
                      flex: "0 0 auto",
                      width: 30,
                      height: 30,
                      borderRadius: "50%",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontFamily: theme.sans,
                      fontWeight: 700,
                      fontSize: 15,
                      color: revealed && isCorrect ? "#fff" : theme.muted,
                      background: revealed && isCorrect ? "#2d8a5f" : theme.card,
                      border: `1px solid ${revealed && isCorrect ? "#2d8a5f" : theme.line}`,
                    }}
                  >
                    {LETTERS[i]}
                  </span>
                  <span>{opt}</span>
                </div>
              );
            })}
          </div>
        </div>
      </AbsoluteFill>

    </AbsoluteFill>
  );
};
