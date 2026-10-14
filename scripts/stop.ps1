<#
.SYNOPSIS
  Stop the model server, backend and frontend started by these scripts.
  Only processes listening on the CoupleCare ports (8080, 8000, 5173) on 127.0.0.1 are stopped.
#>
$Root = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $Root 'logs\model-server.pid'
if (Test-Path $pidFile) {
    $id = Get-Content $pidFile
    Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
    Remove-Item $pidFile -Force
    Write-Host "Stopped model server (PID $id)"
}
foreach ($port in 8080, 8000, 5173) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -in @('127.0.0.1', '::1') }
    foreach ($c in $conns) {
        Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped process $($c.OwningProcess) on port $port"
    }
}
