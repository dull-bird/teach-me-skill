import React from "react";
import { Audio, Series, staticFile, useCurrentFrame } from "remotion";
import manifest from "./data/manifest.json";
import { Hook } from "./scenes/Hook";
import { ImportPanel } from "./scenes/ImportPanel";
import { InstallPanel } from "./scenes/InstallPanel";
import { Intro } from "./scenes/Intro";
import { Outro } from "./scenes/Outro";
import { QuizPanel } from "./scenes/QuizPanel";
import { Quote } from "./scenes/Quote";
import { StoryPanel } from "./scenes/StoryPanel";
import { VaultPanel } from "./scenes/VaultPanel";
import { Why } from "./scenes/Why";
import { WorkflowPanel } from "./scenes/WorkflowPanel";

type NarrationSegment = (typeof manifest.segments)[number];

type SceneGroup = {
  scene: string;
  segments: NarrationSegment[];
  startFrame: number;
  endFrame: number;
};

export const TOTAL_DURATION = manifest.totalDurationFrames;

const sceneGroups: SceneGroup[] = [];

for (const segment of manifest.segments) {
  const previous = sceneGroups.at(-1);
  if (!previous || previous.scene !== segment.scene) {
    sceneGroups.push({
      scene: segment.scene,
      segments: [segment],
      startFrame: segment.startFrame,
      endFrame: segment.startFrame,
    });
  } else {
    previous.segments.push(segment);
  }
}

sceneGroups.forEach((group, index) => {
  group.endFrame = index < sceneGroups.length - 1
    ? sceneGroups[index + 1].startFrame
    : manifest.totalDurationFrames;
});

const activeText = (segments: NarrationSegment[], frame: number) => {
  let text = segments[0].text;
  for (const segment of segments) {
    if (frame >= segment.startFrame) {
      text = segment.text;
    } else {
      break;
    }
  }
  return text;
};

const renderScene = (scene: string, text: string) => {
  switch (scene) {
    case "hook":
      return <Hook text={text} />;
    case "intro":
      return <Intro />;
    case "why":
      return <Why text={text} />;
    case "story":
      return <StoryPanel />;
    case "workflow-steps":
    case "workflow-skills":
      return <WorkflowPanel />;
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

const GroupedScene: React.FC<{ group: SceneGroup }> = ({ group }) => {
  const frame = useCurrentFrame();
  const absoluteFrame = group.startFrame + frame;
  return renderScene(group.scene, activeText(group.segments, absoluteFrame));
};

export const TeachMePromo: React.FC = () => (
  <>
    <Audio src={staticFile("narration.mp3")} />
    <Series>
      {sceneGroups.map((group, index) => {
        const startFrame = index === 0 ? 0 : group.startFrame;
        return (
          <Series.Sequence key={`${group.scene}-${group.startFrame}`} durationInFrames={group.endFrame - startFrame}>
            <GroupedScene group={group} />
          </Series.Sequence>
        );
      })}
    </Series>
  </>
);
