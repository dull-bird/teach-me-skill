import React from "react";
import { useCurrentFrame } from "remotion";
import { theme } from "../theme";

/** Soft blurred gradient blobs, echoing the site's hero background. */
export const SoftBlobBackground: React.FC<{ opacity?: number }> = ({ opacity = 1 }) => {
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: theme.paper,
        opacity,
      }}
    >
      <div
        style={{
          position: "absolute",
          left: "8%",
          top: "6%",
          width: 620,
          height: 560,
          borderRadius: "50%",
          background: theme.accent,
          opacity: 0.16,
          filter: "blur(70px)",
        }}
      />
      <div
        style={{
          position: "absolute",
          right: "6%",
          top: "-4%",
          width: 560,
          height: 500,
          borderRadius: "50%",
          background: theme.blue,
          opacity: 0.13,
          filter: "blur(70px)",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: "38%",
          bottom: "-6%",
          width: 480,
          height: 420,
          borderRadius: "50%",
          background: theme.coral,
          opacity: 0.1,
          filter: "blur(70px)",
        }}
      />
    </div>
  );
};

const bob = (frame: number, phase: number, amp = 10, speed = 0.05) =>
  Math.sin(frame * speed + phase) * amp;

/** A small, round, cute cloud made of overlapping circles. */
export const Cloud: React.FC<{ x: number; y: number; scale?: number; phase?: number }> = ({
  x,
  y,
  scale = 1,
  phase = 0,
}) => {
  const frame = useCurrentFrame();
  const dy = bob(frame, phase, 8, 0.04);
  return (
    <svg
      width={140 * scale}
      height={80 * scale}
      viewBox="0 0 140 80"
      style={{ position: "absolute", left: x, top: y + dy }}
    >
      <g fill="#ffffff" stroke={theme.line} strokeWidth={2}>
        <ellipse cx={45} cy={48} rx={38} ry={26} />
        <ellipse cx={85} cy={40} rx={32} ry={24} />
        <ellipse cx={70} cy={58} rx={44} ry={20} />
      </g>
    </svg>
  );
};

/** A tiny five-petal flower, matching the illustration accent palette. */
export const Flower: React.FC<{ x: number; y: number; scale?: number; phase?: number; color?: string }> = ({
  x,
  y,
  scale = 1,
  phase = 0,
  color = "#e79a9a",
}) => {
  const frame = useCurrentFrame();
  const rot = bob(frame, phase, 6, 0.035);
  return (
    <svg
      width={44 * scale}
      height={44 * scale}
      viewBox="0 0 44 44"
      style={{
        position: "absolute",
        left: x,
        top: y,
        transform: `rotate(${rot}deg)`,
      }}
    >
      <g fill={color}>
        {[0, 72, 144, 216, 288].map((deg) => (
          <ellipse
            key={deg}
            cx={22}
            cy={12}
            rx={7}
            ry={10}
            transform={`rotate(${deg} 22 22)`}
            opacity={0.9}
          />
        ))}
      </g>
      <circle cx={22} cy={22} r={6} fill="#f6c453" />
    </svg>
  );
};

/** Small four-point sparkle/star, twinkling. */
export const Sparkle: React.FC<{ x: number; y: number; scale?: number; phase?: number }> = ({
  x,
  y,
  scale = 1,
  phase = 0,
}) => {
  const frame = useCurrentFrame();
  const t = (Math.sin(frame * 0.08 + phase) + 1) / 2;
  const s = 0.7 + t * 0.5;
  const opacity = 0.35 + t * 0.55;
  return (
    <svg
      width={28 * scale}
      height={28 * scale}
      viewBox="0 0 28 28"
      style={{
        position: "absolute",
        left: x,
        top: y,
        transform: `scale(${s})`,
        opacity,
      }}
    >
      <path
        d="M14 0 C14 8 16 12 24 14 C16 16 14 20 14 28 C14 20 12 16 4 14 C12 12 14 8 14 0 Z"
        fill={theme.accent}
      />
    </svg>
  );
};

/** Rounded speech bubble, used for tiny caption chips near illustrations. */
export const Bubble: React.FC<{
  children: React.ReactNode;
  color?: string;
  bg?: string;
}> = ({ children, color = theme.ink, bg = "#ffffff" }) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      padding: "14px 26px",
      borderRadius: 999,
      background: bg,
      color,
      border: `2px solid ${theme.line}`,
      fontFamily: theme.sans,
      fontWeight: 650,
      fontSize: 34,
      boxShadow: "0 10px 30px rgba(30,25,15,0.10)",
    }}
  >
    {children}
  </div>
);
