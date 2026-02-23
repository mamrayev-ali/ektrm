param(
  [Parameter(Mandatory=$true)]
  [ValidateSet("local","smoke","ci","detect")]
  [string]$Mode
)

$ErrorActionPreference = "Stop"

function Fail($msg) {
  Write-Host "[ERROR] $msg" -ForegroundColor Red
  exit 1
}

function Info($msg) {
  Write-Host "[INFO]  $msg" -ForegroundColor Cyan
}

function Ok($msg) {
  Write-Host "[OK]    $msg" -ForegroundColor Green
}

# --- Hard stop: forbid fake/placeholder verification scaffolds ---
$forbidden = @(
  ".agentkit/scripts/verify_contract.py",
  "services/api/scripts/placeholder_checks.py",
  "frontend/scripts/placeholder-task.cjs"
)

foreach ($p in $forbidden) {
  if (Test-Path $p) {
    Fail "Forbidden placeholder verification artifact detected: $p. Remove it and restore real toolchain-based verification."
  }
}

# --- Required tools (fail fast, no bypass) ---
function RequireCmd($name, $hint) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    Fail "Missing required tool: $name. $hint"
  }
}

# Always need git + python + make
RequireCmd git "Install Git for Windows."
RequireCmd python "Install Python 3.13+ and ensure 'python' is on PATH."
RequireCmd make "Install GNU Make (e.g., via Chocolatey) OR run verify.sh from Git Bash. Recommended: install 'make' for Windows."

if ($Mode -ne "detect") {
  # For local/smoke/ci we require real toolchains; no placeholder passes.
  RequireCmd uv   "Install uv (recommended) and ensure it is on PATH."
  RequireCmd node "Install Node.js 20+ and ensure it is on PATH."
  RequireCmd pnpm "Install pnpm and ensure it is on PATH."
}

Info "Running verification mode: $Mode"
Info "Repo root: $(Get-Location)"

switch ($Mode) {
  "detect" {
    make detect
    Ok "detect completed"
  }
  "smoke" {
    # Fast subset (still real). Adjust targets later as your repo grows.
    make verify-smoke
    Ok "verify-smoke passed"
  }
  "local" {
    make verify-local
    Ok "verify-local passed"
  }
  "ci" {
    make verify-ci
    Ok "verify-ci passed"
  }
}