#!/usr/bin/env bash
# Bootstrap script: run this on the new machine after copying the project over.
#
# Usage:
#   bash migrate.sh                  # interactive
#   STEPFUN_HOME=/path bash migrate.sh
#
# What it does:
#   1. Creates a venv (optional but recommended)
#   2. pip install -e . so `python -m stepfun_image.cli` and
#      `python -m stepfun_audio.cli` work from anywhere
#   3. Installs all SKILL.md files under skill/ into ~/.claude/skills/
#      (skill/SKILL.md         -> stepfun-image
#       skill/audio/SKILL.md   -> stepfun-audio)
#   4. Runs `whoami` to verify key resolution

set -euo pipefail

PROJECT_DIR="${STEPFUN_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
SKILLS_DIR="${HOME}/.claude/skills"

echo "==> project: $PROJECT_DIR"
echo "==> skills root: $SKILLS_DIR"

# 1. venv (best-effort, ignore if already in one)
if [[ -z "${VIRTUAL_ENV:-}" && ! -d "$PROJECT_DIR/.venv" ]]; then
  echo "==> creating venv"
  python3 -m venv "$PROJECT_DIR/.venv"
  # shellcheck disable=SC1091
  source "$PROJECT_DIR/.venv/bin/activate"
fi

# 2. install
echo "==> pip install -e ."
python -m pip install -e "$PROJECT_DIR"

# 3. drop all SKILL.md files: map layout skill/X/SKILL.md -> stepfun-X
#    and skill/SKILL.md -> stepfun-image
install_skill() {
  local src="$1"
  local name="$2"
  local dst_dir="$SKILLS_DIR/$name"
  local dst="$dst_dir/SKILL.md"
  if [[ ! -f "$src" ]]; then
    echo "!! $src not found — skipping"
    return
  fi
  mkdir -p "$dst_dir"
  cp "$src" "$dst"
  echo "   - $name installed at $dst"
}

echo "==> installing skills"
install_skill "$PROJECT_DIR/skill/SKILL.md" "stepfun-image"
install_skill "$PROJECT_DIR/skill/audio/SKILL.md" "stepfun-audio"

# 4. verify key
echo "==> whoami"
python -m stepfun_image.cli whoami

echo
echo "Done. Try:"
echo "  python -m stepfun_image.cli t2i \"hello\" -o /tmp/hello.png"
echo "  python -m stepfun_audio.cli tts \"hello\" -o /tmp/hello.mp3"
