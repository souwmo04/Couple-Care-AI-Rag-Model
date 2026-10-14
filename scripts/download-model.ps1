<#
.SYNOPSIS
  Download a pinned llama.cpp Windows build and a pinned GGUF model into .\models,
  verifying the model's SHA-256 against the value published by Hugging Face.

.DESCRIPTION
  Nothing is downloaded unless you run this script. Model weights carry their own licence:
  Qwen3-4B-Instruct-2507 is Apache-2.0 (see docs/model-selection.md).

.EXAMPLE
  scripts\download-model.ps1                       # CUDA 12.4 build + Q4_K_M (~2.5 GB model)
  scripts\download-model.ps1 -Backend cpu          # CPU-only llama.cpp build
  scripts\download-model.ps1 -Quant Q5_K_M
#>
[CmdletBinding()]
param(
    [ValidateSet('cuda', 'cpu')] [string]$Backend = 'cuda',
    [ValidateSet('Q4_K_M', 'Q5_K_M', 'Q8_0')] [string]$Quant = 'Q4_K_M',
    [string]$LlamaCppTag = 'b11603',
    [string]$Repo = 'unsloth/Qwen3-4B-Instruct-2507-GGUF',
    [string]$Revision = 'a06e946bb6b655725eafa393f4a9745d460374c9'
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # Invoke-WebRequest is much faster without the progress bar
$Root = Split-Path -Parent $PSScriptRoot
$Models = Join-Path $Root 'models'
$LlamaDir = Join-Path $Models 'llama.cpp'
New-Item -ItemType Directory -Force -Path $Models, $LlamaDir | Out-Null

# ---------------------------------------------------------------- llama.cpp
$assets = if ($Backend -eq 'cuda') {
    @("llama-$LlamaCppTag-bin-win-cuda-12.4-x64.zip", 'cudart-llama-bin-win-cuda-12.4-x64.zip')
} else {
    @("llama-$LlamaCppTag-bin-win-cpu-x64.zip")
}
$release = Invoke-RestMethod -Uri "https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/$LlamaCppTag"
foreach ($asset in $assets) {
    $meta = $release.assets | Where-Object { $_.name -eq $asset }
    if (-not $meta) { throw "$asset is not part of llama.cpp release $LlamaCppTag." }
    $url = "https://github.com/ggml-org/llama.cpp/releases/download/$LlamaCppTag/$asset"
    $zip = Join-Path $Models $asset
    if (-not (Test-Path $zip) -or (Get-Item $zip).Length -ne $meta.size) {
        Write-Host ("Downloading {0} ({1} MB) ..." -f $asset, [math]::Round($meta.size / 1MB))
        $venvPy = Join-Path $Root '.venv\Scripts\python.exe'
        if ((Test-Path $venvPy) -and $meta.digest -like 'sha256:*') {
            # Parallel range requests: some networks throttle each GitHub connection to ~100 KB/s.
            & $venvPy (Join-Path $PSScriptRoot 'parallel_download.py') $url $zip --sha256 $meta.digest.Substring(7) --connections 24
            if ($LASTEXITCODE) { throw "Download of $asset failed." }
        } else {
            Invoke-WebRequest -Uri $url -OutFile "$zip.part"
            Move-Item "$zip.part" $zip -Force
        }
    }
    if ($meta.digest -like 'sha256:*') {
        $got = (Get-FileHash -Algorithm SHA256 -Path $zip).Hash.ToLower()
        if ("sha256:$got" -ne $meta.digest) {
            Remove-Item $zip -Force
            throw "Checksum mismatch for $asset; the file was deleted. Re-run the script."
        }
        Write-Host "  checksum OK"
    }
    Write-Host "Extracting $asset ..."
    Expand-Archive -Path $zip -DestinationPath $LlamaDir -Force
}
$server = Get-ChildItem -Path $LlamaDir -Recurse -Filter 'llama-server.exe' | Select-Object -First 1
if (-not $server) { throw 'llama-server.exe was not found in the downloaded archive.' }
Write-Host "llama-server: $($server.FullName)"

# ---------------------------------------------------------------- GGUF model
$file = "Qwen3-4B-Instruct-2507-$Quant.gguf"
$target = Join-Path $Models $file
$meta = Invoke-RestMethod -Uri "https://huggingface.co/api/models/$Repo/revision/${Revision}?blobs=true"
$entry = $meta.siblings | Where-Object { $_.rfilename -eq $file }
if (-not $entry) { throw "$file is not present in $Repo at revision $Revision." }
$expected = $entry.lfs.sha256
if (-not (Test-Path $target)) {
    $sizeGb = [math]::Round($entry.size / 1GB, 2)
    Write-Host "Downloading $file ($sizeGb GB) from $Repo@$($Revision.Substring(0,8)) ..."
    $venvPy = Join-Path $Root '.venv\Scripts\python.exe'
    $modelUrl = "https://huggingface.co/$Repo/resolve/$Revision/$file"
    if (Test-Path $venvPy) {
        & $venvPy (Join-Path $PSScriptRoot 'parallel_download.py') $modelUrl $target --sha256 $expected --connections 8
        if ($LASTEXITCODE) { throw "Download of $file failed." }
    } else {
        Invoke-WebRequest -Uri $modelUrl -OutFile "$target.part"
        Move-Item "$target.part" $target -Force
    }
}
Write-Host 'Verifying SHA-256 ...'
$actual = (Get-FileHash -Algorithm SHA256 -Path $target).Hash.ToLower()
if ($actual -ne $expected) {
    Remove-Item $target -Force
    throw "Checksum mismatch for $file (expected $expected, got $actual). The file was deleted."
}
Write-Host "Checksum OK: $actual" -ForegroundColor Green

@{
    server   = $server.FullName
    model    = $target
    repo     = $Repo
    revision = $Revision
    sha256   = $actual
    llamacpp = $LlamaCppTag
    backend  = $Backend
} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $Models 'model.json')
Write-Host 'Wrote models\model.json. Start the server with scripts\start-model.ps1'
