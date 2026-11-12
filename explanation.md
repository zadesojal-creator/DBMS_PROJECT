# STOCKTRADE v2 — COMPLETE FEATURE-BY-FEATURE TECHNICAL EXPLANATION
## End-to-End Execution Guide: From UI Button Click to MySQL Engine Execution

> **Document Purpose**: Exhaustive technical documentation explaining **every single feature** of StockTrade v2.  
> **How to Read This Document**: For every user-facing feature, this guide traces the exact path:
> `[UI Button Click]` $\to$ `[Frontend State & Payload]` $\to$ `[Flask API Route]` $\to$ `[Service Layer Logic]` $\to$ `[MySQL 8.0 Engine & SQL Execution]` $\to$ `[Database Locks, Triggers & Procedures]` $\to$ `[UI Update]`.

---

# TABLE OF CONTENTS
1. [System Architecture & The Request-Execution Lifecycle](#1-system-architecture--the-request-execution-lifecycle)
2. [Authentication & Session Features](#2-authentication--session-features)
   - [Feature 1: User Login & Role Isolation](#feature-1-user-login--role-isolation)
   - [Feature 2: User Logout & Session Invalidation](#feature-2-user-logout--session-invalidation)
   - [Feature 3: Session Tenancy Verification (`/auth/me`)](#feature-3-session-tenancy-verification)
3. [Market & Equities Features](#3-market--equities-features)
   - [Feature 4: Live Market Screener & Price Ticker](#feature-4-live-market-screener--price-ticker)
   - [Feature 5: Autonomous Market Simulator (Background Engine)](#feature-5-autonomous-market-simulator-background-engine)
   - [Feature 6: Interactive Stock Price Chart (Multi-Timeframe)](#feature-6-interactive-stock-price-chart-multi-timeframe)
4. [Retail Investor Features](#4-retail-investor-features)
   - [Feature 7: Portfolio Overview & Valuation](#feature-7-portfolio-overview--valuation)
   - [Feature 8: Execute Market BUY Order (Atomic Stored Procedure)](#feature-8-execute-market-buy-order-atomic-stored-procedure)
   - [Feature 9: Execute Market SELL Order (Realized P&L Calculation)](#feature-9-execute-market-sell-order-realized-pl-calculation)
   - [Feature 10: Virtual Cash Deposit](#feature-10-virtual-cash-deposit)
   - [Feature 11: Trade Execution History & RFC 4180 CSV Export](#feature-11-trade-execution-history--rfc-4180-csv-export)
   - [Feature 12: Watchlist Toggle (Add / Remove)](#feature-12-watchlist-toggle-add--remove)
   - [Feature 13: Conditional Price Alerts](#feature-13-conditional-price-alerts)
   - [Feature 14: Assigned Broker View](#feature-14-assigned-broker-view)
5. [Institutional Broker Features](#5-institutional-broker-features)
   - [Feature 15: Client Roster & Volume Analytics](#feature-15-client-roster--volume-analytics)
   - [Feature 16: Client Onboarding (Broker-Investor Assignment)](#feature-16-client-onboarding-broker-investor-assignment)
   - [Feature 17: Client Portfolio & Trade Inspection (Tenant Isolated)](#feature-17-client-portfolio--trade-inspection-tenant-isolated)
   - [Feature 18: Terminate Advisory Relationship](#feature-18-terminate-advisory-relationship)
   - [Feature 19: Brokerage Commission Analytics (40% Platform Split)](#feature-19-brokerage-commission-analytics-40-platform-split)
6. [System Administrator Features](#6-system-administrator-features)
   - [Feature 20: Platform Overview & Global KPIs](#feature-20-platform-overview--global-kpis)
   - [Feature 21: Listed Equity CRUD (Add / Edit Company)](#feature-21-listed-equity-crud-add--edit-company)
   - [Feature 22: User Account Administration & Lockout Reset](#feature-22-user-account-administration--lockout-reset)
   - [Feature 23: Security Audit Log Inspection](#feature-23-security-audit-log-inspection)
   - [Feature 24: Market Simulator Real-Time Controls](#feature-24-market-simulator-real-time-controls)
   - [Feature 25: Automated 7-Point Financial Reconciliation Audit](#feature-25-automated-7-point-financial-reconciliation-audit)
7. [AI Text-to-SQL Assistant & Manual SQL Features](#7-ai-text-to-sql-assistant--manual-sql-features)
   - [Feature 26: AI Natural-Language SQL Generation & Execution](#feature-26-ai-natural-language-sql-generation--execution)
   - [Feature 27: Manual SQL Mode (AST-Validated Execution)](#feature-27-manual-sql-mode-ast-validated-execution)
   - [Feature 28: AI Query History & Audit Log](#feature-28-ai-query-history--audit-log)

---

# 1. System Architecture & The Request-Execution Lifecycle

Every interaction in StockTrade v2 follows a strict 5-layer separation of concerns:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. CLIENT BROWSER: React 18 SPA (Vite)                                         │
│    User clicks a button -> Client validates form -> Sends HTTP JSON / Form Data  │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ HTTPS / REST API
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. ROUTE & SECURITY MIDDLEWARE: Flask 3 Blueprints                              │
│    CSRF Validation -> Flask-Login Session Check -> @role_required decorator    │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ Python Method Call
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. SERVICE & REPOSITORY LAYER: Python 3.11                                     │
│    Input sanitization -> Idempotency check -> Prepares parameters               │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ Parameterized SQL / CALL sp_...
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 4. DATABASE DRIVER & POOL: SQLAlchemy 2.0 Core & PyMySQL (TLS CA)              │
│    Borrows pooled connection -> Enforces session parameters -> Executes query  │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ Native MySQL Engine
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 5. DATABASE ENGINE: MySQL 8.0+ / InnoDB                                         │
│    Row locks (FOR UPDATE) -> Stored Procedures -> Triggers -> ACID Commit/Rollback│
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# 2. Authentication & Session Features

---

### Feature 1: User Login & Role Isolation

#### 1. What the User Clicks
- On the split login gateway (`http://127.0.0.1:5000`), the user enters their **Username or Email** and **Password** (or clicks one of the demo pills: `admin`, `broker_arun`, `investor_rahul`) and clicks **"Sign In to Terminal"**.

#### 2. Frontend Action (`frontend/src/pages/Login.jsx`)
- Collects `identifier` and `password`.
- Sends an asynchronous HTTP request:
  ```http
  POST /api/v1/auth/login
  Content-Type: application/json

  {"identifier": "investor_rahul", "password": "Investor@StockTrade2026"}
  ```

#### 3. Backend Route & Service (`routes/auth.py` $\to$ `repositories/user_repo.py`)
- Route `api_login()` validates non-empty strings.
- Calls `UserRepository.get_by_identifier(identifier)`.
- Checks brute-force lockout status: If `locked_until > CURRENT_TIMESTAMP`, login is rejected immediately (`HTTP 403 Forbidden`).
- Calls `check_password_hash(user['password_hash'], password)`.
  - **If Password Correct**:
    - Calls `UserRepository.reset_failed_logins(user_id)`.
    - Logs successful login event in `Audit_Logs`.
    - Calls `flask_login.login_user(User(user), remember=True)`.
    - Sets encrypted, HTTP-only session cookie.
  - **If Password Incorrect**:
    - Calls `UserRepository.record_failed_login(user_id)`.
    - If failed attempts reach 5, sets `locked_until = NOW() + INTERVAL 15 MINUTE`.
    - Writes `LOGIN_FAILED` audit log.

#### 4. Database Queries Executed
```sql
-- 1. Fetch user credentials and lockout status
SELECT id, username, email, password_hash, full_name, role, status, 
       failed_login_attempts, locked_until 
FROM Users 
WHERE (username = 'investor_rahul' OR email = 'investor_rahul') 
LIMIT 1;

-- 2. If password matches: Reset failed counter and update last login
UPDATE Users 
SET failed_login_attempts = 0, 
    locked_until = NULL, 
    last_login_at = CURRENT_TIMESTAMP 
WHERE id = 4;

-- 3. Log security event
INSERT INTO Audit_Logs (user_id, action, ip_address, details) 
VALUES (4, 'LOGIN_SUCCESS', '127.0.0.1', 'User logged in successfully');
```

#### 5. Screen Update
- Returns `HTTP 200 OK` with user role and profile. React updates global auth state in `AuthContext` and redirects the user to their designated portal (`/investor/dashboard`, `/broker/clients`, or `/admin/overview`).

---

### Feature 2: User Logout & Session Invalidation

#### 1. What the User Clicks
- User clicks the **"Exit"** / **"Sign Out"** button on the top-right navbar.

#### 2. Frontend Action (`Navbar.jsx`)
- Sends:
  ```http
  POST /api/v1/auth/logout
  ```

#### 3. Backend Route (`routes/auth.py`)
- Retrieves `current_user.id`.
- Inserts `LOGOUT` audit log into `Audit_Logs`.
- Calls `flask_login.logout_user()`.
- Calls `session.clear()`, completely deleting server-side session cookies.

#### 4. Database Query Executed
```sql
INSERT INTO Audit_Logs (user_id, action, ip_address, details) 
VALUES (4, 'LOGOUT', '127.0.0.1', 'User logged out');
```

#### 5. Screen Update
- React clears stored user tokens and redirects the browser back to the login portal.

---

### Feature 3: Session Tenancy Verification (`/auth/me`)

#### 1. What Happens
- Whenever the browser refreshes or navigates between tabs, React verifies that the user's session is still active and valid.

#### 2. Request & Execution
- Sends:
  ```http
  GET /api/v1/auth/me
  ```
- Flask reads the encrypted session cookie, verifies the cryptographic signature with `SECRET_KEY`, and executes:
  ```sql
  SELECT id, username, email, full_name, role, status 
  FROM Users 
  WHERE id = :current_user_id;
  ```
- Returns the current user's role and account status. If the cookie is expired or manipulated, Flask returns `HTTP 401 Unauthorized` and logs the user out.

---

# 3. Market & Equities Features

---

### Feature 4: Live Market Screener & Price Ticker

#### 1. What the User Clicks / Sees
- User opens the **"Market"** tab or views the moving ticker tape marquee.
- Can type into the search bar (e.g. "Tata") or click a Sector Pill (e.g. "Banking", "Information Technology").

#### 2. Frontend Action (`frontend/src/pages/market/MarketView.jsx`)
- Poller or component mount sends:
  ```http
  GET /market/api/v1/market/prices
  ```

#### 3. Backend Route & Service (`routes/market.py` $\to$ `repositories/market_repo.py`)
- Executes query against the security view `v_market_latest`.

#### 4. Database Query Executed
```sql
SELECT 
    stock_id, symbol, company_name, sector, exchange, status,
    current_price, previous_close, day_change, day_change_pct,
    day_open, day_high, day_low, volume, updated_at
FROM v_market_latest
ORDER BY volume DESC;
```
*View Mechanics (`v_market_latest`)*:
This view joins `Stocks` with `Current_Prices`, dynamically calculating:
- `day_change = cp.price - cp.previous_close`
- `day_change_pct = ROUND(((cp.price - cp.previous_close) / cp.previous_close) * 100, 2)`

#### 5. Screen Update
- Renders 104 stock cards with green/red badges indicating positive/negative percentage changes, volume, and live market quotes.

---

### Feature 5: Autonomous Market Simulator (Background Engine)

#### 1. What Triggers It
- Runs autonomously in a background daemon thread (`services/market_simulator.py`) independently of any user clicks.

#### 2. Execution Logic & Mathematical Model
- Ticks every **500 milliseconds** (2 ticks per second).
- Acquires MySQL advisory lock `GET_LOCK('stocktrade_simulator', 0)` so only one process in a cluster generates prices.
- For each stock $i$, draws Gaussian variable $Z \sim \mathcal{N}(0, 1)$ and calculates:
  $$\Delta P_i = P_{i,t} \times \left( \mu_i \cdot \Delta t + \sigma_{sector} \cdot \sqrt{\Delta t} \cdot Z + \kappa \cdot (\bar{P}_{sector} - P_{i,t}) \cdot \Delta t \right)$$
- **Clamps**:
  - Max per-tick movement bounded to $\pm 0.50\%$.
  - Daily price bounded to $\pm 10.0\%$ circuit limit bands from `previous_close`.
- **Decoupled Persistence**: Fast ticks update memory. A dedicated background flush thread executes batch writes to MySQL **once per second** to prevent database pool exhaustion.

#### 3. Database Queries Executed (Batch Flush)
```sql
-- 1. Acquire advisory lock
SELECT GET_LOCK('stocktrade_simulator', 0);

-- 2. Batch update live quotes in Current_Prices
UPDATE Current_Prices 
SET price = :new_price, 
    volume = volume + :tick_volume,
    day_high = GREATEST(day_high, :new_price),
    day_low = LEAST(day_low, :new_price),
    updated_at = CURRENT_TIMESTAMP
WHERE stock_id = :sid;

-- 3. Append 1-minute historical observation
INSERT INTO Stock_Prices (stock_id, price, volume, recorded_at)
VALUES (:sid, :new_price, :volume, CURRENT_TIMESTAMP);
```

---

### Feature 6: Interactive Stock Price Chart (Multi-Timeframe)

#### 1. What the User Clicks
- On any stock card, the user clicks **"View Chart"** or clicks on the stock row.
- In the modal, clicks timeframe tabs: **"1m"**, **"5m"**, or **"1h"**.

#### 2. Frontend Action (`StockChartModal.jsx`)
- Sends:
  ```http
  GET /market/api/v1/market/stocks/1/history?timeframe=5m
  ```

#### 3. Backend Route & Database Query (`routes/market.py`)
```sql
-- For high-resolution 1m / 5m buckets:
SELECT recorded_at, price, volume 
FROM Stock_Prices 
WHERE stock_id = 1 
  AND recorded_at >= NOW() - INTERVAL 24 HOUR 
ORDER BY recorded_at ASC;

-- For hourly OHLC rollups (1h):
SELECT hour_bucket, open_price, high_price, low_price, close_price, volume
FROM Stock_Price_Hourly
WHERE stock_id = 1
ORDER BY hour_bucket ASC;
```

#### 4. Screen Update
- Chart.js renders a smooth line or candlestick chart showing price movement, volume bars, and day high/low markers.

---

# 4. Retail Investor Features

---

### Feature 7: Portfolio Overview & Valuation

#### 1. What the User Clicks
- Investor clicks **"Dashboard"** or **"Portfolio"**.

#### 2. Frontend Action (`InvestorDashboard.jsx`)
- Sends:
  ```http
  GET /investor/api/v1/investor/portfolio
  ```

#### 3. Database Queries Executed
```sql
-- 1. Fetch available cash balance
SELECT virtual_balance, currency, status 
FROM Accounts 
WHERE user_id = 4;

-- 2. Fetch active holdings with live market valuation
SELECT 
    holding_id, stock_id, symbol, company_name, sector, exchange,
    quantity, avg_cost, total_invested, current_price, current_value,
    unrealized_pnl, return_pct
FROM v_investor_portfolio 
WHERE user_id = 4;
```
*View Mechanics (`v_investor_portfolio`)*:
- `total_invested = quantity * avg_cost`
- `current_value = quantity * current_price`
- `unrealized_pnl = current_value - total_invested`
- `return_pct = ROUND(((current_value - total_invested) / total_invested) * 100, 2)`

#### 4. Screen Update
- Displays 4 live KPI cards: **Total Portfolio Value**, **Available Cash**, **Unrealized Gain/Loss**, and **Total Investments**. Below, displays the holdings breakdown table.

---

### Feature 8: Execute Market BUY Order (Atomic Stored Procedure)

#### 1. What the User Clicks
- In the Market or Portfolio view, clicks **"Trade"** on a stock (e.g. TCS).
- Selects **BUY**, enters quantity (e.g. **10 shares**).
- Trade ticket displays real-time estimated gross amount, brokerage fee, and net settlement.
- Clicks **"Execute Order"**.

#### 2. Frontend Action (`TradeTicketModal.jsx`)
- Generates a UUID v4 idempotency key (e.g. `9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d`).
- Sends:
  ```http
  POST /investor/api/v1/investor/orders
  Content-Type: application/json

  {
    "stock_id": 1,
    "side": "BUY",
    "quantity": 10,
    "idempotency_key": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
  }
  ```

#### 3. Backend Route & Service Layer (`routes/investor.py` $\to$ `services/trading_service.py`)
- Validates that user has role `INVESTOR`.
- Calls `TradingService.execute_market_order()`.
- Python invokes MySQL stored procedure `sp_execute_trade` with input and output parameters.

#### 4. Database Engine Execution (`sp_execute_trade` in `database/procedures.sql`)
The entire trade executes inside MySQL under an atomic transaction:

```sql
CALL sp_execute_trade(
    4,                     -- p_user_id (Rahul)
    1,                     -- p_stock_id (TCS)
    'BUY',                 -- p_side
    10,                    -- p_quantity
    '9b1deb4d-...',        -- p_idempotency_key
    @order_id, @transaction_id, @execution_price, @status, @message
);
```

**Step-by-Step Execution inside MySQL**:
1. **Idempotency Guard**:
   ```sql
   SELECT id, status, executed_price INTO v_existing_order_id, ... 
   FROM Orders 
   WHERE user_id = 4 AND idempotency_key = '9b1deb4d-...';
   ```
   If already processed, returns immediately with existing receipt, preventing double-orders.
2. **Fetch Live Execution Price**:
   ```sql
   SELECT price INTO v_current_price FROM Current_Prices WHERE stock_id = 1;
   ```
3. **Pessimistic Row Lock on Account**:
   ```sql
   SELECT virtual_balance INTO v_current_balance 
   FROM Accounts 
   WHERE user_id = 4 
   FOR UPDATE;
   ```
   *padlocks the investor's balance row against concurrent trades*.
4. **Calculate Financials**:
   - $\text{Gross} = 10 \times 4133.45 = ₹41,334.50$
   - $\text{Fee} = \max(41,334.50 \times 0.0010, 1.00) = ₹41.33$
   - $\text{Total Deducted} = ₹41,375.83$
5. **Solvency Verification**:
   If `v_current_balance < Total Deducted`:
   - Inserts `Orders` row with `status = 'REJECTED'` and reason `'Insufficient funds'`.
   - Fires trigger `trg_orders_audit_insert` to log rejection in `Order_Events`.
   - Quits procedure. No money or shares move.
6. **Balance Deduction**:
   ```sql
   UPDATE Accounts 
   SET virtual_balance = virtual_balance - 41375.83 
   WHERE user_id = 4;
   ```
7. **Pessimistic Row Lock & WAC Calculation on Holdings**:
   ```sql
   SELECT quantity, avg_cost INTO v_existing_qty, v_existing_avg_cost 
   FROM Holdings 
   WHERE user_id = 4 AND stock_id = 1 
   FOR UPDATE;
   ```
   Calculates Weighted-Average Cost:
   $$\text{WAC}_{new} = \frac{(Q_{old} \times \text{AvgCost}_{old}) + (10 \times 4133.45)}{Q_{old} + 10}$$
   ```sql
   INSERT INTO Holdings (user_id, stock_id, quantity, avg_cost)
   VALUES (4, 1, 10, 4133.45)
   ON DUPLICATE KEY UPDATE 
       quantity = quantity + 10,
       avg_cost = v_new_wac;
   ```
8. **Record Receipts & Events**:
   ```sql
   -- Insert executed order
   INSERT INTO Orders (user_id, stock_id, side, quantity, executed_price, status, idempotency_key)
   VALUES (4, 1, 'BUY', 10, 4133.45, 'EXECUTED', '9b1deb4d-...');
   
   -- Insert trade transaction receipt
   INSERT INTO Transactions (order_id, user_id, stock_id, side, quantity, execution_price, gross_amount, brokerage_fee, net_amount, realized_pnl)
   VALUES (@order_id, 4, 1, 'BUY', 10, 4133.45, 41334.50, 41.33, 41375.83, 0.00);
   ```
9. **Double-Entry Ledger Ingestion**:
   ```sql
   -- Entry 1: Equity purchase debit
   INSERT INTO Account_Ledger (account_id, entry_type, amount, balance_after, reference_type, reference_id)
   VALUES (v_account_id, 'BUY', -41334.50, v_bal_after_trade, 'ORDER', @order_id);

   -- Entry 2: Platform brokerage fee debit
   INSERT INTO Account_Ledger (account_id, entry_type, amount, balance_after, reference_type, reference_id)
   VALUES (v_account_id, 'FEE', -41.33, v_bal_after_fee, 'ORDER', @order_id);
   ```
10. **Platform Broker Commission Split**:
    If investor has an active broker (e.g. Arun Mehta):
    ```sql
    INSERT INTO Commissions (broker_id, investor_id, transaction_id, commission_rate, commission_amount)
    VALUES (v_broker_id, 4, @transaction_id, 0.40, 41.33 * 0.40);
    ```
11. **Triggers Activated**:
    - `trg_orders_audit_insert`: Automatically logs status transition `NEW` $\to$ `EXECUTED` into `Order_Events`.
    - `trg_ledger_block_update` / `delete`: Ensures the ledger rows can never be altered.

#### 5. Screen Update
- Flask returns `HTTP 201 Created` with order execution details.
- React shows green success toast notification, immediately drops available buying power by ₹41,375.83, and adds 10 shares of TCS to the portfolio table.

---

### Feature 9: Execute Market SELL Order (Realized P&L Calculation)

#### 1. What the User Clicks
- In the Portfolio table, clicks **"Sell"** on an owned position (e.g. TCS).
- Enters quantity (e.g. **5 shares**), clicks **"Execute Order"**.

#### 2. Frontend Action
- Sends:
  ```http
  POST /investor/api/v1/investor/orders
  {"stock_id": 1, "side": "SELL", "quantity": 5, "idempotency_key": "uuid..."}
  ```

#### 3. Database Execution (`sp_execute_trade`)
1. **Holdings Row Lock & Sufficiency Check**:
   ```sql
   SELECT quantity, avg_cost INTO v_existing_qty, v_avg_cost 
   FROM Holdings 
   WHERE user_id = 4 AND stock_id = 1 
   FOR UPDATE;
   ```
   If `v_existing_qty < 5`:
   - Records order as `REJECTED` (`"Insufficient holdings to sell"`).
   - Quits procedure. Zero balance or shares move.
2. **Decrement Share Holdings**:
   ```sql
   UPDATE Holdings 
   SET quantity = quantity - 5 
   WHERE user_id = 4 AND stock_id = 1;
   ```
   *(If remaining quantity becomes 0, deletes holding row).*
3. **Calculate Realized Profit & Loss (P&L)**:
   $$\text{Realized P\&L} = (\text{Execution Price} - \text{Avg Cost}) \times \text{Sold Quantity}$$
   $$\text{Example} = (4200.00 - 4133.45) \times 5 = +₹332.75$$
4. **Credit Cash Proceeds**:
   - $\text{Gross Proceeds} = 5 \times 4200.00 = ₹21,000.00$
   - $\text{Fee} = 21,000.00 \times 0.0010 = ₹21.00$
   - $\text{Net Cash Credited} = ₹20,979.00$
   ```sql
   UPDATE Accounts 
   SET virtual_balance = virtual_balance + 20979.00 
   WHERE user_id = 4;
   ```
5. **Ledger & Transaction Ingestion**:
   - `Transactions` records `realized_pnl = 332.75`.
   - `Account_Ledger` records `SELL` (+₹21,000.00) and `FEE` (-₹21.00).

#### 4. Screen Update
- React updates cash balance (+₹20,979.00), decrements share count, and highlights the green realized profit amount in the Transactions tab.

---

### Feature 10: Virtual Cash Deposit

#### 1. What the User Clicks
- In the Portfolio dashboard, clicks the **"Deposit Funds"** button.
- Types deposit amount (e.g. ₹50,000.00) and clicks **"Confirm Deposit"**.

#### 2. Frontend Action (`DepositModal.jsx`)
- Sends:
  ```http
  POST /investor/api/v1/investor/deposit
  {"amount": 50000.00}
  ```

#### 3. Backend & Database Queries (`routes/investor.py` $\to$ `services/trading_service.py`)
```sql
-- 1. Lock and credit Accounts balance
SELECT id, virtual_balance FROM Accounts WHERE user_id = 4 FOR UPDATE;

UPDATE Accounts 
SET virtual_balance = virtual_balance + 50000.00 
WHERE user_id = 4;

-- 2. Ingest double-entry audit record into Account_Ledger
INSERT INTO Account_Ledger (account_id, entry_type, amount, balance_after, reference_type, reference_id)
VALUES (1, 'DEPOSIT', 50000.00, 150000.00, 'SELF_DEPOSIT', 'DEP-4-TIMESTAMP');
```

#### 4. Screen Update
- Cash balance immediately reflects the new funds; ledger entry appears in the audit history.

---

### Feature 11: Trade Execution History & RFC 4180 CSV Export

#### 1. What the User Clicks
- User clicks **"Transactions"** tab to view historical trade receipts.
- Clicks the **"Export CSV"** button.

#### 2. Database Query (`v_investor_transactions`)
```sql
SELECT 
    transaction_id, order_id, symbol, company_name, side,
    quantity, execution_price, gross_amount, brokerage_fee,
    net_amount, realized_pnl, executed_at
FROM v_investor_transactions
WHERE user_id = 4
ORDER BY executed_at DESC;
```

#### 3. Screen Update / Download
- Screen displays chronological table with realized P&L badges.
- Clicking "Export CSV" streams an RFC 4180 compliant CSV file (`stocktrade_transactions_2026.csv`) directly to the user's downloads folder.

---

### Feature 12: Watchlist Toggle (Add / Remove)

#### 1. What the User Clicks
- On any stock card or screener row, clicks the **Star** icon to monitor or unmonitor an equity.

#### 2. Database Queries Executed
```sql
-- To Add to Watchlist:
INSERT INTO Watchlist (user_id, stock_id) 
VALUES (4, 1)
ON DUPLICATE KEY UPDATE added_at = CURRENT_TIMESTAMP;

-- To Remove from Watchlist:
DELETE FROM Watchlist 
WHERE user_id = 4 AND stock_id = 1;

-- To Query Watchlist:
SELECT w.stock_id, s.symbol, s.company_name, cp.price, cp.day_change_pct, cp.volume
FROM Watchlist w
JOIN Stocks s ON w.stock_id = s.id
JOIN Current_Prices cp ON s.id = cp.stock_id
WHERE w.user_id = 4;
```

---

### Feature 13: Conditional Price Alerts

#### 1. What the User Clicks
- In the stock view, clicks **"Set Alert"**.
- Enters target price (e.g. ₹4,200.00) and condition (`ABOVE` or `BELOW`).
- Clicks **"Create Alert"**.

#### 2. Database Query
```sql
INSERT INTO Price_Alerts (user_id, stock_id, target_price, condition_type, is_active)
VALUES (4, 1, 4200.00, 'ABOVE', TRUE);
```
- When `MarketSimulator` ticks TCS past ₹4,200, the system triggers the alert badge.

---

### Feature 14: Assigned Broker View

#### 1. What the User Clicks
- Investor clicks **"My Broker"** tab.

#### 2. Database Query
```sql
SELECT 
    u.full_name AS broker_name, 
    u.email AS broker_email, 
    bc.assigned_at,
    cr.broker_commission_rate
FROM Broker_Clients bc
JOIN Users u ON bc.broker_id = u.id
JOIN Commission_Rules cr ON cr.is_active = TRUE
WHERE bc.investor_id = 4 AND bc.status = 'ACTIVE'
LIMIT 1;
```

---

# 5. Institutional Broker Features

---

### Feature 15: Client Roster & Volume Analytics

#### 1. What the User Clicks
- Broker Arun Mehta logs in and clicks **"Clients"**.

#### 2. Frontend Action (`BrokerClientsView.jsx`)
- Sends:
  ```http
  GET /broker/api/v1/broker/clients
  ```

#### 3. Database Query (`v_broker_client_summary`)
```sql
SELECT 
    investor_id, investor_name, investor_email, virtual_balance,
    assigned_at, total_trades, total_volume, total_commission_generated
FROM v_broker_client_summary
WHERE broker_id = 2;
```
*Tenant Security*: The query automatically restricts records to `broker_id = current_user.id`. Arun cannot see clients assigned to Priya.

---

### Feature 16: Client Onboarding (Broker-Investor Assignment)

#### 1. What the User Clicks
- Broker clicks **"Onboard Client"**.
- Selects an unassigned investor (e.g. `investor_rohit`) from the dropdown and clicks **"Assign Client"**.

#### 2. Database Query & Triggers Activated
```sql
INSERT INTO Broker_Clients (broker_id, investor_id, status)
VALUES (2, 9, 'ACTIVE');
```
*Triggers Enforcing Integrity*:
- `trg_broker_clients_role_insert`: Checks that `broker_id` has `role = 'BROKER'` and `investor_id` has `role = 'INVESTOR'`. If an admin or another investor is passed, it aborts with SQLSTATE `'45000'`.
- Virtual generated column `active_investor_id` enforces a database-level unique key `uq_active_client_investor`, making it impossible for an investor to be assigned to two active brokers at once.

---

### Feature 17: Client Portfolio & Trade Inspection (Tenant Isolated)

#### 1. What the User Clicks
- Broker clicks on client **"Rahul Verma"** to inspect his portfolio.

#### 2. Backend Route & Isolation Verification (`routes/broker.py`)
- First verifies that Rahul (ID 4) is currently assigned to Broker Arun (ID 2):
  ```sql
  SELECT id FROM Broker_Clients 
  WHERE broker_id = 2 AND investor_id = 4 AND status = 'ACTIVE';
  ```
  *If no active relationship exists, Flask immediately returns `HTTP 404 Not Found`*.
- If verified, queries Rahul's holdings and trades:
  ```sql
  SELECT * FROM v_broker_client_transactions 
  WHERE broker_id = 2 AND user_id = 4;
  ```

---

### Feature 18: Terminate Advisory Relationship

#### 1. What the User Clicks
- Broker clicks **"End Advisory"** on a client card.

#### 2. Database Query Executed
```sql
UPDATE Broker_Clients 
SET status = 'INACTIVE', 
    terminated_at = CURRENT_TIMESTAMP 
WHERE broker_id = 2 AND investor_id = 4 AND status = 'ACTIVE';
```

---

### Feature 19: Brokerage Commission Analytics (40% Platform Split)

#### 1. What the User Clicks
- Broker clicks **"Commission Analytics"**.

#### 2. Database Query (`v_broker_commissions`)
```sql
SELECT 
    commission_id, transaction_id, investor_id, investor_name,
    stock_symbol, transaction_amount, brokerage_fee,
    commission_amount, created_at
FROM v_broker_commissions
WHERE broker_id = 2
ORDER BY created_at DESC;
```
- Displays total cumulative commissions earned and daily earnings chart.

---

# 6. System Administrator Features

---

### Feature 20: Platform Overview & Global KPIs

#### 1. What the User Clicks
- Administrator logs in and opens **"Overview"**.

#### 2. Database Queries Executed
```sql
-- 1. Global trading turnover and collected brokerage fees
SELECT 
    total_trades, total_units_traded, total_gross_turnover,
    total_brokerage_collected, total_commissions_paid, net_platform_revenue
FROM v_admin_trade_facts;

-- 2. System user counts
SELECT role, COUNT(*) AS count FROM Users GROUP BY role;

-- 3. Listed equities count
SELECT COUNT(*) FROM Stocks WHERE is_active = TRUE;
```

---

### Feature 21: Listed Equity CRUD (Add / Edit Company)

#### 1. What the User Clicks
- Admin clicks **"Add Listed Equity"**.
- Fills: Symbol (`ZOMATO`), Company Name (`Zomato Ltd`), Sector (`Retail & Consumer Services`), Exchange (`NSE`), Initial Price (`₹260.00`).
- Clicks **"Save Equity"**.

#### 2. Database Queries Executed
```sql
-- 1. Insert master stock row
INSERT INTO Stocks (symbol, company_name, sector, exchange, is_active)
VALUES ('ZOMATO', 'Zomato Ltd', 'Retail & Consumer Services', 'NSE', TRUE);

-- 2. Initialize 1:1 Current_Prices quote record
INSERT INTO Current_Prices (stock_id, price, previous_close, volume, day_open, day_high, day_low)
VALUES (LAST_INSERT_ID(), 260.00, 260.00, 0, 260.00, 260.00, 260.00);
```

---

### Feature 22: User Account Administration & Lockout Reset

#### 1. What the User Clicks
- Admin opens **"User Accounts"**.
- Finds a locked-out user (e.g. `investor_vikram`), and clicks **"Reset Security Lockout"**.

#### 2. Database Queries Executed
```sql
-- Query user security audit view
SELECT user_id, username, email, role, status, failed_login_attempts, locked_until
FROM v_admin_user_audit;

-- Reset lockout
UPDATE Users 
SET failed_login_attempts = 0, 
    locked_until = NULL 
WHERE id = 6;

-- Log admin action
INSERT INTO Audit_Logs (user_id, action, ip_address, details)
VALUES (1, 'ADMIN_RESET_LOCKOUT', '127.0.0.1', 'Reset lockout for user_id 6');
```

---

### Feature 23: Security Audit Log Inspection

#### 1. What the User Clicks
- Admin clicks **"Security Audit Logs"**.

#### 2. Database Query (`v_admin_audit_logs`)
```sql
SELECT log_id, user_id, username, role, action, ip_address, details, created_at
FROM v_admin_audit_logs
ORDER BY created_at DESC
LIMIT 500;
```
*Immutability Guard*: Triggers `trg_audit_logs_block_update` and `trg_audit_logs_block_delete` prevent any modification of these rows.

---

### Feature 24: Market Simulator Real-Time Controls

#### 1. What the User Clicks
- Admin opens **"Simulator Controls"**.
- Adjusts the Tick Speed slider (e.g. from 0.50s to 0.10s) or clicks **"Pause Simulation"**.

#### 2. Backend Action (`routes/admin.py` $\to$ `services/market_simulator.py`)
- Sends:
  ```http
  POST /admin/api/v1/admin/simulator/control
  {"action": "set_interval", "interval": 0.10}
  ```
- Calls `MarketSimulator.get_instance().set_interval(0.10)`. The background thread immediately adjusts its sleep timing without restarting the server.

---

### Feature 25: Automated 7-Point Financial Reconciliation Audit

#### 1. What the User Clicks
- Admin clicks **"Run Financial Reconciliation"**.

#### 2. Database Stored Procedure Execution
```sql
CALL sp_reconcile_financial_integrity();
```

**The 7 Invariants Verified**:
1. **Cash Balance Invariant**: Does `Accounts.virtual_balance` match the exact sum of all signed amounts in `Account_Ledger`?
2. **Holdings Quantity Invariant**: Does each investor's holding quantity match $\sum \text{BUY} - \sum \text{SELL}$?
3. **Transaction Completeness**: Are there any completed orders missing a transaction receipt?
4. **Ledger Completeness**: Are there any trade transactions missing double-entry ledger entries?
5. **Commission Rule Integrity**: Does every broker commission equal exactly $\text{fee} \times 0.40$?
6. **No Duplicate Executions**: Are there any orders with multiple transactions?
7. **Opening Grant Verification**: Does every investor have exactly one ₹100,000 opening grant in the ledger?

#### 3. Output
- Returns `status: "PASS"` with 0 discrepancies found across all 7 checks.

---

# 7. AI Text-to-SQL Assistant & Manual SQL Features

---

### Feature 26: AI Natural-Language SQL Generation & Execution

#### 1. What the User Clicks
- User opens `/ai/assistant`.
- Types a prompt in plain English, e.g.:
  - *"Show me all banking stocks"*
  - *"Give me stocks whose price is greater than 1,000"*
  - *"List accounts with failed login attempts"*
- Clicks **"Ask AI"**.

#### 2. Frontend Action (`AssistantView.jsx`)
- Sends:
  ```http
  POST /ai/api/v1/ai/query
  {"prompt": "Give me stocks whose price is greater than 1,000"}
  ```

#### 3. Multi-Stage Pipeline Execution in Backend (`routes/ai.py`)
1. **Stage 1: Intent & Entity Resolution (`IntentService`)**:
   - Parses prompt: extracts `domain = "MARKET_EQUITIES"`, `price_operator = ">"`, `price_value = 1000.0`.
2. **Stage 2: Schema RAG & LLM Routing (`LLMRouter`)**:
   - Connects to Groq (`openai/gpt-oss-120b`) via Windows Certificate Store (`truststore`).
   - LLM generates structured JSON:
     ```json
     {
       "sql": "SELECT symbol, company_name, sector, current_price, day_change_pct, volume FROM v_market_latest WHERE current_price > 1000 ORDER BY current_price DESC LIMIT 500;",
       "tables": ["v_market_latest"],
       "explanation": "Retrieves stocks with current market price exceeding ₹1,000.00."
     }
     ```
3. **Stage 3: AST Allowlist Validation (`SQLValidator` via `sqlglot`)**:
   - Confirms statement is a single parseable `SELECT`.
   - Rejects stacked queries (`;`), mutations (`INSERT`, `UPDATE`, `DELETE`, `DROP`), and disallowed base tables (`Users`, `Accounts`).
4. **Stage 4: Semantic Consistency Guard (`SemanticValidator`)**:
   - Verifies that `current_price` filter is actually present in the `WHERE` clause.
5. **Stage 5: Scoped Database Execution (`QueryExecutor`)**:
   - Connects using dedicated read-only database user `stocktrade_ai_ro`.
   - Executes session constraints before running the query:
     ```sql
     SET SESSION TRANSACTION READ ONLY;
     SET @current_user_id = 4;
     SET max_execution_time = 5000;

     SELECT symbol, company_name, sector, current_price, day_change_pct, volume 
     FROM v_market_latest 
     WHERE current_price > 1000 
     ORDER BY current_price DESC 
     LIMIT 500;
     ```
6. **Stage 6: Grounded Analysis**:
   - Summarizes rows returned (e.g. 65 stocks retrieved, top gainer identified).
   - Ingests record into `AI_Query_History`.

#### 4. Screen Update
- Displays the **Assistant Direct Answer** summary, query execution time (e.g. 43ms), the generated SQL box with copy button, and an interactive data table with chart toggle buttons (Bar, Line, Donut).

---

### Feature 27: Manual SQL Mode (AST-Validated Execution)

#### 1. What the User Clicks
- User clicks the **"Manual SQL"** tab.
- Types a raw SQL query (e.g. `SELECT symbol, current_price FROM v_market_latest WHERE sector = 'Banking';`).
- Clicks **"Run Query"**.

#### 2. Backend Route (`POST /ai/api/v1/ai/execute`)
- Query is checked by `SQLValidator` for AST safety.
- If safe, executes under `stocktrade_ai_ro` with a 5000ms query timeout.
- Returns columns and result rows to the screen.

---

### Feature 28: AI Query History & Audit Log

#### 1. What the User Clicks
- User clicks **"Query History"** tab.

#### 2. Database Query (`AI_Query_History`)
```sql
SELECT 
    query_id, prompt, generated_sql, tables_used,
    validation_status, execution_status, duration_ms,
    row_count, provider, created_at
FROM AI_Query_History
WHERE user_id = :current_user_id
ORDER BY created_at DESC;
```
- Displays complete audit history of all prompts asked, models used, and execution speeds.

---

# Summary Matrix: Buttons, Endpoints & Database Objects

| UI Feature / Button | Frontend Page | HTTP Endpoint | Primary Database Object / Query |
| :--- | :--- | :--- | :--- |
| **Sign In** | `Login.jsx` | `POST /api/v1/auth/login` | `SELECT Users` $\to$ `UPDATE Users` $\to$ `INSERT Audit_Logs` |
| **Sign Out** | `Navbar.jsx` | `POST /api/v1/auth/logout` | `INSERT Audit_Logs` |
| **Market Screener** | `MarketView.jsx` | `GET /market/api/v1/market/prices` | `SELECT * FROM v_market_latest` |
| **View Stock Chart** | `StockChartModal.jsx` | `GET /market/api/v1/market/stocks/<id>/history` | `SELECT * FROM Stock_Prices` |
| **Execute BUY Order** | `TradeTicketModal.jsx` | `POST /investor/api/v1/investor/orders` | `CALL sp_execute_trade(..., 'BUY', ...)` |
| **Execute SELL Order** | `TradeTicketModal.jsx` | `POST /investor/api/v1/investor/orders` | `CALL sp_execute_trade(..., 'SELL', ...)` |
| **Deposit Cash** | `DepositModal.jsx` | `POST /investor/api/v1/investor/deposit` | `UPDATE Accounts` $\to$ `INSERT Account_Ledger` |
| **Export Trades CSV** | `TransactionsView.jsx` | `GET /reports/export/transactions` | `SELECT * FROM v_investor_transactions` |
| **Star / Unstar Ticker** | `MarketView.jsx` | `POST / DELETE /investor/api/v1/investor/watchlist` | `INSERT / DELETE FROM Watchlist` |
| **Set Price Alert** | `AlertsModal.jsx` | `POST /investor/api/v1/investor/alerts` | `INSERT INTO Price_Alerts` |
| **Client Roster** | `BrokerClientsView.jsx` | `GET /broker/api/v1/broker/clients` | `SELECT * FROM v_broker_client_summary` |
| **Onboard Client** | `OnboardClientModal.jsx` | `POST /broker/api/v1/broker/clients` | `INSERT INTO Broker_Clients` *(role triggers checked)* |
| **Commission Analytics**| `CommissionsView.jsx` | `GET /broker/api/v1/broker/commissions` | `SELECT * FROM v_broker_commissions` |
| **Add Listed Company** | `ListedCompaniesView.jsx` | `POST /admin/api/v1/admin/stocks` | `INSERT INTO Stocks` $\to$ `INSERT Current_Prices` |
| **Reset User Lockout** | `UserAccountsView.jsx` | `POST /admin/api/v1/admin/users/<id>/reset-lockout` | `UPDATE Users SET failed_login_attempts=0, locked_until=NULL` |
| **Simulator Speed** | `SimulatorControlsView.jsx`| `POST /admin/api/v1/admin/simulator/control` | `MarketSimulator.set_interval()` |
| **Reconcile Finances** | `AdminDashboard.jsx` | `POST /admin/api/v1/admin/reconcile` | `CALL sp_reconcile_financial_integrity()` |
| **Ask AI** | `AssistantView.jsx` | `POST /ai/api/v1/ai/query` | Groq LLM $\to$ `sqlglot` $\to$ `SELECT v_...` under `stocktrade_ai_ro` |
