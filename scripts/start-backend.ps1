<#
.SYNOPSIS
  Start the FastAPI backend on 127.0.0.1:8000 (foreground; Ctrl+C to stop).
#>
[CmdletBinding()]
param([int]$Port = 8000, [switch]$Reload)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Py)) { throw 'Virtual environment not found. Run scripts\setup.ps1 first.' }
Set-Location $Root
$extra = @()
if ($Reload) { $extra = @('--reload', '--reload-dir', 'backend') }
& $Py -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $Port @extra
