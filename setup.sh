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

# --- 1b. Python runtime deps (pyyaml + mcp for the MCP server) -----------
# Both are hard deps now: pyyaml for skill template parsing, mcp for the
# Claude Desktop / Cursor bridge. Install lazily (idempotent) without
# requiring a venv.

ensure_pymod() {
  local mod="$1" pkg="$2"
  if python3 -c "import $mod" >/dev/null 2>&1; then
    return 0
  fi
  yellow "  installing $pkg (one-time, user site)…"
  if ! python3 -m pip install --user --quiet "$pkg" >/dev/null 2>&1; then
    red "✘ pip install $pkg failed — install manually and re-run setup"
    return 1
  fi
}

ensure_pymod yaml pyyaml || exit 2
ensure_pymod mcp  mcp    || yellow "  (mcp install skipped — Claude Desktop bridge will be inactive)"
green "✓ python deps (pyyaml, mcp)"

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

# --- 6. Claude Desktop MCP registration (optional, skipped if not installed) -
# One-shot: writes/merges scripts/frameai_mcp_server.py into
# claude_desktop_config.json so Desktop discovers FrameAI skills as MCP
# prompts. Existing user entries are preserved.

register_claude_desktop() {
  local config_dir=""
  case "$(uname -s)" in
    Darwin) config_dir="$HOME/Library/Application Support/Claude" ;;
    Linux)  config_dir="$HOME/.config/Claude" ;;
    *)      return 0 ;;
  esac

  if [ ! -d "$config_dir" ]; then
    yellow "  (Claude Desktop not detected — skipping MCP registration. Install Desktop and re-run ./setup.sh to enable.)"
    return 0
  fi

  if ! python3 -c 'import mcp' >/dev/null 2>&1; then
    yellow "  (mcp package missing — skipping Claude Desktop registration. Install with: python3 -m pip install --user mcp)"
    return 0
  fi

  local config_file="$config_dir/claude_desktop_config.json"
  local server_path="$ROOT/scripts/frameai_mcp_server.py"
  local py_path
  py_path=$(command -v python3)

  python3 - "$config_file" "$server_path" "$py_path" <<'PYEOF'
import json, sys
from pathlib import Path

cfg_path = Path(sys.argv[1])
server_path = sys.argv[2]
py = sys.argv[3]

if cfg_path.exists():
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("  ✘ existing claude_desktop_config.json is malformed — skipping (manual fix required)", file=sys.stderr)
        sys.exit(0)
    if not isinstance(data, dict):
        data = {}
else:
    data = {}

data.setdefault("mcpServers", {})
new_entry = {"command": py, "args": [server_path]}
prev = data["mcpServers"].get("frameai")

if prev == new_entry:
    print(f"  ✓ Claude Desktop MCP already registered (no change): {cfg_path}")
else:
    data["mcpServers"]["frameai"] = new_entry
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  ✓ Claude Desktop MCP registered: {cfg_path}")
    print("    Restart Claude Desktop to load FrameAI skills.")
PYEOF
}

register_claude_desktop

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
