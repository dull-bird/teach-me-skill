import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";

export const WorkflowPanel: React.FC<{ locale?: "zh" | "en" }> = ({ locale = "zh" }) => {
  const image = locale === "en" ? "workflow-en.png" : "workflow.png";
  return (
    <AbsoluteFill
      style={{
        background: "#f8f7f2",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Img
        src={staticFile(image)}
        style={{ width: "100%", height: "100%", objectFit: "contain" }}
      />
    </AbsoluteFill>
  );
};
