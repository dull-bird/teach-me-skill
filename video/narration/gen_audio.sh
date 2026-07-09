#!/bin/bash
set -e
cd "$(dirname "$0")"
VOICE="Tingting"
RATE=172
node -e '
const fs = require("fs");
const segs = JSON.parse(fs.readFileSync("segments.json", "utf8"));
segs.forEach((s,i) => console.log(i + "\t" + s.id));
' > /tmp/seg_index.tsv

while IFS=$'\t' read -r idx id; do
  text=$(node -e "const s=require('./segments.json'); process.stdout.write(s[$idx].text)")
  say -v "$VOICE" -r "$RATE" -o "segments/${id}.aiff" "$text"
  afconvert -f WAVE -d LEI16 "segments/${id}.aiff" "segments/${id}.wav"
  rm "segments/${id}.aiff"
  dur=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "segments/${id}.wav")
  echo "$id $dur"
done < /tmp/seg_index.tsv
