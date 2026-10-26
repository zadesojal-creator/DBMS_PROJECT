# StockTrade Database Initializer Script (init_db.ps1)
# Provisions databases, schemas, views, triggers, stored procedures, seed users, companies, and 7-day price backfill.

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  StockTrade Database Initializer" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$PythonExe = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Virtual environment not found at .venv. Please create one with Python 3.11+." -ForegroundColor Red
    exit 1
}

Write-Host "[1/2] Initializing MySQL Schemas, Users, Triggers & Stored Procedures..." -ForegroundColor Yellow
& $PythonExe init_db.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] StockTrade database initialized successfully!" -ForegroundColor Green
    Write-Host "Databases provisioned: 'stocktrade' and 'stocktrade_test'" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Database initialization failed. Please check MySQL root credentials in .env." -ForegroundColor Red
    exit 1
}
