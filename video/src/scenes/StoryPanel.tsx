import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CaptionBar } from "../components/CaptionBar";

export const StoryPanel: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const scale = interpolate(frame, [0, durationInFrames], [1.05, 1.16], { extrapolateRight: "clamp" });
  const panX = interpolate(frame, [0, durationInFrames], [10, -50], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: "#fbfaf7", overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          transform: `scale(${scale}) translateX(${panX}px)`,
        }}
      >
        <Img src={staticFile("story.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </div>
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "linear-gradient(180deg, rgba(0,0,0,0) 55%, rgba(20,18,12,0.32) 100%)",
        }}
      />
      <CaptionBar text={text} />
    </AbsoluteFill>
  );
};
