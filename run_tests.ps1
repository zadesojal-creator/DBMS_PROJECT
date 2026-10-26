# StockTrade Test Suite Runner (run_tests.ps1)
# Executes all 43 unit, integration, concurrency, and security tests with coverage reporting.

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  StockTrade Test Suite Runner (pytest)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$PytestExe = ".\.venv\Scripts\pytest.exe"

if (-not (Test-Path $PytestExe)) {
    Write-Host "[ERROR] pytest not found in .venv. Run 'pip install -r requirements.txt'." -ForegroundColor Red
    exit 1
}

Write-Host "Running 43 test assertions with code coverage..." -ForegroundColor Yellow
& $PytestExe -v --cov=. tests/

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] All test assertions passed with 100% success rate!" -ForegroundColor Green
} else {
    Write-Host "`n[WARNING] Some test assertions failed. See output above for details." -ForegroundColor Red
}
