# StockTrade v2 — Glossary & Safe Maintenance Guide

This guide establishes the standard financial and technical terminology, critical entry points, safe modification protocols, and debugging workflows for StockTrade v2.

---

## 1. Technical & Financial Glossary

- **National Stock Exchange (NSE) / Bombay Stock Exchange (BSE)**: The primary Indian equity exchanges simulated by the platform.
- **Weighted-Average Cost (WAC)**: The accounting formula used by `sp_execute_trade` to compute the cost basis of accumulated share holdings across multiple purchase orders:
  $$\text{WAC}_{new} = \frac{(Q_{old} \times \text{Avg Cost}_{old}) + (Q_{new} \times P_{exec})}{Q_{old} + Q_{new}}$$
- **Realized Profit / Loss (P&L)**: The net cash gain or loss materialized and booked to `Transactions` upon executing a SELL order:
  $$\text{Realized P\&L} = (P_{exec} - \text{WAC}_{holding}) \times Q_{sold}$$
- **Unrealized Gain / Loss**: The paper profit or loss computed dynamically in `v_investor_portfolio` comparing current market value against cost basis:
  $$\text{Unrealized Gain} = (P_{curr} - \text{WAC}_{holding}) \times Q_{holding}$$
- **Double-Entry Financial Ledger (`Account_Ledger`)**: A permanent, append-only record where every cash balance mutation is accompanied by a signed credit/debit entry, running balance snapshot, and reference ID.
- **Ledger Immutability Trigger**: Database triggers (`trg_ledger_block_update`, `trg_ledger_block_delete`) that raise SQLSTATE `'45000'` signals to forbid any alteration or removal of financial audit entries.
- **MySQL Advisory Lock (`GET_LOCK`)**: A database-level mutex used by `MarketSimulator` (`SELECT GET_LOCK('stocktrade_simulator', 0)`) ensuring that exactly one process in a cluster flushes price ticks to the database.
- **Abstract Syntax Tree (AST)**: A tree representation of SQL syntactic structure parsed by `sqlglot`. Used by `SQLValidator` to reject data mutation statements, Cartesian joins, and unauthorized tables before queries reach MySQL.
- **Tenant Isolation**: An architectural boundary ensuring that Investors can only access their own holdings/trades, Brokers can only access their assigned clients, and database sessions enforce `@current_user_id`.

---

## 2. Critical Maintenance Rules (Non-Negotiable)

1. **Never Bypass `sp_execute_trade` for Orders**:
   - Order execution must always occur inside `sp_execute_trade`. Never perform trade math, balance deductions, or holding increments in Python application code. Database-level ACID atomicity and row locking (`FOR UPDATE`) protect financial invariants.
2. **Never Mutate `Account_Ledger` or `Transactions`**:
   - Never write an `UPDATE` or `DELETE` query against `Account_Ledger`, `Transactions`, `Commissions`, or `Audit_Logs`. Database triggers will reject the operation with a `'45000'` signal.
3. **Never Use Mock Data or Hardcoded Stocks**:
   - All market prices, portfolios, holdings, and transactions must originate from the MySQL database and the running Python market simulator. Never introduce fallbacks that return fake success messages or in-memory dummy objects.
4. **Preserve the Existing Frontend UI & Aesthetic**:
   - The asymmetrical split terminal login screen, glowing status pills, minimalist KPI cards, and Chart.js candlestick charts are verified design requirements. Do not replace the UI with generic dashboard templates or simplify existing views.
5. **Protect Production Credentials & Git History**:
   - Never stage or commit `.env`, `.env.aiven`, `aiven-ca.pem`, or initialization scripts. Keep them excluded via `.gitignore`.
6. **Use Minimal, Targeted Code Changes**:
   - When resolving defects, identify the root cause and apply the smallest safe patch. Avoid unrelated refactoring, aesthetic redesigns, or dependency changes during bug repairs.

---

## 3. Safe Debugging & Verification Workflow

### Step 1: Run the Automated Test Suite (Isolated Test DB)
Always verify application integrity using the dedicated test suite:
```powershell
.\.venv\Scripts\pytest -v
```
All 136 tests must pass before deploying or committing changes.

### Step 2: Verify Frontend Production Build
Confirm the React SPA bundles cleanly with Vite without compilation warnings or missing asset imports:
```powershell
npm --prefix frontend run build
```

### Step 3: Verify Aiven Cloud TLS Connectivity (Read-Only)
To test cloud connectivity against Aiven MySQL without modifying live data:
```powershell
$env:USE_AIVEN = "true"
.\.venv\Scripts\python -c "from config import Config; from models.db import init_db_engines, get_db_connection; init_db_engines(Config);
with get_db_connection() as conn:
    print('Users:', conn.exec_driver_sql('SELECT COUNT(*) FROM Users').scalar())
    print('Stocks:', conn.exec_driver_sql('SELECT COUNT(*) FROM Stocks').scalar())"
```

### Step 4: Verify Live Server Status
Start the local server and simulator, then probe health:
```powershell
.\.venv\Scripts\python app.py
```
In a separate terminal:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/health"
```
Must return HTTP 200 with `status: "healthy"`.

---

## 4. Troubleshooting Runbook

| Symptom | Probable Cause | Diagnostic Command / File | Safe Corrective Action |
| :--- | :--- | :--- | :--- |
| `OperationalError: (1045, "Access denied")` | DB user mismatch (e.g. attempting to connect as `stocktrade_app` instead of `avnadmin` on cloud) | Check `config.py` and `models/db.py` | Ensure `DB_USER` or `DB_ROOT_USER` is configured as `avnadmin` on Aiven. |
| `[SSL: CERTIFICATE_VERIFY_FAILED]` | PyMySQL kwargs overwrite bug or missing Aiven Project CA | Check `models/db.py` | Verify `query_params["ssl_ca"] = db_ssl_ca` is used without passing conflicting `ssl_verify_cert="true"`. |
| `HTTP 500 without JSON` on AI Assistant | Missing `stocktrade_ai_ro` user on cloud database or non-API path in error handler | Check `routes/ai.py` and `app.py` line 101 | Ensure `db_ai_user` falls back to `db_user` on remote hosts and `"/api/" in request.path` returns JSON. |
| `Simulator indicator red / stale` | Simulator singleton not started or advisory lock contested | Check `/market/api/v1/market/status` | Ensure `START_SIMULATOR=true` and only 1 worker process is configured in Gunicorn. |
| `Order rejected: Insufficient funds` | Available cash balance less than trade gross amount + fee | Check `Accounts.virtual_balance` | Submit virtual cash deposit via `/investor/api/v1/investor/deposit` to credit trading account. |
| `Trigger signal 45000: strictly append-only` | Code attempted an `UPDATE` or `DELETE` on `Account_Ledger` or `Transactions` | Check SQL statement | Correct query: accounting entries must be posted as new debit/credit rows, never modified. |
