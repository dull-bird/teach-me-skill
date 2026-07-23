import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { Flower, SoftBlobBackground, Sparkle } from "../components/Decor";

type Locale = "zh" | "en";

const QUOTE: Record<Locale, { lines: string[]; cite: string }> = {
  zh: {
    lines: ["把持续建设自己的大脑，", "当作此生唯一重要的任务。"],
    cite: "—— 李笑来，《专注的真相》",
  },
  en: {
    lines: ["Keep building your own brain,", "as the one task that matters most in this life."],
    cite: "— Li Xiaolai, The Truth of Focus",
  },
};

export const Quote: React.FC<{ locale?: Locale }> = ({ locale = "zh" }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const markScale = spring({ frame, fps, config: { damping: 11, mass: 0.5 }, durationInFrames: 18 });
  const quoteOpacity = interpolate(frame, [14, 36], [0, 1], { extrapolateRight: "clamp" });
  const quoteY = interpolate(frame, [14, 36], [16, 0], { extrapolateRight: "clamp" });
  const citeOpacity = interpolate(frame, [50, 70], [0, 1], { extrapolateRight: "clamp" });

  const sceneFade =
    interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" }) *
    interpolate(frame, [durationInFrames - 16, durationInFrames], [1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

  const copy = QUOTE[locale];

  return (
    <AbsoluteFill style={{ opacity: sceneFade }}>
      <SoftBlobBackground />
      <Flower x={260} y={200} scale={1} phase={0.4} color="#f2b880" />
      <Flower x={1600} y={840} scale={1.2} phase={2.1} color="#e79a9a" />
      <Sparkle x={1700} y={220} phase={1.2} />
      <Sparkle x={220} y={860} phase={3.4} />

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", padding: "0 260px" }}>
        <div
          style={{
            transform: `scale(${markScale})`,
            fontFamily: theme.serif,
            fontSize: 120,
            lineHeight: 1,
            color: theme.accent,
            opacity: 0.55,
            marginBottom: 6,
          }}
        >
          "
        </div>
        <div
          style={{
            opacity: quoteOpacity,
            transform: `translateY(${quoteY}px)`,
            fontFamily: theme.serif,
            fontStyle: "italic",
            fontSize: 56,
            lineHeight: 1.5,
            color: theme.ink,
            textAlign: "center",
          }}
        >
          {copy.lines.map((line, i) => (
            <React.Fragment key={i}>
              {line}
              {i < copy.lines.length - 1 && <br />}
            </React.Fragment>
          ))}
        </div>
        <div
          style={{
            opacity: citeOpacity,
            marginTop: 30,
            fontFamily: theme.sans,
            fontSize: 26,
            fontWeight: 650,
            letterSpacing: 1,
            color: theme.muted,
          }}
        >
          {copy.cite}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
