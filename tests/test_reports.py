"""
Tests for CSV Reports & CSV Formula Injection Protection (tests/test_reports.py)
"""
import pytest
from routes.reports import sanitize_csv_cell

def test_csv_formula_injection_sanitization():
    """Verify malicious formulas beginning with =, +, -, @ are properly escaped with leading quote."""
    dangerous_inputs = [
        "=cmd|'/C calc'!A0",
        "+1+2",
        "-500",
        "@SUM(A1:A10)",
        "\tmalicious_tab",
        "\rmalicious_cr"
    ]
    for inp in dangerous_inputs:
        sanitized = sanitize_csv_cell(inp)
        assert sanitized.startswith("'"), f"Failed to sanitize {inp}, got {sanitized}"

    safe_inputs = [
        "RELIANCE",
        "BUY",
        "100",
        "2450.50",
        "Regular Investor Name"
    ]
    for inp in safe_inputs:
        sanitized = sanitize_csv_cell(inp)
        assert not sanitized.startswith("'"), f"Unnecessarily escaped safe input: {inp}"

def test_transactions_csv_export_endpoint(investor_client):
    """Verify transactions CSV download endpoint returns valid CSV headers and content."""
    res = investor_client.get("/api/v1/reports/transactions-csv")
    assert res.status_code == 200
    assert "text/csv" in res.content_type
    assert "Content-Disposition" in res.headers
    assert "stocktrade_transactions.csv" in res.headers["Content-Disposition"]

    # Verify CSV structure
    csv_text = res.get_data(as_text=True)
    lines = csv_text.strip().splitlines()
    assert len(lines) >= 1
    headers = lines[0]
    assert "Transaction ID" in headers
    assert "Symbol" in headers
    assert "Gross Amount" in headers
    assert "Brokerage Fee" in headers
