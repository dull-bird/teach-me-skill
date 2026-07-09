import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FPS = 30;
const GAP_SEC = 0.4; // silence between segments
const LEAD_IN_SEC = 0.2; // small silence before first line

const segments = JSON.parse(fs.readFileSync(path.join(__dirname, "segments.json"), "utf8"));

function durationOf(file) {
  const out = execSync(
    `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${file}"`
  )
    .toString()
    .trim();
  return parseFloat(out);
}

let cursor = LEAD_IN_SEC;
const manifest = [];
const srtLines = [];
const concatListPath = path.join(__dirname, "segments", "concat.txt");
const concatEntries = [];

// Leading silence file
const silenceLead = path.join(__dirname, "segments", "_silence_lead.wav");
execSync(
  `ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=mono -t ${LEAD_IN_SEC} "${silenceLead}"`
);
concatEntries.push(`file '${path.basename(silenceLead)}'`);

const silenceGap = path.join(__dirname, "segments", "_silence_gap.wav");
execSync(
  `ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=mono -t ${GAP_SEC} "${silenceGap}"`
);

function srtTime(sec) {
  const ms = Math.round(sec * 1000);
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  const msRem = ms % 1000;
  const pad = (n, l = 2) => String(n).padStart(l, "0");
  return `${pad(h)}:${pad(m)}:${pad(s)},${pad(msRem, 3)}`;
}

segments.forEach((seg, i) => {
  const wavFile = path.join(__dirname, "segments", `${seg.id}.wav`);
  const dur = durationOf(wavFile);
  const startSec = cursor;
  const endSec = startSec + dur;

  manifest.push({
    id: seg.id,
    scene: seg.scene,
    text: seg.text,
    startSec,
    durationSec: dur,
    startFrame: Math.round(startSec * FPS),
    durationFrames: Math.round(dur * FPS),
  });

  srtLines.push(String(i + 1));
  srtLines.push(`${srtTime(startSec)} --> ${srtTime(endSec)}`);
  srtLines.push(seg.text);
  srtLines.push("");

  concatEntries.push(`file '${seg.id}.wav'`);
  if (i < segments.length - 1) {
    concatEntries.push(`file '${path.basename(silenceGap)}'`);
  }

  cursor = endSec + GAP_SEC;
});

const totalDurationSec = cursor - GAP_SEC;
const totalDurationFrames = Math.round(totalDurationSec * FPS) + 30; // +1s tail for outro fade

fs.writeFileSync(concatListPath, concatEntries.join("\n") + "\n");
fs.writeFileSync(
  path.join(__dirname, "manifest.json"),
  JSON.stringify({ fps: FPS, totalDurationSec, totalDurationFrames, segments: manifest }, null, 2)
);
fs.writeFileSync(path.join(__dirname, "..", "public", "subtitles.srt"), srtLines.join("\n"));

// Concatenate into one narration track (WAV), then export MP3 for Remotion.
const narrationWav = path.join(__dirname, "..", "public", "narration.wav");
execSync(
  `ffmpeg -y -f concat -safe 0 -i "${concatListPath}" -ar 44100 -ac 2 "${narrationWav}"`
);
const narrationMp3 = path.join(__dirname, "..", "public", "narration.mp3");
execSync(`ffmpeg -y -i "${narrationWav}" -codec:a libmp3lame -qscale:a 2 "${narrationMp3}"`);

console.log("Total duration (s):", totalDurationSec.toFixed(2));
console.log("Total duration (frames @30fps):", totalDurationFrames);
console.log("Wrote manifest.json, subtitles.srt, narration.mp3");
