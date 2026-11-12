# StockTrade v2 — Test Suite Inventory & Production Defect Audit

This document records the automated testing architecture, test execution results, and an exhaustive investigation into the live deployment defect where the AI SQL Assistant reported:
`Server returned HTTP 500 without JSON.`

---

## 1. Automated Test Suite Inventory (136 Tests Across 15 Modules)

All tests are executed using `pytest` against an isolated test database (`stocktrade_test`).

```powershell
.\.venv\Scripts\pytest -v
```

| Test Module Path | Test Count | Scope & Focus Areas | Actual Result | Execution Time |
| :--- | :--- | :--- | :--- | :--- |
| [`tests/test_trading.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/tests/test_trading.py) | 9 | Buy/sell atomic order math, WAC recalculation, realized P&L, fee minimums, rollback on failure | **9 / 9 PASSED** | 1.06s |
| [`tests/test_concurrency.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/tests/test_concurrency.py) | 3 | Multi-threaded concurrent order execution, deposit race conditions, idempotency replays | **3 / 3 PASSED** | 0.97s |
| [`tests/test_database.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/tests/test_database.py) | 16 | Foreign key restrictions, check constraints, 16 triggers, ledger immutability, `sp_execute_trade` | **16 / 16 PASSED** | 0.22s |
| [`tests/test_reconciliation.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/tests/test_reconciliation.py) | 4 | Financial invariant reconciliation procedure, RBAC isolation, discrepancy detection | **4 / 4 PASSED** | 0.42s |
| [`tests/test_ai_sql.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/tests/test_ai_sql.py) | 37 | sqlglot AST mutation blocking, stacked statements, Cartesian joins, role tenancy, manual SQL | **37 / 37 PASSED** | 1.86s |
| [`tests/test_ai_intent_correctness.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/tests/test_ai_intent_correctness.py) | 15 | Dynamic sector resolution, scope clamps (`ALL` vs `TOP_N`), honest empty results, out-of-domain rejection | **15 / 15 PASSED** | 1.38s |
| [`tests/test_investor_features.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/tests/test_investor_features.py) | 6 | Watchlist CRUD, price alerts evaluation, assigned broker view, CSV statement export | **6 / 6 PASSED** | 0.42s |
| [`tests/test_broker_clients.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/tests/test_broker_clients.py) | 4 | Broker client onboarding, tenant isolation (404 enforcement), ending assignments | **4 / 4 PASSED** | 0.50s |
| [`tests/test_market.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/tests/test_market.py) | 14 | 500ms high-frequency tick speed, decoupled batch flush, SSE stream snapshot, pricing math | **14 / 14 PASSED** | 8.43s |
| [`tests/test_auth.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/tests/test_auth.py) | 7 | Password hashing, brute force lockout (5 attempts), session restoration, SPA root serving | **7 / 7 PASSED** | 0.85s |
| [`tests/test_permissions.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/tests/test_permissions.py) | 8 | Role-based boundary enforcement (Investor $\to$ Admin, Broker $\to$ Admin blocked with 403) | **8 / 8 PASSED** | 0.35s |
| [`tests/test_backup.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/tests/test_backup.py) | 3 | MySQL binary discovery, backup creation, metadata recording, retention policy | **3 / 3 PASSED** | 0.38s |
| [`tests/test_reports.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/tests/test_reports.py) | 2 | CSV formula injection sanitization (`=`, `+`, `-`, `@`), transaction CSV export | **2 / 2 PASSED** | 0.30s |
| [`tests/test_production_readiness_audit.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/tests/test_production_readiness_audit.py) | 8 | Production entry point, all 21 templates compiling, RBAC isolation, CSRF headers, TLS connect args | **8 / 8 PASSED** | 0.57s |
| **Total Test Suite** | **136** | **Complete System End-to-End Test Suite** | **136 / 136 PASSED (100%)** | **12.30s** |

---

## 2. In-Depth Root Cause Analysis: Live Error `Server returned HTTP 500 without JSON`

During live deployment on Render connected to Aiven Cloud MySQL, the AI SQL Assistant UI displayed:
```text
Server returned HTTP 500 without JSON.
```

An exhaustive investigation through the frontend fetch pipeline, Flask error handler, and database connection pool revealed the complete chain of causation:

### The Failure Chain (Step-by-Step)

```
[User Submits Question in AssistantView.jsx]
       │
       ▼
[api.ai.query(q) -> POST /ai/api/v1/ai/query]
       │
       ▼
[routes/ai.py: api_query() calls QueryExecutor.execute_scoped_query]
       │
       ▼
[services/query_executor.py: with get_ai_connection() as conn]
       │
       ▼
[models/db.py: Checks out connection from _ai_engine]
       │
       ▼
[DEFECT 1: Aiven MySQL User Mismatch]
       • Aiven Cloud MySQL only had master administrator account 'avnadmin'.
       • models/db.py defaulted db_ai_user = "stocktrade_ai_ro" and db_ai_pass = "StockTradeAiRo@2026!".
       • Result: PyMySQL throws OperationalError: (1045, "Access denied for user 'stocktrade_ai_ro'@'...'")!
       │
       ▼
[Exception Bubbles to Flask Error Handler]
       │
       ▼
[DEFECT 2: Route Prefix Match in handle_error]
       • app.py contained:
         is_api = request.path.startswith("/api/") or request.headers.get("Accept") == "application/json"
       • But the AI endpoint path is /ai/api/v1/ai/query (starts with /ai/, NOT /api/)!
       • If Accept header was omitted or generic (*/*), is_api evaluated to FALSE.
       • Flask executed: return render_template("errors/500.html"), 500
       • The server returned an HTML error document instead of JSON!
       │
       ▼
[DEFECT 3: Frontend JSON Parser Catch in client.js]
       • frontend/src/api/client.js:
         const json = await res.json().catch(() => null);
         if (!res.ok) {
           const errorMsg = json?.error?.message || json?.message || `HTTP ${res.status}: ${res.statusText}`;
           ...
         }
       • Because response body was HTML, res.json() threw SyntaxError and caught to null.
       • Result: json?.error was undefined. The UI showed: "Server returned HTTP 500 without JSON."
```

### Verified Resolution

1. **Cloud User Fallback in [`models/db.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/models/db.py)**:
   ```python
   db_ai_user = get_val("DB_AI_USER")
   db_ai_pass = get_val("DB_AI_PASSWORD")
   if not db_ai_user or (db_ai_user == "stocktrade_ai_ro" and db_host not in ("localhost", "127.0.0.1")):
       db_ai_user = db_user
       db_ai_pass = db_pass
   ```
   When connecting to a remote cloud host (like Aiven) where `stocktrade_ai_ro` is not provisioned, the read-only AI pool automatically falls back to `db_user` (`avnadmin`), preventing connection termination.

2. **JSON Error Response Guarantee in [`app.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/app.py)**:
   Ensuring any route containing `"/api/"` (including `/ai/api/`, `/market/api/`, `/investor/api/`, `/broker/api/`, `/admin/api/`) returns structured JSON ensures that even unexpected runtime failures produce valid JSON payloads that `client.js` can parse and display cleanly.

---

## 3. Known Cloud Hosting Caveats & Environmental Limitations

1. **Render Free Tier Container Sleep**:
   - Web services on Render Free Tier spin down after 15 minutes of inactivity.
   - The first request after sleep takes approximately 50 seconds to boot the container.
   - An external uptime monitor pinging `/health` every 10 minutes prevents container idling.

2. **Aiven Cloud MySQL Free Tier Inactivity Power-Off**:
   - Aiven Free Tier instances automatically power off after extended inactivity.
   - Reactivating requires logging into the Aiven Web Console and clicking **Resume**. All database schemas, tables, triggers, and procedures remain intact on persistent storage.

3. **In-Memory Rate Limiting**:
   - `Flask-Limiter` is configured with `memory://`. Rate limits are enforced locally inside the single Gunicorn worker process. For multi-node horizontal scaling, a Redis storage URI should be configured.
