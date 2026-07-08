#!/usr/bin/env bash
# Install the teach-me Agent Skill into detected local agent skill directories.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$REPO_DIR/skills/teach-me"

install_into() {
  local target_root="$1"
  local label="$2"
  local dest="$target_root/skills/teach-me"

  mkdir -p "$target_root/skills"
  rm -rf "$dest"
  cp -r "$SRC" "$dest"
  echo "Installed into $label: $dest"
}

installed_any=false

if [ -d "$HOME/.codex" ]; then
  install_into "$HOME/.codex" "Codex"
  installed_any=true
  echo "  Optional: run codex/install-hook.sh"
fi

if [ -d "$HOME/.claude" ]; then
  install_into "$HOME/.claude" "Claude Code"
  installed_any=true
  echo "  Optional: run claude-code/install-hook.sh"
fi

if [ -d "$HOME/.kimi" ] || [ -d "$HOME/.agents" ]; then
  install_into "$HOME/.agents" "shared ~/.agents"
  installed_any=true
  echo "  Optional: run kimi/install-hook.sh"
fi

if [ -d "$HOME/.openclaw" ]; then
  install_into "$HOME/.openclaw" "OpenClaw"
  installed_any=true
  echo "  Optional: run openclaw/install-hook.sh"
fi

if [ "$installed_any" = false ]; then
  echo "No known agent home was detected. Manually copy skills/teach-me into an agent skills directory."
  exit 1
fi

echo
echo "Teach Me skill installed. First capture will ask to confirm ~/.teach_me_skill/vault and note language."
