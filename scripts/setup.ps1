<#
.SYNOPSIS
  One-time setup: Python virtual environment, backend dependencies, frontend dependencies, .env.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
#>
[CmdletBinding()]
param(
    [switch]$SkipFrontend
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Require-Command($Name, $Hint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name was not found on PATH. $Hint"
    }
}

Require-Command python 'Install Python 3.11 or 3.12 from https://www.python.org/downloads/ and tick "Add to PATH".'
$pyVersion = (python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')")
if ([version]$pyVersion -lt [version]'3.11') { throw "Python $pyVersion found; 3.11 or newer is required." }
Write-Host "Python $pyVersion OK"

if (-not (Test-Path .venv)) {
    Write-Host 'Creating virtual environment (.venv)...'
    python -m venv .venv
}
$Py = Join-Path $Root '.venv\Scripts\python.exe'

# Keep every download cache inside the project folder, not on the system drive.
$cache = Join-Path $Root '.cache'
New-Item -ItemType Directory -Force -Path (Join-Path $cache 'pip'), (Join-Path $cache 'npm'), (Join-Path $cache 'huggingface') | Out-Null
$env:PIP_CACHE_DIR = Join-Path $cache 'pip'
$env:HF_HOME = Join-Path $cache 'huggingface'
"[global]`ncache-dir = $env:PIP_CACHE_DIR`n" | Set-Content -Encoding ascii (Join-Path $Root '.venv\pip.ini')

& $Py -m pip install --upgrade pip "setuptools>=83"  # older setuptools has known vulnerabilities (pip-audit)
Write-Host 'Installing CPU-only PyTorch (keeps the GPU free for the language model)...'
& $Py -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
Write-Host 'Installing backend dependencies...'
& $Py -m pip install -r requirements-dev.txt

if (-not $SkipFrontend) {
    Require-Command node 'Install Node.js 20 LTS or newer from https://nodejs.org/.'
    Write-Host "Node $(node --version) OK"
    Push-Location frontend
    try { npm ci } finally { Pop-Location }
}

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host 'Created .env from .env.example'
}

Write-Host ''
Write-Host 'Setup complete. Next steps:' -ForegroundColor Green
Write-Host '  1. scripts\download-model.ps1   (downloads llama.cpp + the GGUF model, ~3 GB)'
Write-Host '  2. scripts\build-index.ps1      (builds the local knowledge index)'
Write-Host '  3. scripts\start-all.ps1        (starts model server, backend and frontend)'
