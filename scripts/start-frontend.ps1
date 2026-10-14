<#
.SYNOPSIS
  Start the Vite dev server on http://127.0.0.1:5173 (foreground; Ctrl+C to stop).
#>
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $Root 'frontend')
if (-not (Test-Path node_modules)) { throw 'Frontend dependencies missing. Run scripts\setup.ps1 first.' }
npm run dev
