#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

locale="${1:-zh}"
locale_suffix=""
if [[ "$locale" != "zh" ]]; then
  locale_suffix="-$locale"
fi

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

if [[ "$locale" == "zh" ]]; then
  voice="stanley"
  speech_rate="-60"
else
  voice="harry"
  speech_rate="-50"
fi
scripts_dir="$(pwd)/scripts"
segments_file="segments${locale_suffix}.json"
segments_dir="segments/${locale}"

mkdir -p "$segments_dir"
rm -f "$segments_dir"/*.mp3

while IFS=$'\t' read -r index id; do
  text=$(node -e "const segments = require('./${segments_file}'); process.stdout.write(segments[${index}].text)")
  output="${segments_dir}/${id}.mp3"
  echo "[$id] $text"
  python3 "${scripts_dir}/aliyun_tts.py" "$voice" "$text" "$output" "$speech_rate"
done < <(node -e "const segments = require('./${segments_file}'); segments.forEach((segment, index) => console.log(index + '\\t' + segment.id))")

node build_manifest.mjs --locale "$locale"
