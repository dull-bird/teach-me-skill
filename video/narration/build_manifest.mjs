import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const fps = 30;
const defaultPauseAfterSec = 0.5;
const leadInSec = 0.2;
const segmentsDir = path.join(__dirname, "segments");
const outputDir = path.join(__dirname, "..", "out");
const publicDir = path.join(__dirname, "..", "public");
const sourceManifestPath = path.join(__dirname, "..", "src", "data", "manifest.json");
const segments = JSON.parse(fs.readFileSync(path.join(__dirname, "segments.json"), "utf8"));

fs.mkdirSync(segmentsDir, { recursive: true });
fs.mkdirSync(outputDir, { recursive: true });
fs.mkdirSync(publicDir, { recursive: true });

const durationOf = (file) => {
  const output = execSync(
    `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${file}"`,
  )
    .toString()
    .trim();
  return Number.parseFloat(output);
};

const srtTime = (seconds) => {
  const milliseconds = Math.round(seconds * 1000);
  const hours = Math.floor(milliseconds / 3_600_000);
  const minutes = Math.floor((milliseconds % 3_600_000) / 60_000);
  const wholeSeconds = Math.floor((milliseconds % 60_000) / 1000);
  const remainder = milliseconds % 1000;
  const pad = (value, width = 2) => String(value).padStart(width, "0");
  return `${pad(hours)}:${pad(minutes)}:${pad(wholeSeconds)},${pad(remainder, 3)}`;
};

const resampledDir = path.join(segmentsDir, "resampled");
fs.mkdirSync(resampledDir, { recursive: true });

const silenceFileFor = (seconds) => {
  const duration = Math.max(0, seconds);
  const filename = `_silence_${duration.toFixed(3)}.wav`;
  const output = path.join(segmentsDir, filename);
  if (!fs.existsSync(output)) {
    execSync(`ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=mono -t ${duration} "${output}"`, {
      stdio: "inherit",
    });
  }
  return output;
};

const leadInFile = silenceFileFor(leadInSec);
const concatEntries = [`file '${path.basename(leadInFile)}'`];
const manifestSegments = [];
const srtLines = [];
let cursor = leadInSec;

segments.forEach((segment, index) => {
  const source = path.join(segmentsDir, `${segment.id}.mp3`);
  const resampled = path.join(resampledDir, `${segment.id}.wav`);
  if (!fs.existsSync(source)) {
    throw new Error(`Missing narration segment: ${source}`);
  }

  execSync(`ffmpeg -y -i "${source}" -ar 44100 -ac 1 "${resampled}"`, { stdio: "inherit" });
  const durationSec = durationOf(source);
  const startSec = cursor;
  const endSec = startSec + durationSec;
  const pauseAfterSec = index === segments.length - 1 ? 0 : (segment.pauseAfterSec ?? defaultPauseAfterSec);

  manifestSegments.push({
    id: segment.id,
    scene: segment.scene,
    text: segment.text,
    startSec,
    durationSec,
    startFrame: Math.round(startSec * fps),
    durationFrames: Math.round(durationSec * fps),
    pauseAfterSec,
  });

  srtLines.push(String(index + 1));
  srtLines.push(`${srtTime(startSec)} --> ${srtTime(endSec)}`);
  srtLines.push(segment.text);
  srtLines.push("");

  concatEntries.push(`file '${path.relative(segmentsDir, resampled)}'`);
  if (pauseAfterSec > 0) {
    concatEntries.push(`file '${path.basename(silenceFileFor(pauseAfterSec))}'`);
  }
  cursor = endSec + pauseAfterSec;
});

const manifest = {
  fps,
  totalDurationSec: cursor,
  totalDurationFrames: Math.round(cursor * fps) + fps,
  segments: manifestSegments,
};

fs.writeFileSync(path.join(segmentsDir, "concat.txt"), `${concatEntries.join("\n")}\n`);
fs.writeFileSync(path.join(__dirname, "manifest.json"), JSON.stringify(manifest, null, 2));
fs.writeFileSync(sourceManifestPath, JSON.stringify(manifest, null, 2));
fs.writeFileSync(path.join(outputDir, "subtitles.srt"), srtLines.join("\n"));

const narrationWav = path.join(publicDir, "narration.wav");
const narrationMp3 = path.join(publicDir, "narration.mp3");
execSync(`ffmpeg -y -f concat -safe 0 -i "${path.join(segmentsDir, "concat.txt")}" -ar 44100 -ac 2 "${narrationWav}"`, {
  stdio: "inherit",
});
execSync(`ffmpeg -y -i "${narrationWav}" -codec:a libmp3lame -qscale:a 2 "${narrationMp3}"`, {
  stdio: "inherit",
});

console.log(`Total duration (s): ${manifest.totalDurationSec.toFixed(2)}`);
console.log(`Total duration (frames @30fps): ${manifest.totalDurationFrames}`);
console.log("Wrote narration manifest, subtitle cues, and narration.mp3");
