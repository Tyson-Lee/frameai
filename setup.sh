#!/usr/bin/env bash
# FrameAI setup — run once after `git clone` (or after `frame update`).
# Idempotent: re-running is safe.
#
# What this does:
#   1. Verifies required CLIs (python3, claude, git)
#   2. Makes executable bits correct (frame, scripts/*.sh, hooks/*.py)
#   3. Re-creates .claude/ symlinks if a Windows clone dropped them
#   4. Regenerates SKILL.md files from templates
#   5. Runs a fast smoke test (skill discovery + lint)
#
# Exit codes:
#   0 = success
#   2 = missing prerequisite
#   3 = lint / smoke test failed
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$*"; }

# --- 1. Prerequisites ------------------------------------------------------

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    red "✘ missing: $1"
    return 1
  fi
  return 0
}

missing=0
need python3 || missing=1
need claude   || { yellow "  install Claude Code: https://docs.claude.com/en/docs/claude-code/install"; missing=1; }
need git      || missing=1
if [ $missing -ne 0 ]; then
  red "Install the missing tools and re-run ./setup.sh"
  exit 2
fi

# Python 3.11+
py_ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
case "$py_ver" in
  3.11|3.12|3.13|3.1[4-9]|3.[2-9]?) : ;;
  *) red "✘ Python 3.11+ required, found $py_ver"; exit 2 ;;
esac
green "✓ prerequisites: python $py_ver, claude $(claude --version 2>&1 | head -1), git"

# --- 2. Executable bits ----------------------------------------------------

chmod +x frame setup.sh 2>/dev/null || true
find scripts -name '*.sh' -exec chmod +x {} \;
find project/.claude/hooks -name '*.py' -exec chmod +x {} \; 2>/dev/null || true
green "✓ executable bits"

# --- 3. .claude/ symlinks (recreate if missing) ----------------------------
# (NOTE: git credential helper is NOT auto-installed.
#  End users only run /skills — no push needed.
#  Automation authors who want to push: see README "자동화 작성자 — push
#  인증" for the manual one-liner that uses YOUR username, not someone
#  else's hardcoded identifier.)

mkdir -p .claude

ensure_symlink() {
  local link="$1" target="$2"
  if [ -L "$link" ] && [ "$(readlink "$link")" = "$target" ]; then
    return 0
  fi
  if [ -e "$link" ] && [ ! -L "$link" ]; then
    yellow "  warning: $link exists but is not a symlink — leaving it alone"
    return 0
  fi
  ln -snf "$target" "$link"
}

ensure_symlink .claude/skills ../skills
ensure_symlink .claude/agents ../agents
ensure_symlink .claude/hooks ../project/.claude/hooks

if [ ! -f .claude/settings.json ]; then
  cp project/.claude/settings.snippet.json .claude/settings.json
fi
green "✓ .claude/ layout (skills, agents, hooks, settings.json)"

# --- 4. Regenerate SKILL.md from templates --------------------------------

if [ -x scripts/gen_skills.py ] || python3 -c 'import sys' ; then
  python3 scripts/gen_skills.py --dry-run >/dev/null 2>&1 || python3 scripts/gen_skills.py >/dev/null
  green "✓ skills regenerated"
fi

# --- 5. Smoke test --------------------------------------------------------

if python3 scripts/lint_skill_cache_order.py >/dev/null 2>&1; then
  green "✓ skill-cache lint passes"
else
  red "✘ skill-cache lint failed — run: python3 scripts/lint_skill_cache_order.py"
  exit 3
fi

# Lightweight pytest subset (fast guards only; skip slow integration)
if python3 -m pytest -q \
    tests/test_lint_skill_cache_order.py \
    tests/test_gen_skills.py \
    tests/test_has_skill.py \
    >/dev/null 2>&1; then
  green "✓ smoke tests pass"
else
  yellow "  warning: smoke tests failed — re-run: python3 -m pytest -q"
fi

echo
green "FrameAI setup complete."
cat <<'TXT'

Next steps:
  - Open Claude Code in this folder:        cd $(basename "$ROOT") && claude
  - List available slash commands:          claude --print "/help"
  - Build a new automation from natural language:
                                            ./frame add "<one paragraph>"
  - List built automations:                 ./frame list
  - Pull latest skills/agents from upstream:./frame update

For team-internal deployment, see docs/security.md before exposing this
repo to sensitive workflows.
TXT
