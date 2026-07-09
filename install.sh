#!/usr/bin/env bash
# Install the teach-me Agent Skill into detected local agent skill directories.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEACH_ME_SRC="$REPO_DIR/skills/teach-me"
CHECK_SRC="$REPO_DIR/skills/check"
RECAP_SRC="$REPO_DIR/skills/recap"
EXAM_SRC="$REPO_DIR/skills/exam"

install_skill() {
  local src="$1"
  local target_root="$2"
  local label="$3"
  local name="$4"
  local dest="$target_root/skills/$name"

  mkdir -p "$target_root/skills"
  rm -rf "$dest"
  cp -r "$src" "$dest"
  echo "Installed into $label: $dest"
}

install_hook_installer() {
  local repo_agent_dir="$1"
  local target_skill_dir="$2"
  local target_name="$3"

  if [ -f "$repo_agent_dir/install_hook.py" ]; then
    cp "$repo_agent_dir/install_hook.py" "$target_skill_dir/$target_name"
    echo "  Copied hook installer: $target_skill_dir/$target_name"
  fi
}

install_into() {
  local target_root="$1"
  local label="$2"

  install_skill "$TEACH_ME_SRC" "$target_root" "$label" "teach-me"
  install_skill "$CHECK_SRC" "$target_root" "$label" "check"
  install_skill "$RECAP_SRC" "$target_root" "$label" "recap"
  install_skill "$EXAM_SRC" "$target_root" "$label" "exam"

  # Copy hook installers into the teach-me skill dir so the runtime can
  # enable/disable hooks later via `teach_me.py hooks`.
  local teach_me_dest="$target_root/skills/teach-me"
  install_hook_installer "$REPO_DIR/claude-code" "$teach_me_dest" "install-claude-code-hook.py"
  install_hook_installer "$REPO_DIR/codex" "$teach_me_dest" "install-codex-hook.py"
  install_hook_installer "$REPO_DIR/kimi" "$teach_me_dest" "install-kimi-hook.py"
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
  echo "No known agent home was detected. Manually copy skills/teach-me, skills/check, skills/recap, and skills/exam into an agent skills directory."
  exit 1
fi

echo
echo "Teach Me, Teach Me Check, Teach Me Recap, and Teach Me Exam skills installed. First capture will ask to confirm ~/.teach_me_skill/vault, note language, and optional Git sync."
