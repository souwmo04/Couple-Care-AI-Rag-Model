<#
.SYNOPSIS
  Check Python and npm dependencies for known vulnerabilities (needs an internet connection).
.DESCRIPTION
  pip-audit checks the packages installed in .venv against the PyPA advisory database; its cache is
  kept in .cache\pip-audit inside the project. The CPU build of torch ("2.14.1+cpu") is not on PyPI,
  so it is checked by version separately. npm audit checks frontend dependencies.
#>
# 'Continue': pip-audit reports on stderr, which Windows PowerShell 5.1 would otherwise treat as a fatal
# error. Failures are detected from exit codes instead.
$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Py = Join-Path $Root '.venv\Scripts\python.exe'
$cache = Join-Path $Root '.cache\pip-audit'
$failed = $false

Write-Host '== Python packages (pip-audit) ==' -ForegroundColor Cyan
& $Py -m pip_audit --cache-dir $cache --progress-spinner off
if ($LASTEXITCODE) { $failed = $true }

$torch = (& $Py -c "import importlib.metadata as m; print(m.version('torch').split('+')[0])").Trim()
$req = Join-Path $env:TEMP 'couplecare-torch-audit.txt'
Set-Content -Path $req -Value "torch==$torch" -Encoding ascii
Write-Host "== torch $torch (checked by version) ==" -ForegroundColor Cyan
& $Py -m pip_audit --cache-dir $cache --progress-spinner off -r $req --no-deps --disable-pip
if ($LASTEXITCODE) { $failed = $true }
Remove-Item $req -ErrorAction SilentlyContinue

Write-Host '== Frontend packages (npm audit) ==' -ForegroundColor Cyan
Push-Location (Join-Path $Root 'frontend')
npm audit
if ($LASTEXITCODE) { $failed = $true }
Pop-Location

if ($failed) { Write-Host 'Vulnerabilities found (see above).' -ForegroundColor Red; exit 1 }
Write-Host 'No known vulnerabilities found.' -ForegroundColor Green
