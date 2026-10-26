# StockTrade Quick Database Query Helper (query_db.ps1)
# Usage: .\query_db.ps1 "SELECT symbol, current_price FROM Current_Prices LIMIT 10;"

param(
    [string]$Query = "SHOW TABLES;"
)

$MysqlExe = "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"

if (-not (Test-Path $MysqlExe)) {
    $MysqlExe = "C:\Program Files\MySQL\MySQL Server 9.7\bin\mysql.exe"
}

Write-Host "`n[Executing SQL Query on 'stocktrade']" -ForegroundColor Cyan
Write-Host "Query: $Query`n" -ForegroundColor Gray

& $MysqlExe -u root -proot stocktrade -t -e "$Query"
