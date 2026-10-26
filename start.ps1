# StockTrade One-Click Startup Script (start.ps1)
# Starts the StockTrade simulated trading platform (Flask backend + Market Simulator + React UI)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting StockTrade Simulated Trading Platform" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$PythonExe = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Virtual environment not found. Please setup .venv." -ForegroundColor Red
    exit 1
}

# Verify React frontend build exists
$DistIndex = ".\static\dist\index.html"
if (-not (Test-Path $DistIndex)) {
    Write-Host "[INFO] Compiled React frontend not found. Building with Vite..." -ForegroundColor Yellow
    Push-Location ".\frontend"
    npm run build
    Pop-Location
}

Write-Host "[INFO] Starting Flask 3 application with autonomous market simulator..." -ForegroundColor Green
Write-Host "[INFO] Open your browser at: http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host "[INFO] Evaluation Logins:" -ForegroundColor White
Write-Host "  - Admin:            admin / Admin@StockTrade2026 (or DemoPassword123!)" -ForegroundColor Gray
Write-Host "  - Broker Arun:      broker_arun / Broker@StockTrade2026 (or DemoPassword123!)" -ForegroundColor Gray
Write-Host "  - Broker Priya:     broker_priya / Broker@StockTrade2026 (or DemoPassword123!)" -ForegroundColor Gray
Write-Host "  - Investor Rahul:   investor_rahul / Investor@StockTrade2026 (or DemoPassword123!)" -ForegroundColor Gray
Write-Host "  - Investor Sneha:   investor_sneha / Investor@StockTrade2026 (or DemoPassword123!)" -ForegroundColor Gray
Write-Host "  - Direct Rohit:     investor_rohit / Investor@StockTrade2026 (or DemoPassword123!)" -ForegroundColor Gray

& $PythonExe app.py
