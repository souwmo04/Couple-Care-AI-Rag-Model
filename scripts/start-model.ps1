<#
.SYNOPSIS
  Start the local llama.cpp model server on 127.0.0.1:8080.

.EXAMPLE
  scripts\start-model.ps1                 # full GPU offload, 4k context
  scripts\start-model.ps1 -GpuLayers 20   # partial offload if VRAM is tight
  scripts\start-model.ps1 -Cpu            # CPU only (slow, but works without a GPU)
#>
[CmdletBinding()]
param(
    [int]$GpuLayers = 99,
    [int]$Context = 4096,
    [int]$Port = 8080,
    [switch]$Cpu
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $Root 'models\model.json'
if (-not (Test-Path $configPath)) {
    throw 'models\model.json not found. Run scripts\download-model.ps1 first.'
}
$cfg = Get-Content $configPath -Raw | ConvertFrom-Json
if (-not (Test-Path $cfg.server)) { throw "llama-server not found at $($cfg.server)" }
if (-not (Test-Path $cfg.model)) { throw "Model file not found at $($cfg.model)" }

$logs = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$ngl = if ($Cpu) { 0 } else { $GpuLayers }
$serverArgs = @(
    '-m', $cfg.model,
    '--host', '127.0.0.1', '--port', "$Port",
    '-c', "$Context",
    '-ngl', "$ngl",
    '--jinja',
    '--parallel', '1',
    '--no-webui'
)
Write-Host "Starting llama-server (GPU layers: $ngl, context: $Context) on http://127.0.0.1:$Port ..."
$proc = Start-Process -FilePath $cfg.server -ArgumentList $serverArgs -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs 'model-server.out.log') `
    -RedirectStandardError (Join-Path $logs 'model-server.err.log')
$proc.Id | Set-Content (Join-Path $logs 'model-server.pid')

# Wait for the model to load (llama-server returns 503 while loading).
$deadline = (Get-Date).AddMinutes(3)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    if ($proc.HasExited) {
        Write-Host (Get-Content (Join-Path $logs 'model-server.err.log') -Tail 30 | Out-String)
        throw 'llama-server exited during startup. If the log mentions out of memory, try -GpuLayers 20 or -Context 2048.'
    }
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) {
            $offload = Select-String -Path (Join-Path $logs 'model-server.err.log') -Pattern 'offloaded \d+/\d+ layers to GPU' | Select-Object -Last 1
            Write-Host "Model server ready (PID $($proc.Id))." -ForegroundColor Green
            if ($offload) { Write-Host "  $($offload.Line.Trim())" } else { Write-Host '  GPU offload not reported in the log - check logs\model-server.err.log' }
            return
        }
    } catch { }
}
throw 'The model server did not become ready within 3 minutes. See logs\model-server.err.log'
