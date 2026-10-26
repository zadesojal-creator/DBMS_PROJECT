# StockTrade v2 - Database Backup & Recovery PowerShell Script
# Usage:
#   .\backup_db.ps1 -Action backup
#   .\backup_db.ps1 -Action drill

param (
    [ValidateSet("backup", "restore", "verify", "drill")]
    [string]$Action = "backup",
    [string]$SourceDb = "stocktrade",
    [string]$TargetDb = "stocktrade_test",
    [string]$File = "",
    [int]$Keep = 5
)

$ErrorActionPreference = "Stop"
$PythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " StockTrade DBMS: Automated Backup & Recovery Engine" -ForegroundColor Cyan
Write-Host " Action: $Action | Database: $SourceDb" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$CmdArgs = @("database/backup_manager.py", "--action", $Action, "--source-db", $SourceDb, "--target-db", $TargetDb, "--keep", $Keep)

if ($File -ne "") {
    $CmdArgs += @("--file", $File)
}

& $PythonExe @CmdArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] Operation '$Action' completed successfully." -ForegroundColor Green
} else {
    Write-Host "`n[ERROR] Operation '$Action' failed with exit code $LASTEXITCODE." -ForegroundColor Red
    exit $LASTEXITCODE
}
