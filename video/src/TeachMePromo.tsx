import React from "react";
import { Audio, Series, staticFile } from "remotion";
import manifest from "./data/manifest.json";
import { Hook } from "./scenes/Hook";
import { Intro } from "./scenes/Intro";
import { Why } from "./scenes/Why";
import { StoryPanel } from "./scenes/StoryPanel";
import { WorkflowPanel } from "./scenes/WorkflowPanel";
import { QuizPanel } from "./scenes/QuizPanel";
import { VaultPanel } from "./scenes/VaultPanel";
import { ImportPanel } from "./scenes/ImportPanel";
import { InstallPanel } from "./scenes/InstallPanel";
import { Quote } from "./scenes/Quote";
import { Outro } from "./scenes/Outro";

export const TOTAL_DURATION = manifest.totalDurationFrames;

const renderScene = (scene: string, text: string) => {
  switch (scene) {
    case "hook":
      return <Hook text={text} />;
    case "intro":
      return <Intro />;
    case "why":
      return <Why text={text} />;
    case "story":
      return <StoryPanel text={text} />;
    case "workflow-steps":
      return <WorkflowPanel text={text} focus="steps" />;
    case "workflow-skills":
      return <WorkflowPanel text={text} focus="skills" />;
    case "quiz":
      return <QuizPanel text={text} />;
    case "vault":
      return <VaultPanel text={text} />;
    case "import":
      return <ImportPanel text={text} />;
    case "install":
      return <InstallPanel text={text} />;
    case "quote":
      return <Quote />;
    case "outro":
      return <Outro />;
    default:
      return null;
  }
};

export const TeachMePromo: React.FC = () => {
  const segments = manifest.segments;

  return (
    <>
      <Audio src={staticFile("narration.mp3")} />
      <Series>
        {segments.map((seg, i) => {
          // Series always starts sequence 0 at frame 0; the manifest's startFrame
          // values are audio-relative (including a small lead-in), so anchor the
          // first scene at 0 and every later boundary at its own startFrame —
          // this keeps captions exactly in sync with the narration track.
          const thisStart = i === 0 ? 0 : seg.startFrame;
          const nextStart = i < segments.length - 1 ? segments[i + 1].startFrame : manifest.totalDurationFrames;
          const durationInFrames = nextStart - thisStart;
          return (
            <Series.Sequence key={seg.id} durationInFrames={durationInFrames}>
              {renderScene(seg.scene, seg.text)}
            </Series.Sequence>
          );
        })}
      </Series>
    </>
  );
};
