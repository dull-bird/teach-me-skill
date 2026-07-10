#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

ENV_FILE="${HOME}/Documents/work/repos/diamond-sutra-skill/promo-video/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

for variable in ALIYUN_AK_ID ALIYUN_AK_SECRET ALIYUN_APPKEY; do
  if [[ -z "${!variable:-}" ]]; then
    echo "ERROR: $variable is not set. Source Aliyun credentials first." >&2
    exit 1
  fi
done

voice="stanley"
speech_rate="-60"
scripts_dir="$(pwd)/scripts"

rm -f segments/*.mp3

while IFS=$'\t' read -r index id; do
  text=$(node -e "const segments = require('./segments.json'); process.stdout.write(segments[$index].text)")
  output="segments/${id}.mp3"
  echo "[$id] $text"
  python3 "${scripts_dir}/aliyun_tts.py" "$voice" "$text" "$output" "$speech_rate"
done < <(node -e "const segments = require('./segments.json'); segments.forEach((segment, index) => console.log(index + '\\t' + segment.id))")

node build_manifest.mjs
