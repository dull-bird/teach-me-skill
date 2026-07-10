import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";

export const WorkflowPanel: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        background: "#f8f7f2",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Img
        src={staticFile("workflow.png")}
        style={{ width: "100%", height: "100%", objectFit: "contain" }}
      />
    </AbsoluteFill>
  );
};
