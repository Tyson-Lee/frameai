#!/usr/bin/env bash
# FrameAI installer — one-line install from inside Claude Code (or terminal).
#
# Usage (inside Claude Code chat):
#   사용자: "FrameAI 설치해줘"
#   Claude: (runs)  curl -fsSL https://raw.githubusercontent.com/Tyson-Lee/frameai/main/install.sh | bash
#
# Usage (terminal direct):
#   curl -fsSL <URL>/install.sh | bash
#   FRAMEAI_HOME=~/my-frameai bash install.sh    # custom location
#
# What this does:
#   1. Resolves install location (FRAMEAI_HOME or ~/frameai by default)
#   2. Clones the repo (or pulls if already cloned)
#   3. Runs setup.sh
#   4. Prints next steps with the path the user can open in Claude Code
set -euo pipefail

TARGET="${FRAMEAI_HOME:-$HOME/frameai}"
REPO_URL="${FRAMEAI_REPO_URL:-https://github.com/Tyson-Lee/frameai.git}"
BRANCH="${FRAMEAI_BRANCH:-main}"

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$*"; }

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    red "✘ missing: $1"
    return 1
  fi
}

missing=0
need git    || missing=1
need claude || { yellow "  install Claude Code first: https://docs.claude.com/en/docs/claude-code/install"; missing=1; }
need python3 || missing=1
[ $missing -ne 0 ] && exit 2

if [ -d "$TARGET/.git" ]; then
  yellow "FrameAI is already installed at $TARGET. Updating instead…"
  cd "$TARGET"
  if [ -n "$(git status --porcelain)" ]; then
    red "✘ uncommitted changes in $TARGET — resolve manually or set FRAMEAI_HOME=<other-path>"
    exit 3
  fi
  git pull --ff-only origin "$BRANCH"
elif [ -e "$TARGET" ]; then
  red "✘ $TARGET exists but is not a FrameAI install. Set FRAMEAI_HOME=<other-path>."
  exit 3
else
  green "→ cloning into $TARGET"
  git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$TARGET"
  cd "$TARGET"
fi

bash setup.sh

echo
green "FrameAI ready at $TARGET"
cat <<TXT

Next steps (no terminal needed):
  1. Open Claude Code (already installed)
  2. From the File menu, open this folder: $TARGET
     (or: cd $TARGET && claude)
  3. Drag files into the chat + type natural language. Example:
     "이 변경 사항으로 ECN 작성해줘" + spec.pdf

To update later (from inside Claude Code chat):
  /frameai-update
  (or just say "FrameAI 업데이트해줘")

For in-house deployment + Bedrock 서울 리전 라우팅, read:
  $TARGET/docs/security.md
TXT
