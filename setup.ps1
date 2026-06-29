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

# --- 2. Git credential helper (uses GH_TOKEN env for Tyson-Lee push) ------
if (Test-Path .git) {
    $current = git config --get-all credential.helper 2>$null
    if ($current -notmatch 'Tyson-Lee') {
        git config credential.helper ""
        git config --add credential.helper '!f() { test -n "$GH_TOKEN" && printf "username=Tyson-Lee\npassword=%s\n" "$GH_TOKEN"; }; f'
        Write-Host "[OK] git credential helper installed (uses GH_TOKEN env)" -ForegroundColor Green
        Write-Host "  push pattern:  `$env:GH_TOKEN='<your-PAT>'; git push" -ForegroundColor Yellow
        Write-Host "  or use:        `$env:GH_TOKEN='<your-PAT>'; .\frame share <slug> --push" -ForegroundColor Yellow
        Write-Host "  (Git for Windows ships with bash, so the inline shell helper works.)" -ForegroundColor DarkGray
    }
    else {
        Write-Host "[OK] git credential helper already configured" -ForegroundColor Green
    }
}

# --- 3. .claude\ layout (Windows junctions instead of symlinks) -----------
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
