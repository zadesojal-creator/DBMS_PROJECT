"""
Reports & CSV Export Blueprint (routes/reports.py)
Hardened against CSV Formula Injection (=, +, -, @ prefix protection).
"""
import csv
import io
from flask import Blueprint, Response, request
from flask_login import current_user, login_required
from services.auth_service import role_required
from repositories.transaction_repo import TransactionRepository
from repositories.broker_repo import BrokerRepository

reports_bp = Blueprint("reports", __name__, url_prefix="/api/v1/reports")

def sanitize_csv_cell(value) -> str:
    """Protects against CSV Formula Injection by prefixing unsafe characters with a single quote."""
    val_str = str(value) if value is not None else ""
    if val_str and val_str[0] in ('=', '+', '-', '@', '\t', '\r'):
        return f"'{val_str}"
    return val_str

@reports_bp.route("/transactions-csv", methods=["GET"])
@login_required
def export_transactions_csv():
    """Exports transaction history for current investor or broker's clients."""
    if current_user.role == "INVESTOR":
        rows = TransactionRepository.get_by_user(current_user.id, limit=5000)
    elif current_user.role == "BROKER":
        rows = TransactionRepository.get_by_broker(current_user.id, limit=5000)
    else: # ADMIN
        rows = TransactionRepository.get_by_user(1, limit=5000)

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Transaction ID", "Date Time", "Symbol", "Side", "Quantity",
        "Execution Price", "Gross Amount", "Brokerage Fee", "Net Amount"
    ])

    for r in rows:
        writer.writerow([
            sanitize_csv_cell(r.get("transaction_id")),
            sanitize_csv_cell(r.get("executed_at")),
            sanitize_csv_cell(r.get("symbol")),
            sanitize_csv_cell(r.get("side")),
            sanitize_csv_cell(r.get("quantity")),
            sanitize_csv_cell(r.get("execution_price")),
            sanitize_csv_cell(r.get("gross_amount")),
            sanitize_csv_cell(r.get("brokerage_fee")),
            sanitize_csv_cell(r.get("net_amount")),
        ])

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=stocktrade_transactions.csv"}
    )
