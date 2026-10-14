<#
.SYNOPSIS
  Build the local knowledge index from data\metadata\sources.json.
.EXAMPLE
  scripts\build-index.ps1               # multilingual E5 embeddings + BM25 (downloads the E5 model on first run)
  scripts\build-index.ps1 -LexicalOnly  # BM25 only
#>
[CmdletBinding()]
param([switch]$LexicalOnly)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONIOENCODING = 'utf-8'
$Py = Join-Path $Root '.venv\Scripts\python.exe'
$a = @('scripts\build_index.py')
if ($LexicalOnly) { $a += '--lexical-only' }
& $Py @a
exit $LASTEXITCODE
