<#
.SYNOPSIS
    FrameAI setup for Windows — run once after `git clone` (or after `frame update`).
    Idempotent: re-running is safe.

.DESCRIPTION
    Mirrors setup.sh on macOS/Linux. Windows-specific details:
    - Uses Junction (directory link, no admin needed) instead of symlinks
      so .claude\skills, .claude\agents, .claude\hooks work without
      Developer Mode.
    - Python is assumed to be `python` (not `python3`) per Windows convention.

.NOTES
    Exit codes:
      0 = success
      2 = missing prerequisite
      3 = lint / smoke test failed
#>

#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$Root = $PSScriptRoot
Set-Location $Root

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

# --- 1. Prerequisites -----------------------------------------------------
$missing = $false
foreach ($cmd in @('git', 'claude', 'python')) {
    if (-not (Test-CommandExists $cmd)) {
        Write-Host "[X] missing: $cmd" -ForegroundColor Red
        $missing = $true
    }
}
if ($missing) { exit 2 }

$pyVer = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pyMajor, $pyMinor = $pyVer.Split('.')
if ([int]$pyMajor -lt 3 -or ([int]$pyMajor -eq 3 -and [int]$pyMinor -lt 11)) {
    Write-Host "[X] Python 3.11+ required, found $pyVer" -ForegroundColor Red
    exit 2
}
$claudeVer = (& claude --version 2>&1) | Select-Object -First 1
Write-Host "[OK] prerequisites: python $pyVer, claude $claudeVer, git" -ForegroundColor Green

# --- 1b. Python runtime deps (pyyaml + mcp for the MCP server) -----------
function Ensure-PyModule {
    param([string]$Mod, [string]$Pkg)
    & python -c "import $Mod" 2>$null
    if ($LASTEXITCODE -eq 0) { return $true }
    Write-Host "  installing $Pkg (one-time, user site)..." -ForegroundColor Yellow
    & python -m pip install --user --quiet $Pkg *>$null
    return ($LASTEXITCODE -eq 0)
}

if (-not (Ensure-PyModule 'yaml' 'pyyaml')) {
    Write-Host "[X] pyyaml install failed — install manually and re-run" -ForegroundColor Red
    exit 2
}
if (-not (Ensure-PyModule 'mcp' 'mcp')) {
    Write-Host "  (mcp install skipped — Claude Desktop bridge will be inactive)" -ForegroundColor Yellow
}
Write-Host "[OK] python deps (pyyaml, mcp)" -ForegroundColor Green

# --- 3. .claude\ layout (Windows junctions instead of symlinks) -----------
# (NOTE: git credential helper is NOT auto-installed.
#  End users only run /skills — no push needed.
#  Automation authors who want to push: see README "자동화 작성자 — push
#  인증" for the manual one-liner that uses YOUR username, not someone
#  else's hardcoded identifier.)
if (-not (Test-Path .claude)) {
    New-Item -ItemType Directory -Path .claude | Out-Null
}

function Ensure-Junction {
    param([string]$LinkPath, [string]$TargetPath)
    $absTarget = (Resolve-Path $TargetPath).Path
    if (Test-Path $LinkPath) {
        $item = Get-Item $LinkPath -Force
        if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            return  # already a junction / symlink
        }
        Write-Host "  warning: $LinkPath exists but is not a junction — leaving it alone" -ForegroundColor Yellow
        return
    }
    if ((Get-Item $absTarget).PSIsContainer) {
        New-Item -ItemType Junction -Path $LinkPath -Target $absTarget | Out-Null
    }
}

Ensure-Junction ".claude\skills"  "skills"
Ensure-Junction ".claude\agents"  "agents"
Ensure-Junction ".claude\hooks"   "project\.claude\hooks"

if (-not (Test-Path ".claude\settings.json")) {
    Copy-Item "project\.claude\settings.snippet.json" ".claude\settings.json"
}
Write-Host "[OK] .claude\ layout (skills, agents, hooks, settings.json)" -ForegroundColor Green

# --- 4. Regenerate SKILL.md from templates --------------------------------
& python scripts\gen_skills.py *>$null
Write-Host "[OK] skills regenerated" -ForegroundColor Green

# --- 5. Smoke test --------------------------------------------------------
& python scripts\lint_skill_cache_order.py *>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] skill-cache lint passes" -ForegroundColor Green
}
else {
    Write-Host "[X] skill-cache lint failed — run: python scripts\lint_skill_cache_order.py" -ForegroundColor Red
    exit 3
}

& python -m pytest -q tests\test_lint_skill_cache_order.py tests\test_gen_skills.py tests\test_has_skill.py *>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] smoke tests pass" -ForegroundColor Green
}
else {
    Write-Host "  warning: smoke tests failed — re-run: python -m pytest -q" -ForegroundColor Yellow
}

# --- 6. Claude Desktop MCP registration ----------------------------------
function Register-ClaudeDesktop {
    $configDir = Join-Path $env:APPDATA "Claude"
    if (-not (Test-Path $configDir)) {
        Write-Host "  (Claude Desktop not detected — skipping MCP registration. Install Desktop and re-run setup.ps1 to enable.)" -ForegroundColor Yellow
        return
    }
    & python -c "import mcp" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  (mcp package missing — skipping Claude Desktop registration. Install with: python -m pip install --user mcp)" -ForegroundColor Yellow
        return
    }

    $configFile = Join-Path $configDir "claude_desktop_config.json"
    $serverPath = Join-Path $Root "scripts\frameai_mcp_server.py"
    $pyPath = (Get-Command python).Source

    $tmpScript = New-TemporaryFile
    @'
import json, sys
from pathlib import Path

cfg_path = Path(sys.argv[1])
server_path = sys.argv[2]
py = sys.argv[3]

if cfg_path.exists():
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("  X existing claude_desktop_config.json is malformed -- skipping (manual fix required)", file=sys.stderr)
        sys.exit(0)
    if not isinstance(data, dict):
        data = {}
else:
    data = {}

data.setdefault("mcpServers", {})
new_entry = {"command": py, "args": [server_path]}
prev = data["mcpServers"].get("frameai")

if prev == new_entry:
    print(f"  OK Claude Desktop MCP already registered (no change): {cfg_path}")
else:
    data["mcpServers"]["frameai"] = new_entry
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  OK Claude Desktop MCP registered: {cfg_path}")
    print("    Restart Claude Desktop to load FrameAI skills.")
'@ | Set-Content -Path $tmpScript -Encoding UTF8

    & python $tmpScript $configFile $serverPath $pyPath
    Remove-Item $tmpScript -Force
}

Register-ClaudeDesktop

Write-Host ""
Write-Host "FrameAI setup complete." -ForegroundColor Green
@"

Next steps:
  - Open Claude Code in this folder:    cd "$Root"; claude
  - List available slash commands:      claude --print "/help"
  - Build a new automation:             .\frame add "<one paragraph>"
  - List built automations:             .\frame list
  - Pull latest skills/agents:          .\frame update

For team-internal deployment, see docs\security.md before exposing this
repo to sensitive workflows.
"@
