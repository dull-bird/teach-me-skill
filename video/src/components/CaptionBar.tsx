import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { theme } from "../theme";

export const CaptionBar: React.FC<{ text: string; bottom?: number }> = ({ text, bottom = 64 }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const y = interpolate(frame, [0, 12], [12, 0], { extrapolateRight: "clamp" });

  return (
    <div
      style={{
        position: "absolute",
        left: "50%",
        bottom,
        transform: `translate(-50%, ${y}px)`,
        opacity,
        maxWidth: 1540,
        padding: "20px 40px",
        borderRadius: 22,
        background: "rgba(255,252,247,0.94)",
        border: `2px solid ${theme.line}`,
        boxShadow: "0 24px 60px rgba(30,25,15,0.20)",
        fontFamily: theme.sans,
        fontSize: 32,
        fontWeight: 600,
        lineHeight: 1.55,
        color: theme.ink,
        textAlign: "center",
      }}
    >
      {text}
    </div>
  );
};
