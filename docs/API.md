# StockTrade REST API Reference

All endpoints return JSON responses with standard envelope format:
```json
// Success
{
  "ok": true,
  "data": { ... }
}

// Error
{
  "ok": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description"
  }
}
```

---

## 1. Authentication (`/api/v1/auth`)

### `POST /api/v1/auth/login`
Authenticates a user and establishes an HTTP-only server-side session.
- **Body**:
  ```json
  {
    "identifier": "investor_rahul",
    "password": "DemoPassword123!"
  }
  ```
- **Responses**:
  - `200 OK`: Returns authenticated user dictionary.
  - `401 Unauthorized`: Bad credentials or account locked (after 5 failed attempts).

### `POST /api/v1/auth/logout`
Destroys the current server-side session and clears authentication cookies.
- **Requires**: Authentication
- **Responses**: `200 OK`.

### `GET /api/v1/auth/session`
Returns current session status and active CSRF token.
- **Responses**:
  ```json
  {
    "ok": true,
    "data": {
      "authenticated": true,
      "csrf_token": "...",
      "user": { "id": 4, "username": "investor_rahul", "role": "INVESTOR" }
    }
  }
  ```

---

## 2. Market Data (`/market/api/v1/market`)

### `GET /market/api/v1/market/prices`
Fetches real-time market prices for all 100 listed equities.
- **Query Params**:
  - `since` (optional): ISO timestamp filter for delta polling.
- **Responses**:
  ```json
  {
    "ok": true,
    "data": [
      {
        "stock_id": 1,
        "symbol": "TCS",
        "company_name": "Tata Consultancy Services Ltd",
        "sector": "Information Technology",
        "current_price": 4210.50,
        "previous_close": 4200.00,
        "change_pct": 0.25
      }
    ]
  }
  ```

### `GET /market/api/v1/market/history`
Aggregates historical time-series into OHLC candlesticks directly in MySQL.
- **Query Params**:
  - `symbol` (required): Equity ticker (e.g. `RELIANCE`).
  - `interval` (optional): `1m`, `5m`, or `1h` (default `5m`).
- **Responses**:
  ```json
  {
    "ok": true,
    "data": {
      "symbol": "RELIANCE",
      "interval": "5m",
      "candles": [
        { "bucket": "2026-10-15 09:15:00", "open": 2450.0, "high": 2455.5, "low": 2448.0, "close": 2453.0, "volume": 1250 }
      ]
    }
  }
  ```

### `GET /market/api/v1/market/status`
Returns market simulator freshness status, completed ticks, and health indicator (`green`, `amber`, `red`).

---

## 3. Investor Endpoints (`/investor/api/v1/investor`)

### `GET /investor/api/v1/investor/summary`
Returns canonical portfolio metrics computed directly from database tables.
- **Requires**: Role `INVESTOR`
- **Responses**:
  ```json
  {
    "ok": true,
    "data": {
      "available_cash": 64337.49,
      "holdings_market_value": 42105.00,
      "portfolio_value": 106442.49,
      "unrealized_pnl": 580.00,
      "realized_pnl": 1240.50
    }
  }
  ```

### `GET /investor/api/v1/investor/holdings`
Returns current open stock positions with weighted average cost basis and mark-to-market valuations.

### `POST /investor/api/v1/investor/orders`
Executes an immediate market order atomically via `sp_execute_trade`.
- **Requires**: Role `INVESTOR`
- **Body**:
  ```json
  {
    "stock_id": 1,
    "side": "BUY",
    "quantity": 10,
    "idempotency_key": "req_1728950000_abc123",
    "quoted_price": 4210.50
  }
  ```
- **Responses**:
  - `200 OK`: Order executed, ledger entries created.
  - `409 Conflict`: Price moved by >1% tolerance since quote; reconfirmation required.
  - `422 Unprocessable Entity`: Insufficient virtual balance or insufficient shares.

### `POST /investor/api/v1/investor/deposit`
Adds virtual cash to the user's account under strict daily caps (Max ₹50,000/day).

### `GET /investor/api/v1/investor/watchlist`
Returns the user's saved watchlist of stocks accompanied by real-time market quotes and day change metrics.

### `POST /investor/api/v1/investor/watchlist`
Adds a stock to the user's watchlist idempotently.
- **Body**: `{ "stock_id": 1 }`

### `DELETE /investor/api/v1/investor/watchlist/<stock_id>`
Removes a stock from the user's watchlist.

### `GET /investor/api/v1/investor/alerts`
Returns price threshold alerts configured by the investor. Optional query filter: `?status=ACTIVE`.

### `POST /investor/api/v1/investor/alerts`
Configures a new price threshold alert evaluated on every market tick.
- **Body**:
  ```json
  {
    "stock_id": 1,
    "target_price": 4300.00,
    "condition_type": "ABOVE"
  }
  ```

### `DELETE /investor/api/v1/investor/alerts/<alert_id>`
Cancels or removes an alert.

### `GET /investor/api/v1/investor/broker`
Returns the investor's active assigned broker relationship and current brokerage fee policy.

### `GET /investor/api/v1/investor/statement`
Exports the investor's complete transaction statement as an RFC-4180 compliant CSV protected against formula injection.

---

## 4. Broker Endpoints (`/broker/api/v1/broker`)

### `GET /broker/api/v1/broker/clients`
Lists all active investor clients assigned to the authenticated broker.

### `POST /broker/api/v1/broker/clients`
Atomically onboards a new investor client, creating a user, virtual account, ₹1,00,000 grant, and active `Broker_Clients` link.
- **Body**:
  ```json
  {
    "username": "ramesh_c",
    "email": "ramesh@example.com",
    "full_name": "Ramesh Chandra",
    "password": "SecurePassword123!",
    "phone": "9876543210"
  }
  ```

### `GET /broker/api/v1/broker/client-profile`
Retrieves detailed holdings, transactions, and commissions for an assigned investor.
- **Tenant Isolation**: Returns `404 Not Found` (never 403) if client is not assigned to the caller.

### `POST /broker/api/v1/broker/clients/<id>/end`
Terminates the broker-client assignment relationship.

### `GET /broker/api/v1/broker/analytics`
Summarizes platform-funded broker commissions (40% of collected investor brokerage).

---

## 5. Administrative Endpoints (`/admin/api/v1/admin`)

### `GET /admin/api/v1/admin/overview`
Returns platform-wide metrics: user count, total circulating virtual capital, listed equities, and trade facts.

### `GET /admin/api/v1/admin/companies` | `POST` | `PUT` | `DELETE`
Full security CRUD with guarded hard-delete checks (prevents deletion if trade orders exist).

### `GET /admin/api/v1/admin/users`
Lists all user accounts, roles, statuses, and failed login counts.

### `PATCH /admin/api/v1/admin/users/<id>/status`
Toggles account status between `ACTIVE` and `INACTIVE`.

### `POST /admin/api/v1/admin/users/<id>/reset-lockout`
Clears failed login counter and unlocks an account after brute force lockout.

### `GET /admin/api/v1/admin/simulator/status` | `POST .../control`
Monitors and controls the APScheduler background worker (`pause`, `resume`, `tick`).

### `GET /admin/api/v1/admin/audit-logs`
Queries tamper-resistant audit logs with pagination and filters.

### `GET /admin/api/v1/admin/commission-rules` | `POST`
Retrieves and updates active platform-wide commission rules (`INVESTOR_BROKERAGE` and `BROKER_COMMISSION`).
- **Body for POST**:
  ```json
  {
    "rule_type": "INVESTOR_BROKERAGE",
    "rate": 0.0010,
    "min_fee": 1.00
  }
  ```

---

## 6. AI Assistant Endpoints (`/api/v1/ai`)

### `POST /api/v1/ai/query`
Natural language database query via multi-provider failover router (Grok &rarr; Gemini &rarr; OpenRouter &rarr; Local Fallback).
- **Body**:
  ```json
  {
    "prompt": "Show my open stock holdings and their current values"
  }
  ```
- **Responses**:
  ```json
  {
    "ok": true,
    "data": {
      "generated_sql": "SELECT symbol, quantity, current_price, market_value FROM v_investor_portfolio WHERE user_id = @current_user_id;",
      "provider_used": "grok",
      "ast_validated": true,
      "columns": ["symbol", "quantity", "current_price", "market_value"],
      "rows": [ ... ],
      "row_count": 1,
      "duration_ms": 12,
      "summary": "You hold 10 shares of TCS with a market value of ₹42,105.00."
    }
  }
  ```

### `POST /api/v1/ai/execute`
Executes custom read-only SQL queries in Manual SQL mode through the unified 5-layer security pipeline (AST allowlist, tenant subquery injection, 5s timeout, read-only transaction, and audit logging).
- **Body**:
  ```json
  {
    "sql": "SELECT symbol, quantity, current_price, market_value FROM v_investor_portfolio ORDER BY market_value DESC;",
    "prompt": "Manual SQL Execution",
    "provider": "MANUAL_SQL"
  }
  ```
- **Responses**:
  - `200 OK`:
    ```json
    {
      "ok": true,
      "data": {
        "executed_sql": "SELECT symbol, quantity, current_price, market_value FROM (SELECT * FROM v_investor_portfolio WHERE user_id = :auth_user_id) AS v_investor_portfolio ORDER BY market_value DESC LIMIT 500;",
        "columns": ["symbol", "quantity", "current_price", "market_value"],
        "rows": [ ... ],
        "row_count": 5,
        "duration_ms": 11,
        "summary": "Query completed successfully, returning 5 rows.",
        "tables_used": ["v_investor_portfolio"],
        "ast_validated": true,
        "provider": "MANUAL_SQL"
      }
    }
    ```
  - `422 Unprocessable Entity`: Validation failure (mutation, unauthorized table, multiple statements, forbidden keyword).

### `GET /api/v1/ai/schema`
Returns role-authorized views, descriptions, columns, and sample queries for the Manual SQL editor.
