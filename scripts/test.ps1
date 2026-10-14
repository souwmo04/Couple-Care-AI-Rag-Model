<#
.SYNOPSIS
  Run all automated tests (no model download required).
.EXAMPLE
  scripts\test.ps1               # backend + frontend
  scripts\test.ps1 -Integration  # also run tests that need a running model server / downloaded embedder
#>
[CmdletBinding()]
param([switch]$Integration)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Py = Join-Path $Root '.venv\Scripts\python.exe'
$env:PYTHONIOENCODING = 'utf-8'

Write-Host '== Backend lint (ruff) ==' -ForegroundColor Cyan
& $Py -m ruff check backend scripts
if ($LASTEXITCODE) { exit $LASTEXITCODE }

Write-Host '== Backend tests (pytest) ==' -ForegroundColor Cyan
if ($Integration) { & $Py -m pytest -m 'integration or not integration' } else { & $Py -m pytest }
if ($LASTEXITCODE) { exit $LASTEXITCODE }

Write-Host '== Frontend type check, lint and tests ==' -ForegroundColor Cyan
Push-Location frontend
try {
    npx tsc -b; if ($LASTEXITCODE) { exit $LASTEXITCODE }
    npm run lint; if ($LASTEXITCODE) { exit $LASTEXITCODE }
    npm test; if ($LASTEXITCODE) { exit $LASTEXITCODE }
} finally { Pop-Location }
Write-Host 'All checks passed.' -ForegroundColor Green
