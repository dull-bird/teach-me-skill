import React from "react";
import { Audio, Series, staticFile, useCurrentFrame } from "remotion";
import manifestZh from "./data/manifest.json";
import manifestEn from "./data/manifest-en.json";
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

type Locale = "zh" | "en";

const manifests: Record<Locale, typeof manifestZh> = {
  zh: manifestZh,
  en: manifestEn,
};

type NarrationSegment = (typeof manifestZh.segments)[number];

type SceneGroup = {
  scene: string;
  segments: NarrationSegment[];
  startFrame: number;
  endFrame: number;
};

const buildSceneGroups = (manifest: typeof manifestZh): SceneGroup[] => {
  const groups: SceneGroup[] = [];
  for (const segment of manifest.segments) {
    const previous = groups.at(-1);
    if (!previous || previous.scene !== segment.scene) {
      groups.push({
        scene: segment.scene,
        segments: [segment],
        startFrame: segment.startFrame,
        endFrame: segment.startFrame,
      });
    } else {
      previous.segments.push(segment);
    }
  }
  groups.forEach((group, index) => {
    group.endFrame = index < groups.length - 1
      ? groups[index + 1].startFrame
      : manifest.totalDurationFrames;
  });
  return groups;
};

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

const renderScene = (scene: string, text: string, locale: Locale) => {
  switch (scene) {
    case "hook":
      return <Hook text={text} />;
    case "intro":
      return <Intro locale={locale} />;
    case "why":
      return <Why text={text} />;
    case "story":
      return <StoryPanel locale={locale} />;
    case "workflow-steps":
    case "workflow-skills":
      return <WorkflowPanel locale={locale} />;
    case "quiz":
      return <QuizPanel text={text} locale={locale} />;
    case "vault":
      return <VaultPanel text={text} locale={locale} />;
    case "import":
      return <ImportPanel text={text} locale={locale} />;
    case "install":
      return <InstallPanel text={text} locale={locale} />;
    case "quote":
      return <Quote locale={locale} />;
    case "outro":
      return <Outro locale={locale} />;
    default:
      return null;
  }
};

type GroupedSceneProps = { group: SceneGroup; locale: Locale };

const GroupedScene: React.FC<GroupedSceneProps> = ({ group, locale }) => {
  const frame = useCurrentFrame();
  const absoluteFrame = group.startFrame + frame;
  return renderScene(group.scene, activeText(group.segments, absoluteFrame), locale);
};

export type TeachMePromoProps = { locale?: Locale };

export const TeachMePromo: React.FC<TeachMePromoProps> = ({ locale = "zh" }) => {
  const manifest = manifests[locale];
  const sceneGroups = buildSceneGroups(manifest);
  const audioFile = locale === "en" ? "narration-en.mp3" : "narration.mp3";
  return (
    <>
      <Audio src={staticFile(audioFile)} />
      <Series>
        {sceneGroups.map((group, index) => {
          const startFrame = index === 0 ? 0 : group.startFrame;
          return (
            <Series.Sequence key={`${group.scene}-${group.startFrame}`} durationInFrames={group.endFrame - startFrame}>
              <GroupedScene group={group} locale={locale} />
            </Series.Sequence>
          );
        })}
      </Series>
    </>
  );
};

export const TOTAL_DURATION = manifestZh.totalDurationFrames;
