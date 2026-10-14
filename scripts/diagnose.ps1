<#
.SYNOPSIS
  Check the CoupleCare environment (Python, Node, dependencies, index, model server, GPU).
#>
$Root = Split-Path -Parent $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
& (Join-Path $Root ".venv\Scripts\python.exe") (Join-Path $PSScriptRoot "diagnose.py")
exit $LASTEXITCODE
