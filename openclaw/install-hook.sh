#!/usr/bin/env bash
# Install and enable the teach-me-learning OpenClaw hook.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_DIR/openclaw/hooks/teach-me-learning"
DEST="$HOME/.openclaw/hooks/teach-me-learning"

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw command not found."
  exit 1
fi

mkdir -p "$HOME/.openclaw/hooks"
rm -rf "$DEST"
cp -r "$SRC" "$DEST"
echo "Installed OpenClaw hook to $DEST"

openclaw hooks enable teach-me-learning
