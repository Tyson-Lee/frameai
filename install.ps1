<#
.SYNOPSIS
    FrameAI installer for Windows — one-line install.

.DESCRIPTION
    Bootstraps FrameAI on Windows by cloning the repo and running setup.ps1.
    Mirrors the behavior of install.sh on macOS/Linux.

.EXAMPLE
    # From Claude Code chat or PowerShell (one-liner):
    irm https://raw.githubusercontent.com/Tyson-Lee/frameai/main/install.ps1 | iex

.EXAMPLE
    # Direct execution with custom install path:
    $env:FRAMEAI_HOME = "$HOME\my-frameai"
    .\install.ps1

.NOTES
    Requirements: git, claude (Claude Code CLI), python (3.11+)
    Optional env: FRAMEAI_HOME, FRAMEAI_REPO_URL, FRAMEAI_BRANCH
#>

#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$Target = if ($env:FRAMEAI_HOME) { $env:FRAMEAI_HOME } else { "$env:USERPROFILE\frameai" }
$RepoUrl = if ($env:FRAMEAI_REPO_URL) { $env:FRAMEAI_REPO_URL } else { 'https://github.com/Tyson-Lee/frameai.git' }
$Branch = if ($env:FRAMEAI_BRANCH) { $env:FRAMEAI_BRANCH } else { 'main' }

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

# --- Prerequisites --------------------------------------------------------
$missing = $false
foreach ($cmd in @('git', 'claude', 'python')) {
    if (-not (Test-CommandExists $cmd)) {
        Write-Host "[X] missing: $cmd" -ForegroundColor Red
        $missing = $true
        if ($cmd -eq 'claude') {
            Write-Host "    install Claude Code: https://docs.claude.com/en/docs/claude-code/install" -ForegroundColor Yellow
        }
    }
}
if ($missing) {
    Write-Host "Install the missing tools and re-run." -ForegroundColor Yellow
    exit 2
}

# --- Clone or update ------------------------------------------------------
if (Test-Path "$Target\.git") {
    Write-Host "FrameAI already installed at $Target. Updating instead..." -ForegroundColor Yellow
    Push-Location $Target
    $status = git status --porcelain
    if ($status) {
        Write-Host "[X] uncommitted changes in $Target — resolve manually or set FRAMEAI_HOME=<other-path>" -ForegroundColor Red
        Pop-Location
        exit 3
    }
    git pull --ff-only origin $Branch
    Pop-Location
}
elseif (Test-Path $Target) {
    Write-Host "[X] $Target exists but is not a FrameAI install. Set FRAMEAI_HOME=<other-path>." -ForegroundColor Red
    exit 3
}
else {
    Write-Host "-> cloning into $Target" -ForegroundColor Green
    git clone --branch $Branch --depth 1 $RepoUrl $Target
}

# --- Run setup.ps1 --------------------------------------------------------
Push-Location $Target
try {
    powershell -ExecutionPolicy Bypass -File .\setup.ps1
}
finally {
    Pop-Location
}

# --- Done ------------------------------------------------------------------
Write-Host ""
Write-Host "FrameAI ready at $Target" -ForegroundColor Green
@"

Next steps (no terminal needed):
  1. Open Claude Code (already installed)
  2. From the File menu, open this folder: $Target
     (or open PowerShell: cd "$Target"; claude)
  3. Drag files into the chat + type natural language. Example:
     "이 변경 사항으로 ECN 작성해줘" + spec.pdf

To update later (from inside Claude Code chat):
  /frameai-update
  (or just say "FrameAI 업데이트해줘")

For in-house deployment + Bedrock Seoul region routing, read:
  $Target\docs\security.md
"@
