# STOCKTRADE (v2) — MASTER PRODUCT & TECHNICAL SPECIFICATION
> **Document Purpose**: Complete, self-contained architecture, schema, business logic, and API reference for StockTrade. Designed to be fed directly to ChatGPT or any AI assistant to understand the existing codebase, add advanced fintech features, or refactor to enterprise grade.

---

## 1. Executive Summary & Project Identity

* **Product Name**: StockTrade (v2)
* **Type**: Fintech-grade simulated stock trading platform (College DBMS Capstone Project).
* **Core Philosophy**: **Virtual Money Only**. No real money, payment gateways, or live broker exchange APIs. All prices are evolved by an autonomous, deterministic, mean-reverting simulation engine.
* **Primary Objective**: Demonstrate relational database design (3NF), ACID transactions, pessimistic concurrency control, append-only financial audit ledgers, database triggers, stored procedures, multi-tenant RBAC, and safe AI-to-SQL query generation.
* **Operating Environment**: Runs locally on Windows in VS Code using Python 3.11+, Flask 3, MySQL 8.0 (InnoDB), and React 18 (Vite SPA).
* **Guiding Invariants**:
  1. $\text{Accounts.virtual\_balance} == \sum \text{Account\_Ledger.signed\_amounts}$ (zero drift).
  2. $\text{Holdings.quantity} == \sum \text{Orders(BUY).quantity} - \sum \text{Orders(SELL).quantity}$.
  3. Financial rows (`Account_Ledger`, `Orders`, `Transactions`, `Audit_Logs`) are **never deleted or updated**.

---

## 2. Technology Stack

| Layer | Choice | Rationale & Configuration |
|---|---|---|
| **Language** | Python 3.11+ | Backend logic, type annotations, `decimal.Decimal` precision. |
| **Backend Framework** | Flask 3.x | Application factory pattern (`create_app`), modular Blueprints, Jinja2 filters. |
| **Database** | MySQL 8.0+ | InnoDB storage engine, `utf8mb4` charset, `READ COMMITTED` transaction isolation. |
| **Data Access** | SQLAlchemy 2.x Core | Parameterized explicit SQL queries, connection pooling via `URL.create()`. |
| **Frontend** | React 18 + Vite | Single-Page Application (SPA) with Lucide React icons and Chart.js. |
| **CSS / Design System** | Custom CSS Variables | Inter font, tabular figures (`font-variant-numeric: tabular-nums`), Indian rupee formatting. |
| **Charts** | Chart.js 4.x + `react-chartjs-2` | Multi-interval OHLC candlesticks & area line charts (1m, 5m, 1h). |
| **Market Simulator** | APScheduler 3.x | Background worker with MySQL advisory lock (`SELECT GET_LOCK('stocktrade_simulator', 0)`). |
| **SQL Parser & Security**| `sqlglot` (MySQL dialect) | Abstract Syntax Tree (AST) validation for the AI Assistant. |
| **AI Providers** | Multi-Provider Failover Router | Grok (xAI) &rarr; Google Gemini &rarr; OpenRouter &rarr; Deterministic Local Fallback. |
| **Authentication** | Flask-Login + Werkzeug | Server-side sessions, `scrypt` password hashing, 5-attempt brute-force lockout (15 min). |
| **Security & CSRF** | Flask-WTF + Security Headers | CSRF tokens in headers (`X-CSRFToken`), `SAMEORIGIN`, `nosniff`, CSV DDE sanitization. |
| **Testing** | `pytest` + `pytest-cov` | 43 unit, integration, concurrency (20 threads), and security tests (100% pass rate). |

---

## 3. Financial & Business Rules

### 3.1 Precision & Number Formatting
* **Money**: `DECIMAL(15,2)` in MySQL; `decimal.Decimal` with `ROUND_HALF_UP` in Python. Floats are **strictly forbidden** for monetary calculations.
* **Stock Prices**: `DECIMAL(12,4)` in MySQL.
* **Quantities**: Positive integers (`BIGINT` or `INT >= 1`).
* **Indian Rupee Formatting**: ₹ symbol with Lakh/Crore grouping (e.g., `₹1,00,000.00`).

### 3.2 Opening Balance & Grants
* Every newly onboarded investor receives an opening virtual cash grant of **₹1,00,000.00** written directly to `Accounts` and recorded in `Account_Ledger` as entry type `OPENING_GRANT`.

### 3.3 Charges & Brokerage (Investor-Paid)
$$\text{brokerage} = \max(\text{min\_fee}, \text{trade\_value} \times \text{rate})$$
* **Default Rate**: $0.10\%$ ($0.0010$).
* **Minimum Fee**: ₹1.00.
* Stored in `Commission_Rules` under rule type `INVESTOR_BROKERAGE`. Charged on **both BUY and SELL** orders and logged as separate `FEE` ledger entries.

### 3.4 Broker Commission (Platform-Funded)
$$\text{broker\_commission} = \text{brokerage\_collected} \times 40\%$$
* Stored in `Commission_Rules` under rule type `BROKER_COMMISSION`.
* **Platform-Funded**: It is an internal platform expense paid to the assigned broker; it is **never deducted from the investor**.
* Recorded in the `Commissions` table with `status = 'EARNED'`. Independent investors without an assigned broker generate ₹0 broker commission.

### 3.5 Cost Basis & P&L Formulas
* **On BUY**: Weighted average cost basis:
  $$\text{new\_avg\_cost} = \frac{(\text{old\_qty} \times \text{old\_avg}) + (\text{new\_qty} \times \text{exec\_price})}{\text{old\_qty} + \text{new\_qty}}$$
  *(Brokerage is tracked as a separate fee and is not capitalized into average cost).*
* **On SELL**: Realized P&L:
  $$\text{realized\_pnl} = (\text{sell\_price} - \text{avg\_cost}) \times \text{sell\_qty} - \text{sell\_brokerage}$$
  *(Average cost basis does NOT change upon partial sale).*
* **Portfolio Metrics**:
  * $\text{Available Cash} = \sum \text{Ledger Signed Amounts}$
  * $\text{Holdings Market Value} = \sum (\text{holding\_qty} \times \text{current\_price})$
  * $\text{Total Portfolio Value} = \text{Available Cash} + \text{Holdings Market Value}$
  * $\text{Unrealized P\&L} = \sum (\text{holding\_qty} \times (\text{current\_price} - \text{avg\_cost}))$
  * $\text{Return \%} = \frac{\text{Total P\&L}}{\text{Invested Cost Basis}} \times 100$

### 3.6 Virtual Cash Deposit Policy
* Investors can add virtual funds up to **₹50,000.00 per day** (`MAX_DAILY_DEPOSIT_INR`). Deposits are recorded in `Account_Ledger` as `DEPOSIT`.

---

## 4. Database Architecture (21 Tables, Views, Stored Procedures & Triggers)

### 4.1 Schema Overview
1. **`Users`**: User identity, roles (`ADMIN`, `BROKER`, `INVESTOR`), status (`ACTIVE`, `INACTIVE`), `failed_login_attempts`, `locked_until`, `is_demo`.
2. **`Accounts`**: Financial balance (`virtual_balance`), currency (`INR`), status (`ACTIVE`, `FROZEN`, `CLOSED`). `CHECK (virtual_balance >= 0)`.
3. **`Account_Ledger`**: Double-entry append-only ledger (`OPENING_GRANT`, `DEPOSIT`, `BUY`, `SELL`, `FEE`, `ADJUSTMENT`), `balance_after`, `reference_type`, `reference_id`.
4. **`Stocks`**: 100 listed equities across 14 sectors (`symbol`, `company_name`, `sector`, `exchange`, `base_price`, `status`).
5. **`Current_Prices`**: Deliberately denormalized 1-row-per-stock quote cache (`price`, `previous_close`, `day_open`, `day_high`, `day_low`, `volume`, `updated_at`) for $O(1)$ read locks during trade execution.
6. **`Stock_Prices`**: Immutable historical time-series observations (`stock_id`, `price`, `volume`, `source`, `recorded_at`). Composite index: `(stock_id, recorded_at)`.
7. **`Orders`**: Order ticket (`BUY`/`SELL`, `status` in `PENDING`, `EXECUTED`, `REJECTED`, `CANCELLED`, `FAILED`), `quantity > 0`, `idempotency_key` (unique per user).
8. **`Holdings`**: Open positions per user & stock (`quantity >= 0`, `average_buy_price`). Unique key `(user_id, stock_id)`.
9. **`Transactions`**: Execution audit log linked to orders (`gross_amount`, `brokerage_fee`, `net_amount`, `executed_at`).
10. **`Broker_Clients`**: Multi-tenant broker assignments (`broker_id`, `investor_id`, `status` in `ACTIVE`, `TERMINATED`).
11. **`Commission_Rules`**: Platform rule matrix (`INVESTOR_BROKERAGE`, `BROKER_COMMISSION`), rates, min fees, `effective_from`.
12. **`Commissions`**: Accrued broker payout records linked to `transaction_id`.
13. **`Price_Alerts`**: User target price triggers (`ABOVE`, `BELOW`, `TRIGGERED`).
14. **`Watchlist`**: User saved tickers.
15. **`Audit_Logs`**: Security and admin action trail (`user_id`, `action`, `entity_type`, `payload`, `ip_address`).
16. **`AI_Query_History`**: Audit trail of AI prompts, generated SQL, AST validation verdicts, and execution timings.
17. **`Saved_Reports`**: Custom saved reporting queries.
18. **`System_Settings`**: Key-value system configurations.
19. **`System_Events`**: Background worker and critical error events.

### 4.2 Stored Procedure: `sp_execute_trade`
Executes market orders inside MySQL in a single transaction under **fixed row-locking order** to guarantee deadlock immunity and prevent concurrency race conditions:
1. `SELECT ... FOR UPDATE` on `Accounts` (locks user cash balance).
2. `SELECT ... FOR UPDATE` on `Holdings` (locks existing position).
3. `SELECT ... FOR SHARE` on `Current_Prices` (reads authoritative live price).
4. **Validation**: Checks balance (on BUY) or holding quantity (on SELL). If insufficient, marks order `REJECTED` and commits without state corruption.
5. **Execution**: Updates balance, updates/inserts holding with weighted average cost, records `Orders` as `EXECUTED`, inserts `Transactions`, and writes 2 `Account_Ledger` entries (`BUY`/`SELL` + `FEE`).
6. **Idempotency**: Replaying the same `idempotency_key` returns the existing executed order without double-spending.

### 4.3 Database Triggers
* **`trg_ledger_block_update`**: `BEFORE UPDATE ON Account_Ledger` &rarr; `SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Account_Ledger is strictly append-only. UPDATE is prohibited.'`.
* **`trg_ledger_block_delete`**: `BEFORE DELETE ON Account_Ledger` &rarr; `SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Account_Ledger is strictly append-only. DELETE is prohibited.'`.
* **`trg_broker_client_role_check`**: Validates that `broker_id` has role `BROKER` and `investor_id` has role `INVESTOR` before linking.

### 4.4 Database Views (Safe AI & Reporting Layer)
* **`v_market_latest`**: Stock tickers, company names, sectors, latest price, day change, % change, day high/low/volume.
* **`v_investor_portfolio`**: User-specific holdings, market values, cost basis, unrealized P&L, scoped by `user_id = @current_user_id`.
* **`v_investor_transactions`**: Historical executions with gross/net amounts and fees.
* **`v_broker_client_summary`**: Client count, aggregate client balances, and total trading volume for brokers.
* **`v_admin_trade_facts`**: System-wide volume, fee accruals, active users, and order counts.

---

## 5. Market Simulation Engine

* **Process Model**: Discrete **Ornstein-Uhlenbeck (OU) Mean-Reverting Bounded Random Walk**:
  $$S_{t+1} = S_t + \theta (\mu - S_t) \Delta t + \sigma S_t \epsilon \sqrt{\Delta t}$$
  * $\theta = 0.05$ (mean reversion speed toward base reference price $\mu$).
  * $\sigma = 0.015$ (volatility component).
  * $\epsilon \sim \mathcal{N}(0, 1)$ (Gaussian random shock).
* **Advisory Lock Concurrency**: The APScheduler background worker invokes `SELECT GET_LOCK('stocktrade_simulator', 0)` before ticking. Only one process holds the lock; secondary processes or gunicorn workers skip ticks cleanly.
* **OHLC Dynamic Candlestick Aggregation**: Rather than storing pre-computed candles, MySQL aggregates historical `Stock_Prices` rows on-the-fly:
  ```sql
  SELECT 
      FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(recorded_at) / :interval) * :interval) AS bucket_start,
      SUBSTRING_INDEX(GROUP_CONCAT(price ORDER BY recorded_at ASC), ',', 1) AS open_price,
      MAX(price) AS high_price,
      MIN(price) AS low_price,
      SUBSTRING_INDEX(GROUP_CONCAT(price ORDER BY recorded_at DESC), ',', 1) AS close_price,
      SUM(volume) AS volume
  FROM Stock_Prices
  WHERE stock_id = :stock_id AND recorded_at >= :start_time
  GROUP BY bucket_start ORDER BY bucket_start ASC;
  ```

---

## 6. Five-Layer AI-to-SQL Assistant Architecture

Allows natural language queries over the database without security or tenant leakage risks:

```
[User NL Prompt] 
      │
      ▼
[Layer 1: RAG View Schema Grounding] (Only authorized views provided in prompt context)
      │
      ▼
[Multi-Provider Failover LLM Router] (Grok -> Gemini -> OpenRouter -> Local Template Fallback)
      │
      ▼
[Layer 2: sqlglot AST Validator] (Enforces SELECT-only, no mutations/DDL, function allowlist)
      │
      ▼
[Layer 3: MySQL User Isolation] (Executed via stocktrade_ai_ro with SELECT-only grants)
      │
      ▼
[Layer 4: Session Tenancy Scoping] (Executes SET @current_user_id = :session_user_id)
      │
      ▼
[Layer 5: Grounded Result Summarizer] (Strictly summarizes returned database rows)
```

---

## 7. Security & Hardening Controls

1. **Role-Based Access Control (RBAC)**: Enforced via `@role_required("INVESTOR"|"BROKER"|"ADMIN")` decorator. Identity is extracted strictly from the server-side session (`current_user.id`), never from request parameters.
2. **Tenant Isolation (404 Not Found Policy)**: When a broker requests an investor's profile not assigned to them, the backend returns `404 Not Found` (never 403), preventing user enumeration.
3. **Brute Force Lockout**: 5 failed login attempts locks the account for 15 minutes in `Users.locked_until`.
4. **Session Fixation Defense**: `session.clear()` on login rotates session keys.
5. **CSV Formula Injection (DDE) Sanitization**: All cells in CSV exports beginning with `=`, `+`, `-`, `@`, `\t`, `\r` are prefixed with `'` to prevent spreadsheet code execution.
6. **CSRF Protection**: All state-changing endpoints require `X-CSRFToken` verification. Authentication endpoints are explicitly exempt to permit seamless SPA login.

---

## 8. Complete REST API Specification

### Authentication
* `POST /api/v1/auth/login`: `{ identifier, password }` &rarr; Authenticates user, creates session.
* `POST /api/v1/auth/logout`: Clears session cookie.
* `GET  /api/v1/auth/session`: Returns `{ authenticated: bool, csrf_token: str, user: object }`.
* `GET  /api/v1/auth/me`: Returns current user info.

### Market
* `GET /market/api/v1/market/prices`: Returns latest quotes for all 100 stocks. Supports `?since=` delta polling.
* `GET /market/api/v1/market/history`: Returns OHLC candles. Params: `symbol`, `interval` (`1m`, `5m`, `1h`).
* `GET /market/api/v1/market/status`: Returns simulator health, tick count, indicator (`green`, `amber`, `red`).

### Investor
* `GET  /investor/api/v1/investor/summary`: Returns `{ available_cash, holdings_market_value, portfolio_value, unrealized_pnl, realized_pnl }`.
* `GET  /investor/api/v1/investor/holdings`: Returns open positions with average cost basis.
* `GET  /investor/api/v1/investor/transactions`: Returns trade history.
* `POST /investor/api/v1/investor/orders` (or `/trade`): `{ stock_id, side: "BUY"|"SELL", quantity, idempotency_key, quoted_price }`.
* `POST /investor/api/v1/investor/deposit`: `{ amount }` (up to ₹50,000/day).
* `GET  /api/v1/reports/transactions-csv`: Downloads formula-sanitized transaction history CSV.

### Broker
* `GET  /broker/api/v1/broker/clients`: Lists active assigned clients.
* `POST /broker/api/v1/broker/clients`: Onboards new client `{ username, email, full_name, password, phone }`.
* `GET  /broker/api/v1/broker/client-profile?investor_id=X`: Returns client portfolio (404 enforced if unassigned).
* `POST /broker/api/v1/broker/clients/<id>/end`: Terminates assignment.
* `GET  /broker/api/v1/broker/analytics`: Returns commission totals and trade volumes.

### Admin
* `GET    /admin/api/v1/admin/overview`: Returns platform counts (users, capital, stocks, orders).
* `GET    /admin/api/v1/admin/companies`: Searchable list of equities.
* `POST   /admin/api/v1/admin/companies`: Lists new stock.
* `PUT    /admin/api/v1/admin/companies/<id>`: Updates stock details.
* `DELETE /admin/api/v1/admin/companies/<id>`: Guarded hard-delete (fails if orders/holdings exist).
* `GET    /admin/api/v1/admin/users`: Lists all users, failed logins, lockout statuses.
* `PATCH  /admin/api/v1/admin/users/<id>/status`: Toggles `ACTIVE`/`INACTIVE`.
* `POST   /admin/api/v1/admin/users/<id>/reset-lockout`: Clears failed login counter and lockout.
* `GET    /admin/api/v1/admin/simulator/status`: Simulator state.
* `POST   /admin/api/v1/admin/simulator/control`: `{ action: "pause"|"resume"|"tick" }`.
* `GET    /admin/api/v1/admin/audit-logs`: Filterable audit log stream.

### AI Assistant
* `POST /ai/api/v1/ai/query`: `{ prompt: str }` &rarr; Returns `{ generated_sql, provider_used, ast_validated, results, summary }`.
* `POST /ai/api/v1/ai/generate`: Stage 1 SQL generation.
* `POST /ai/api/v1/ai/execute`: Stage 2 execution.
* `GET  /ai/api/v1/ai/providers`: LLM provider health check.

---

## 9. Project Codebase & Directory Map

```
DBMSPRJ/
├── app.py                      # Flask 3 app factory, Blueprints, SPA fallback, security headers
├── config.py                   # Environment configs (Development, Testing, Production)
├── requirements.txt            # Pinned Python dependencies
├── init_db.py                  # Idempotent DB provisioning & 7-day price backfill
├── init_db.ps1                 # PowerShell DB initializer runner
├── start.ps1                   # One-click startup script (Flask + Simulator + React SPA)
├── run_tests.ps1               # Pytest suite runner with coverage
├── query_db.ps1                # PowerShell MySQL CLI query runner
│
├── database/                   # Authoritative Database DDL & Seed Scripts
│   ├── schema.sql              # 21 tables, check constraints, foreign keys
│   ├── indexes.sql             # Composite indexes (time-series, orders, ledger)
│   ├── views.sql               # Safe views (v_market_latest, v_investor_portfolio, etc.)
│   ├── triggers.sql            # Ledger immutability triggers (block UPDATE/DELETE)
│   ├── procedures.sql          # sp_execute_trade atomic market order stored procedure
│   ├── seed_companies.sql      # 100 Indian equities across 14 sectors
│   ├── seed_demo_users.sql     # Admin, 2 Brokers, 6 Investors with opening grants
│   ├── seed_settings_rules.sql # Commission rules (0.10% fee, 40% broker commission)
│   └── backfill_prices.py      # Generates 7-day 1-minute historical prices
│
├── models/                     # Core Database & User Entities
│   ├── db.py                   # SQLAlchemy 2.x Core pool manager (URL.create escaping)
│   ├── schema.py               # Table schema definitions for SQLAlchemy Core
│   └── user.py                 # Flask-Login User model wrapper
│
├── repositories/               # Pure Data Access Layer (Parameterised SQL)
│   ├── user_repo.py            # User CRUD, failed login tracking, lockouts
│   ├── account_repo.py         # Balances, deposits, account statuses
│   ├── stock_repo.py           # Equities, quotes, company CRUD
│   ├── order_repo.py           # Order creation & retrieval
│   ├── holding_repo.py         # Open positions & weighted avg cost basis
│   ├── transaction_repo.py     # Execution records
│   ├── ledger_repo.py          # Append-only ledger inserts & balance sums
│   ├── broker_repo.py          # Client assignments & commission calculations
│   └── audit_repo.py           # Security and audit log records
│
├── services/                   # Core Business & Algorithmic Logic
│   ├── auth_service.py         # Authenticate, brute-force lockout, @role_required
│   ├── trading_service.py      # sp_execute_trade wrapper & deposit limits
│   ├── portfolio_service.py    # Mark-to-market calculations & double reconciliation
│   ├── market_simulator.py     # APScheduler Ornstein-Uhlenbeck worker + MySQL advisory lock
│   ├── llm_router.py           # Multi-provider failover router (Grok -> Gemini -> OpenRouter)
│   ├── rag_service.py          # Role-based view schema grounding & template library
│   ├── sql_validator.py        # sqlglot AST parser & mutation blocker
│   └── query_executor.py       # Scoped read-only query execution (@current_user_id)
│
├── routes/                     # Blueprint Route Controllers
│   ├── auth.py                 # /api/v1/auth/login, logout, session
│   ├── market.py               # /market/api/v1/market/prices, history, status
│   ├── investor.py             # /investor/api/v1/investor/summary, holdings, trade, deposit
│   ├── broker.py               # /broker/api/v1/broker/clients, client-profile, analytics
│   ├── admin.py                # /admin/api/v1/admin/overview, companies, users, simulator
│   ├── ai.py                   # /ai/api/v1/ai/query, generate, execute
│   └── reports.py              # /api/v1/reports/transactions-csv (formula sanitized)
│
├── frontend/                   # Modern React 18 SPA (Vite)
│   ├── package.json            # React, Vite, Chart.js, Lucide icons
│   ├── vite.config.js          # Proxy to http://127.0.0.1:5000, build outDir: ../static/dist
│   ├── index.html              # HTML5 template with Inter font
│   └── src/
│       ├── main.jsx            # Entry point with AuthProvider
│       ├── App.jsx             # Top-level view router and global modals
│       ├── api/client.js       # Centralized fetch wrapper with CSRF extraction
│       ├── context/AuthContext # Auth state, login/logout, CSRF token management
│       ├── styles/index.css    # Design tokens, tabular nums, flash animations, modals
│       ├── utils/formatters.js # Indian numbering (₹, Lakh/Crore), %, quantities
│       ├── components/
│       │   ├── Navbar.jsx      # Topbar, brand, Ctrl+K stock search, user menu
│       │   ├── Sidebar.jsx     # Role-based navigation consoles
│       │   ├── SimulatedBadge  # Real-time simulation health dot (green/amber/red)
│       │   ├── KpiTile.jsx     # Tabular KPI cards with gain/loss badges
│       │   ├── StockChartModal # Chart.js 1m/5m/1h OHLC candlesticks & line chart
│       │   ├── TradeTicketModal# BUY/SELL ticket, fee breakdown, confirmation dialog
│       │   ├── DepositModal.jsx# Instant virtual deposit with ₹50,000 daily validation
│       │   └── OnboardClient   # Broker client registration modal
│       └── pages/
│           ├── Login.jsx       # Auth screen with 1-click evaluation accounts
│           ├── investor/       # DashboardView, MarketView, PortfolioView, TransactionsView
│           ├── broker/         # ClientsView (drawer + 404 policy), AnalyticsView
│           ├── admin/          # OverviewView, CompaniesView, UsersView, SimulatorView, Audit
│           └── ai/             # AssistantView (NL prompt, AST badge, SQL view, data table)
│
├── static/dist/                # Production build output generated by Vite
├── docs/                       # Comprehensive Architecture & Viva Documentation
│   ├── DECISIONS.md            # Architectural decisions log
│   ├── ERD.md                  # Mermaid ER diagram of 21 tables
│   ├── NORMALIZATION.md        # 1NF -> 3NF walk with denormalization justifications
│   ├── API.md                  # REST endpoint reference
│   ├── SECURITY.md             # 5-layer AI security & RBAC documentation
│   ├── DBMS_CONCEPTS.md        # College viva Q&A guide (ACID, Locks, Stored Procs)
│   └── TEST_REPORT.md          # 43-test execution report (100% pass rate)
└── tests/                      # Pytest Automated Test Suite (43 tests)
    ├── conftest.py             # Fixtures for unauthenticated, admin, broker, investor clients
    ├── test_database.py        # Constraints, triggers, sp_execute_trade idempotency
    ├── test_auth.py            # Login, password check, lockout, SPA root serving
    ├── test_trading.py         # Buy/Sell math, realized P&L, fees, deposits
    ├── test_concurrency.py     # 20-thread race condition test without overspend
    ├── test_market.py          # Simulator status, price parity, OHLC aggregation
    ├── test_permissions.py     # Role isolation & RBAC decorators
    ├── test_broker_clients.py  # Client onboarding & 404 tenant isolation
    ├── test_reports.py         # CSV formula injection sanitization
    └── test_ai_sql.py          # AST mutation rejection & multi-provider failover
```

---

## 10. Seed Demo Accounts & Passwords

| Role | Username | Seed Password | Accepted Master Demo Password | Notes |
|---|---|---|---|---|
| **Admin** | `admin` | `Admin@StockTrade2026` | `DemoPassword123!` | System Administrator (Full access) |
| **Broker** | `broker_arun` | `Broker@StockTrade2026` | `DemoPassword123!` | Apex Capital (Manages Rahul, Sneha, Vikram) |
| **Broker** | `broker_priya` | `Broker@StockTrade2026` | `DemoPassword123!` | BlueChip Securities (Manages Ananya, Karan) |
| **Investor** | `investor_rahul` | `Investor@StockTrade2026`| `DemoPassword123!` | Client of Arun Mehta; ₹1,00,000 grant |
| **Investor** | `investor_sneha` | `Investor@StockTrade2026`| `DemoPassword123!` | Client of Arun Mehta; ₹1,00,000 grant |
| **Investor** | `investor_rohit` | `Investor@StockTrade2026`| `DemoPassword123!` | Direct Independent Investor (no broker) |

---

## 11. Feature Expansion Roadmap (Ideas for ChatGPT to Implement Next)

When passing this document to ChatGPT, you can ask it to implement any of the following professional features:

### Tier 1: Advanced Trading Engine Features
1. **Limit & Stop-Loss Orders**: Extend `Orders` table with `order_type ENUM('MARKET','LIMIT','STOP_LOSS')`, `limit_price`, `stop_price`. Update the simulator tick loop to match and execute pending limit orders when market price hits threshold.
2. **Options Trading Simulation (Calls & Puts)**: Add `Options_Contracts` table (`strike_price`, `expiry_date`, `contract_type`) and Black-Scholes pricing engine.
3. **Short Selling & Margin Trading**: Add collateral margin requirements, borrow fees, and liquidation margin call procedures.

### Tier 2: Real-Time & Analytics Upgrades
4. **WebSocket / Server-Sent Events (SSE) Live Feed**: Replace 4-second HTTP polling with SSE or Flask-SocketIO for millisecond-level tick streaming.
5. **Technical Indicators on Charts**: Compute RSI (Relative Strength Index), MACD, Moving Averages (SMA-20, EMA-50), and Bollinger Bands directly in the chart modal.
6. **Portfolio Performance Benchmarking**: Compare investor portfolio return against a simulated NIFTY 50 benchmark index.

### Tier 3: Social & Gamification Features
7. **Leaderboard & Competitions**: Ranks investors by 7-day and 30-day return percentages.
8. **Social Trading & Copy Trading**: Allows investors to follow top-performing public profiles and replicate trades automatically.
9. **PDF Account Statement Generator**: Generates formatted PDF statements for tax year / monthly holdings using ReportLab.

### Tier 4: Enterprise & Regulatory Compliance
10. **Two-Factor Authentication (2FA)**: TOTP authenticator app support (Google Authenticator) with QR code generation.
11. **Simulated KYC & PAN Verification**: Multi-step onboarding workflow with simulated document upload and admin approval queue.
12. **Dark Mode UI Toggle**: Tokenized theme toggle between Light (`#F3F5F7`) and Dark Terminal (`#0B0F19`).

---

## 12. Master Prompt for ChatGPT

Copy and paste the prompt below into ChatGPT along with this file:

```markdown
You are a Principal Full-Stack Engineer, Database Architect, and Fintech Security Lead.
I am providing you with the complete technical specification of my existing, working project: "StockTrade (v2)".

Please review the architecture, MySQL schema, stored procedures, financial invariants, and REST APIs detailed in PRODUCT_SPEC_MASTER.md.

I want to enhance this project to make it even more professional. 
Specifically, I would like you to help me with:
[INSERT YOUR DESIRED FEATURE HERE, e.g.:
 1. Implementing Limit and Stop-Loss orders in the database and UI
 2. Adding Technical Indicators (RSI, MACD) to the StockChartModal
 3. Upgrading price polling to Server-Sent Events (SSE)
 4. Adding a Dark Mode toggle to the React design system
 5. Building an investor leaderboard ranking by return %]

Please provide production-ready, clean, modular code conforming strictly to the existing architecture:
- Maintain DECIMAL(15,2) money precision and double reconciliation invariants.
- Keep database operations parameterized in SQLAlchemy 2.x Core repositories.
- Follow the existing React 18 component structure with Inter font and tabular numerals.
- Ensure all tests pass.
```
