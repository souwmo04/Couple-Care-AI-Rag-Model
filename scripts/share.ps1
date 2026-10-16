<#
.SYNOPSIS
  Share CoupleCare AI from this PC with a public link.
.DESCRIPTION
  Builds the website, starts the backend on 127.0.0.1:7860 serving both the website and the API, and opens a
  public tunnel to it. The link works while this window is open and your PC is on. Ctrl+C stops sharing.

  - Fixed link without a warning page (recommended): put SHARE_PAGES_REPO=yourname/repository in .env (a public
    GitHub repository, e.g. this project's). Each start opens a Cloudflare quick tunnel and publishes its address
    to that repository's gh-pages branch (only share-page/ and link.json; override with SHARE_PAGES_BRANCH), so
    friends always use https://yourname.github.io/repository/ once GitHub Pages serves that branch. When sharing
    stops, the page shows that CoupleCare is offline.
  - Fixed link with ngrok (free account, shows an ngrok notice page): NGROK_AUTHTOKEN and NGROK_DOMAIN in .env.
  - Otherwise: a Cloudflare quick tunnel (no account); its https://....trycloudflare.com link changes every time.

  The tunnel program is downloaded once into .cache\tools in this project (nothing is installed elsewhere).
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

# 1. Tunnel program, kept inside the project folder.
$tools = Join-Path $Root '.cache\tools'
New-Item -ItemType Directory -Force $tools | Out-Null
$dotenv = @{}
$envFile = Join-Path $Root '.env'
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^\s*(NGROK_AUTHTOKEN|NGROK_DOMAIN|SHARE_PAGES_REPO|SHARE_PAGES_BRANCH)\s*=\s*"?([^"#\s]+)"?') {
            $dotenv[$Matches[1]] = $Matches[2]
        }
    }
}
$pagesRepo = $dotenv['SHARE_PAGES_REPO']
if ($pagesRepo -and $pagesRepo -notmatch '^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$') { throw 'SHARE_PAGES_REPO must look like yourname/couplecare' }
$useNgrok = -not $pagesRepo -and $dotenv.ContainsKey('NGROK_AUTHTOKEN') -and $dotenv.ContainsKey('NGROK_DOMAIN')
if ($pagesRepo) {
    $pagesOwner, $pagesName = $pagesRepo.Split('/')
    $pagesOwner = $pagesOwner.ToLower()
    $pagesUrl = "https://$pagesOwner.github.io/$pagesName/"
    $pagesBranch = if ($dotenv['SHARE_PAGES_BRANCH']) { $dotenv['SHARE_PAGES_BRANCH'] } else { 'gh-pages' }
    if ($pagesBranch -notmatch '^[A-Za-z0-9._/-]+$' -or $pagesBranch -in @('main', 'master')) {
        throw 'SHARE_PAGES_BRANCH must be a separate branch such as gh-pages (never main/master).'
    }
}

# Publish the current tunnel address (or $null = offline) to the GitHub Pages repository.
function Publish-Link([string]$Link) {
    $ErrorActionPreference = 'Continue'
    $dir = Join-Path $Root '.cache\share-pages'
    # A small separate checkout holding only the pages branch (never the project's code or history).
    if (-not (Test-Path (Join-Path $dir '.git'))) {
        New-Item -ItemType Directory -Force $dir | Out-Null
        git -C $dir init --quiet 2>&1 | Out-Null
        git -C $dir remote add origin "https://github.com/$pagesRepo.git" 2>&1 | Out-Null
        git -C $dir checkout --quiet --orphan $pagesBranch 2>&1 | Out-Null
    }
    # Commit as the same person as this project (its identity may be set only for this folder).
    foreach ($key in 'user.name', 'user.email') {
        $value = git -C $Root config $key
        if ($value) { git -C $dir config $key $value }
    }
    git -C $dir fetch --quiet --depth 1 origin $pagesBranch 2>&1 | Out-Null
    if (-not $LASTEXITCODE) { git -C $dir reset --quiet --hard FETCH_HEAD 2>&1 | Out-Null }
    Copy-Item -Path (Join-Path $Root 'share-page\*') -Destination $dir -Recurse -Force
    $json = [ordered]@{ url = $(if ($Link) { $Link } else { $null }); updated = (Get-Date).ToUniversalTime().ToString('o') } |
        ConvertTo-Json -Compress
    [System.IO.File]::WriteAllText((Join-Path $dir 'link.json'), $json, (New-Object System.Text.UTF8Encoding $false))
    git -C $dir add -A 2>&1 | Out-Null
    $msg = if ($Link) { 'CoupleCare is online' } else { 'CoupleCare is offline' }
    git -C $dir commit --quiet -m $msg 2>&1 | Out-Null
    git -C $dir push --quiet origin "HEAD:refs/heads/$pagesBranch" 2>&1 | Out-Null
    if ($LASTEXITCODE) { Write-Warning "Could not update https://github.com/$pagesRepo (check your GitHub login)." }
    elseif ($Link) { Write-Host "Friends' link (ready in about a minute): $pagesUrl" -ForegroundColor Green }
    else { Write-Host 'The friends'' page now shows that CoupleCare is offline.' }
}
if ($useNgrok) {
    $ngrok = Join-Path $tools 'ngrok.exe'
    if (-not (Test-Path $ngrok)) {
        Write-Host 'Downloading ngrok (once) ...' -ForegroundColor Cyan
        $zip = Join-Path $tools 'ngrok.zip'
        Invoke-WebRequest -Uri 'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip' -OutFile $zip -UseBasicParsing
        Expand-Archive -Path $zip -DestinationPath $tools -Force
        Remove-Item $zip
    }
    # Own config file in the project (ngrok would otherwise write one under AppData on C:).
    $ngrokConfig = Join-Path $tools 'ngrok.yml'
    if (-not (Test-Path $ngrokConfig)) { Set-Content -Path $ngrokConfig -Value 'version: "3"' -Encoding ascii }
    $domain = $dotenv['NGROK_DOMAIN'] -replace '^https?://', '' -replace '/.*$', ''
} else {
    $cf = Join-Path $tools 'cloudflared.exe'
    if (-not (Test-Path $cf)) {
        Write-Host 'Downloading cloudflared (once) ...' -ForegroundColor Cyan
        $src = 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe'
        Invoke-WebRequest -Uri $src -OutFile $cf -UseBasicParsing
    }
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
# The GitHub Pages page checks /api/health before sending friends on, so it must be allowed to ask.
if ($pagesRepo) { $env:COUPLECARE_CORS_ORIGINS = "[""https://$pagesOwner.github.io""]" }
$published = $false
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
    if ($pagesRepo) {
        Write-Host "Starting the tunnel; friends' link: $pagesUrl" -ForegroundColor Green
    } elseif ($useNgrok) {
        Write-Host "Your link: https://$domain" -ForegroundColor Green
    } else {
        Write-Host 'Opening the public link. Look for the line with https://....trycloudflare.com below.' -ForegroundColor Green
    }
    Write-Host 'Keep this window open while friends use it. Ctrl+C stops sharing.' -ForegroundColor Green
    Write-Host ''
    $ErrorActionPreference = 'Continue'  # tunnel programs log to stderr
    if ($useNgrok) {
        $env:NGROK_AUTHTOKEN = $dotenv['NGROK_AUTHTOKEN']
        & $ngrok http "http://127.0.0.1:$Port" --url "https://$domain" --config $ngrokConfig --log stdout 2>&1 |
            ForEach-Object { "$_" }
    } else {
        & $cf tunnel --no-autoupdate --url "http://127.0.0.1:$Port" 2>&1 | ForEach-Object {
            $line = "$_"
            $line
            if ($pagesRepo -and -not $published -and $line -match 'https://(?!api\.)[a-z0-9-]+\.trycloudflare\.com') {
                $published = $true
                Publish-Link $Matches[0]
            }
        }
    }
}
finally {
    if (-not $backend.HasExited) { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue }
    if ($published) { Publish-Link $null }
    Write-Host 'Sharing stopped.'
}
