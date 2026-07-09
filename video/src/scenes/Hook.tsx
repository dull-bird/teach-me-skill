import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { theme } from "../theme";
import { Cloud, Flower, Sparkle, SoftBlobBackground } from "../components/Decor";

export const Hook: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 16], [0, 1], { extrapolateRight: "clamp" });
  const y = interpolate(frame, [0, 16], [22, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      <SoftBlobBackground />
      <Cloud x={130} y={110} scale={1} phase={0.5} />
      <Cloud x={1600} y={840} scale={1.1} phase={2.3} />
      <Flower x={1720} y={150} scale={1} phase={1.4} color="#f2b880" />
      <Sparkle x={260} y={780} phase={1} />
      <Sparkle x={1550} y={260} phase={3} />

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", padding: "0 220px" }}>
        <div
          style={{
            opacity,
            transform: `translateY(${y}px)`,
            fontFamily: theme.serif,
            fontSize: 58,
            lineHeight: 1.55,
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
