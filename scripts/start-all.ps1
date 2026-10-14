<#
.SYNOPSIS
  Start the model server (if downloaded), the backend and the frontend in separate windows.
  The app still runs without a model - it will clearly show "AI generation offline".
#>
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot

if (Test-Path (Join-Path $Root 'models\model.json')) {
    & (Join-Path $PSScriptRoot 'start-model.ps1')
} else {
    Write-Warning 'No model downloaded yet - AI generation will be offline. Run scripts\download-model.ps1.'
}
Start-Process powershell -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $PSScriptRoot 'start-backend.ps1')
Start-Process powershell -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $PSScriptRoot 'start-frontend.ps1')
Write-Host 'Backend: http://127.0.0.1:8000/api/docs   Frontend: http://127.0.0.1:5173' -ForegroundColor Green
