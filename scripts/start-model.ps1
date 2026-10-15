<#
.SYNOPSIS
  Start the local llama.cpp model server on 127.0.0.1:18080 with a fresh random API key.

.EXAMPLE
  scripts\start-model.ps1                 # full GPU offload, 8k context
  scripts\start-model.ps1 -GpuLayers 20   # partial offload if VRAM is tight
  scripts\start-model.ps1 -Cpu            # CPU only (slow, but works without a GPU)
  scripts\start-model.ps1 -ModelFile Qwen3.5-4B-Q4_K_M.gguf   # another GGUF in models\ (comparisons)
#>
[CmdletBinding()]
param(
    [int]$GpuLayers = 99,
    [int]$Context = 8192,
    [int]$Port = 18080,
    [switch]$Cpu,
    # A GGUF file name inside models\ (defaults to the verified model in models\model.json).
    [string]$ModelFile,
    # Thinking/reasoning output. 'off' gives direct answers (the app is designed for non-thinking models).
    [ValidateSet('off', 'on', 'auto')][string]$Reasoning = 'off',
    # Server-side default presence penalty (0 = off). Some models (e.g. Qwen3.5) recommend 1.5 to curb repetition.
    [ValidateRange(0.0, 2.0)][double]$PresencePenalty = 0
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $Root 'models\model.json'
if (-not (Test-Path $configPath)) {
    throw 'models\model.json not found. Run scripts\download-model.ps1 first.'
}
$cfg = Get-Content $configPath -Raw | ConvertFrom-Json
if (-not (Test-Path $cfg.server)) { throw "llama-server not found at $($cfg.server)" }
$modelPath = $cfg.model
if ($ModelFile) {
    if ($ModelFile -notmatch '^[A-Za-z0-9._-]+\.gguf$') { throw '-ModelFile must be a plain .gguf file name inside models' }
    $modelPath = Join-Path $Root "models\$ModelFile"
}
if (-not (Test-Path $modelPath)) { throw "Model file not found at $modelPath" }

# Windows (Hyper-V/WSL) reserves TCP port ranges; binding inside one fails with a confusing error.
$reserved = netsh interface ipv4 show excludedportrange protocol=tcp | Select-String '^\s*(\d+)\s+(\d+)' | ForEach-Object {
    [pscustomobject]@{ Start = [int]$_.Matches[0].Groups[1].Value; End = [int]$_.Matches[0].Groups[2].Value }
}
$hit = $reserved | Where-Object { $Port -ge $_.Start -and $Port -le $_.End } | Select-Object -First 1
if ($hit) {
    throw "Port $Port is reserved by Windows ($($hit.Start)-$($hit.End)). Use -Port with another value and set COUPLECARE_LLM_BASE_URL to match."
}

# A new random API key on every start. Only the CoupleCare backend reads it (models\server.key),
# so web pages open in the browser cannot use the local model server.
$keyFile = Join-Path $Root 'models\server.key'
$bytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
[System.IO.File]::WriteAllText($keyFile, (($bytes | ForEach-Object { $_.ToString('x2') }) -join ''))

$logs = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$ngl = if ($Cpu) { 0 } else { $GpuLayers }
$serverArgs = @(
    '-m', ('"{0}"' -f $modelPath),  # quoted: Start-Process does not quote paths with spaces
    '--host', '127.0.0.1', '--port', "$Port",
    '-c', "$Context",
    '-ngl', "$ngl",
    '--jinja',
    '--reasoning', $Reasoning,
    '--presence-penalty', ([string]::Format([cultureinfo]::InvariantCulture, '{0}', $PresencePenalty)),
    '--parallel', '1',
    '--no-webui',
    '--api-key-file', ('"{0}"' -f $keyFile)
)
Write-Host "Model: $(Split-Path -Leaf $modelPath)"
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
            Write-Host "Model server ready (PID $($proc.Id))." -ForegroundColor Green
            # Verify GPU use from the driver, not from log wording (which varies between llama.cpp builds).
            $onGpu = (& nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>$null) -match "^\s*$($proc.Id)\s*$"
            $vram = (& nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>$null)
            if ($onGpu) { Write-Host "  Running on the GPU (VRAM in use: $vram)" }
            elseif ($ngl -gt 0) { Write-Warning 'llama-server is not listed as a GPU process; it may be running on the CPU. Check the NVIDIA driver and the CUDA build.' }
            return
        }
    } catch { }
}
throw 'The model server did not become ready within 3 minutes. See logs\model-server.err.log'
