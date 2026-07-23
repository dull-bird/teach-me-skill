import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";

export const StoryPanel: React.FC<{ locale?: "zh" | "en" }> = ({ locale = "zh" }) => {
  const image = locale === "en" ? "story-en.jpg" : "story.jpg";
  return (
    <AbsoluteFill style={{ background: "#fbfaf7", overflow: "hidden", alignItems: "center", justifyContent: "center" }}>
      <Img
        src={staticFile(image)}
        style={{ width: "100%", height: "100%", objectFit: "contain", flexShrink: 0 }}
      />
    </AbsoluteFill>
  );
};
