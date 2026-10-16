<#
.SYNOPSIS
  Share CoupleCare AI from this PC with a temporary public link (Cloudflare quick tunnel, free, no account).
.DESCRIPTION
  Builds the website, starts the backend on 127.0.0.1:7860 serving both the website and the API, and opens a
  Cloudflare quick tunnel to it. The https://....trycloudflare.com link is printed below; it works while this
  window is open and changes every time. cloudflared.exe is downloaded once into .cache\tools in this project.
  Press Ctrl+C to stop sharing (the backend is stopped too).
.EXAMPLE
  scripts\share.ps1
.EXAMPLE
  scripts\share.ps1 -SkipBuild
#>
[CmdletBinding()]
param([int]$Port = 7860, [switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Py = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Py)) { throw 'Virtual environment not found. Run scripts\setup.ps1 first.' }

# 1. cloudflared, kept inside the project folder.
$tools = Join-Path $Root '.cache\tools'
$cf = Join-Path $tools 'cloudflared.exe'
if (-not (Test-Path $cf)) {
    New-Item -ItemType Directory -Force $tools | Out-Null
    Write-Host 'Downloading cloudflared (once) ...' -ForegroundColor Cyan
    $src = 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe'
    Invoke-WebRequest -Uri $src -OutFile $cf -UseBasicParsing
}

# 2. Website build.
$dist = Join-Path $Root 'frontend\dist'
if (-not $SkipBuild -or -not (Test-Path (Join-Path $dist 'index.html'))) {
    Write-Host 'Building the website ...' -ForegroundColor Cyan
    Push-Location (Join-Path $Root 'frontend')
    # npm writes warnings to stderr; do not let PowerShell treat them as errors (the exit code decides).
    $ErrorActionPreference = 'Continue'
    try { npm run build 2>&1 | ForEach-Object { "$_" } } finally { Pop-Location; $ErrorActionPreference = 'Stop' }
    if ($LASTEXITCODE) { throw 'Website build failed.' }
}

# 3. Backend serving website + API on one port.
$env:COUPLECARE_FRONTEND_DIST = $dist
$logs = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force $logs | Out-Null
$backend = Start-Process -FilePath $Py -PassThru -WindowStyle Hidden `
    -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--app-dir', 'backend', '--host', '127.0.0.1', '--port', "$Port") `
    -RedirectStandardOutput (Join-Path $logs 'share-backend.out.log') `
    -RedirectStandardError (Join-Path $logs 'share-backend.err.log')
try {
    Write-Host 'Starting the app ...' -ForegroundColor Cyan
    $ok = $false
    for ($i = 0; $i -lt 90 -and -not $ok; $i++) {
        Start-Sleep -Seconds 2
        if ($backend.HasExited) { throw 'The backend stopped. See logs\share-backend.err.log' }
        try { $ok = (Invoke-WebRequest "http://127.0.0.1:$Port/api/health" -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200 } catch { }
    }
    if (-not $ok) { throw 'The backend did not start in time. See logs\share-backend.err.log' }

    # 4. Public link.
    Write-Host ''
    Write-Host 'Opening the public link. Look for the line with https://....trycloudflare.com below.' -ForegroundColor Green
    Write-Host 'Keep this window open while friends use it. Ctrl+C stops sharing.' -ForegroundColor Green
    Write-Host ''
    $ErrorActionPreference = 'Continue'  # cloudflared logs to stderr
    & $cf tunnel --no-autoupdate --url "http://127.0.0.1:$Port" 2>&1 | ForEach-Object { "$_" }
}
finally {
    if (-not $backend.HasExited) { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue }
    Write-Host 'Sharing stopped.'
}
