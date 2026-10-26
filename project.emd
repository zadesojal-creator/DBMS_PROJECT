# STOCKTRADE (v2) — MASTER PROJECT ARCHITECTURE & SPECIFICATION

> **Document Classification**: Comprehensive Technical, Database, Architectural, and Operational Manual  
> **System Name**: StockTrade v2  
> **Application Type**: Institutional-Grade Simulated Stock Trading & Relational DBMS Platform  
> **Core Philosophy**: **Virtual Paper Trading Only**. All monetary balances are strictly simulated virtual capital with zero real money exposure, zero third-party broker API dependency, and deterministic financial accounting.  
> **Target Audience**: Software Engineers, Database Architects, Evaluators, Technical Recruiters, and DBMS Professors.

---

## 1. Executive Summary & System Invariants

**StockTrade v2** is a complete, full-stack, enterprise-hardened stock trading simulation and financial accounting web platform. Engineered as a premier Database Management System (DBMS) capstone, it showcases advanced relational database design (3NF), strict ACID transaction guarantees, pessimistic concurrency control, append-only double-entry financial audit ledgers, database triggers, stored procedures, multi-tenant role-based access control (RBAC), an autonomous mean-reverting market simulator, and a secure dual-mode AI SQL Assistant.

### Core Mathematical & Financial Invariants
The system enforces four mathematical invariants that cannot be violated under any concurrency race condition:
1. **Zero Floating-Point Drift**: All monetary values use MySQL `DECIMAL(15,2)` and Python `decimal.Decimal` with `ROUND_HALF_UP`. Floating-point numbers (`FLOAT`/`DOUBLE`) are strictly forbidden in accounting logic.
2. **Double-Entry Ledger Integrity**: An investor's virtual cash balance always exactly equals the sum of all their signed ledger entries:
   $$\text{Accounts.virtual\_balance} \equiv \sum \text{Account\_Ledger.signed\_amount}$$
3. **Holding Position Preservation**: An investor's current open share position strictly equals total historical bought shares minus total historical sold shares:
   $$\text{Holdings.quantity} \equiv \sum \text{Orders(BUY).quantity} - \sum \text{Orders(SELL).quantity}$$
4. **Append-Only Immutability**: Financial records in `Account_Ledger`, `Orders`, `Transactions`, and `Audit_Logs` can **never be updated or deleted**. Database-level triggers intercept and reject any `UPDATE` or `DELETE` statements with SQL state exceptions.

---

## 2. Technology Stack & Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER (Browser)                             │
│  React 18 SPA (Vite) • Lucide React • Chart.js 4.x • Inter Font • Tabular Nums │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ HTTPS / REST (JSON) + SSE
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             APPLICATION LAYER (Flask 3)                         │
│  ├── Blueprints: Auth, Market, Investor, Broker, Admin, AI, Reports             │
│  ├── Security: Flask-Login, Scrypt Hashing, CSRF Defense, 404 Tenant Isolation   │
│  ├── Services: TradingService, PortfolioService, MarketSimulator, LLMRouter      │
│  └── AI Engine: sqlglot AST Validator, Schema RAG Grounder, Read-Only User Pool │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ Parameterized SQL / Stored Procedures
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DATABASE LAYER (MySQL 8.0 InnoDB)                     │
│  ├── 21 Tables: Normal Form (3NF), Check Constraints, Composite Indexes        │
│  ├── Stored Procedures: sp_execute_trade (Pessimistic Row-Locking Order)       │
│  ├── Triggers: trg_ledger_block_update, trg_ledger_block_delete, Role Checks   │
│  └── Views: v_market_latest, v_investor_portfolio, v_admin_trade_facts         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

| Layer | Component | Technical Selection & Purpose |
|---|---|---|
| **Backend Framework** | Python 3.11+ / Flask 3.x | Application factory pattern (`create_app`), Blueprint route segregation, Jinja2 filters, custom error handlers. |
| **Database Engine** | MySQL 8.0+ (InnoDB) | Full ACID compliance, foreign keys with `ON DELETE RESTRICT`, `utf8mb4` character set, `READ COMMITTED` isolation. |
| **Data Access Layer** | SQLAlchemy 2.x Core | Parameterized explicit SQL queries, connection pooling via `URL.create()`, transaction context managers. |
| **Frontend Framework** | React 18 + Vite | Single Page Application (SPA), client-side state routing, hot-module reload, production build out to `static/dist`. |
| **UI & Styling** | Custom Fintech Design System | 60/40 asymmetrical split login gateway, charging bull geometric brandmark, live moving marquee ticker tape, tactile inputs. |
| **Charting Engine** | Chart.js 4.x + `react-chartjs-2` | Interactive multi-interval candlestick/area charts (1m, 5m, 1h) with volume histograms. |
| **Market Simulator** | Python Background Thread | Ornstein-Uhlenbeck stochastic mean-reverting process, discrete ticks (500ms / 50 ticks/sec), MySQL advisory lock. |
| **SQL Parser & Security**| `sqlglot` (MySQL Dialect) | Abstract Syntax Tree (AST) validation for the AI SQL Assistant; enforces mutation blocking and session tenant scoping. |
| **AI LLM Routing** | Multi-Provider Failover Router | Grok (xAI) primary &rarr; Google Gemini &rarr; OpenRouter &rarr; Deterministic Local SQL Fallback. |
| **Authentication** | Flask-Login + Werkzeug | Scrypt password hashing, session fixation defense (`session.clear()`), 5-attempt brute-force lockout (15 min). |
| **Testing Framework** | `pytest` + `pytest-cov` | 95 comprehensive unit, integration, race-condition, and security tests (100% pass rate). |

---

## 3. User Roles & Permission Matrix

The platform implements strict Multi-Tenant Role-Based Access Control (RBAC). A user's authenticated identity is resolved entirely from the secure server-side session (`current_user.id`), never from client-supplied request payloads.

```
                  ┌──────────────────────┐
                  │   StockTrade Users   │
                  └──────────┬───────────┘
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│      ADMIN      │ │     BROKER      │ │    INVESTOR     │
│ System Overseer │ │ Client Manager  │ │  Paper Trader   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 3.1 System Administrator (`ADMIN`)
* **Scope**: Global system-wide administration.
* **Capabilities**:
  - View global platform health, active users, listed companies, aggregate capital, and trading volumes.
  - Company Management: Create new listed equities, modify company details, and activate/deactivate trading symbols.
  - User Management: View all accounts, inspect failed login counts, reset brute-force account lockouts, toggle user active status.
  - Market Simulator Controls: Pause, resume, trigger manual ticks, adjust tick intervals.
  - Commission Rule Engine: Configure platform brokerage rates and broker commission split percentages.
  - Security Audit Trail: Search and filter system-wide audit logs with IP addresses and user agents.
  - AI Assistant: Execute authorized read-only natural language and manual SQL queries across system-level views (`v_admin_trade_facts`, `Audit_Logs`, `Users`).

### 3.2 Institutional Broker (`BROKER`)
* **Scope**: Multi-tenant client desk managing only assigned investors.
* **Capabilities**:
  - Client Onboarding: Register new investor clients with instant automated credential generation and opening cash grants.
  - Client Portfolio Oversight: Inspect assigned clients' real-time holdings, cash balances, open orders, and transaction histories.
  - Commission Analytics: Track platform-funded commission earnings (40% of brokerage collected from assigned client trades).
  - Termination: Terminate broker-client advisory relationships cleanly without deleting historical records.
  - AI Assistant: Query assigned client performance, trade frequency, and commission attribution.
* **Enforced Tenant Isolation (404 Policy)**: If a broker attempts to query or access an investor not assigned to them, the system responds with `404 Not Found` (never 403 Forbidden) to eliminate user enumeration vulnerabilities.

### 3.3 Retail & Direct Investor (`INVESTOR`)
* **Scope**: Single-tenant isolated paper-trading account.
* **Capabilities**:
  - Portfolio Dashboard: Real-time net portfolio valuation, available virtual cash, invested cost basis, unrealized P&L, realized P&L.
  - Market Directory: Browse 100 listed Indian equities across 14 industry sectors with live quotes, 24h change, high/low, and volume.
  - Order Execution: Execute instant market `BUY` and `SELL` orders using ACID stored procedures with authoritative price validation.
  - Virtual Cash Deposits: Add virtual funds up to ₹50,000.00 per day via a simulated deposit workflow.
  - Watchlist & Price Alerts: Save target tickers and configure price threshold alert triggers (`ABOVE` / `BELOW`).
  - Reporting & Ledger: Inspect complete append-only account ledger entries and download formula-sanitized transaction history CSVs.
  - AI Assistant: Ask natural language questions or write manual SQL queries restricted strictly to own portfolio, orders, and ledger.

---

## 4. Financial Rules, Constraints & Investor Restrictions

| Rule / Guardrail | Value / Enforcement | System Implementation |
|---|---|---|
| **Opening Virtual Cash Grant** | ₹1,00,000.00 | Automatically credited on account creation; logged in `Account_Ledger` as `OPENING_GRANT`. |
| **Maximum Daily Deposit** | ₹50,000.00 per 24 hours | Verified by `AccountRepository.get_daily_deposit_total()`; logged as `DEPOSIT`. |
| **Minimum Cash Balance** | ₹0.00 (No negative cash) | Enforced by MySQL constraint: `CHECK (virtual_balance >= 0)`. |
| **Minimum Order Quantity** | 1 Share (Integer $\ge 1$) | Enforced by MySQL constraint: `CHECK (quantity > 0)`. |
| **Investor Brokerage Fee** | 0.10% (min ₹1.00) | Calculated on trade value; charged on both BUY and SELL; logged as `FEE`. |
| **Broker Commission** | 40% of collected brokerage | Funded by platform expense; credited to assigned broker; never deducted from investor. |
| **Independent Investor Brokerage** | 0.10% to platform | If investor has no assigned broker, platform retains 100% of collected brokerage fee. |
| **Cost Basis Accounting** | Weighted Average Cost | Computed on every BUY; preserved on partial SELL; logged in `Holdings`. |
| **Short Selling & Borrowing** | Strictly Prohibited | Investors cannot sell shares they do not own: `Holdings.quantity >= sell_quantity`. |
| **Idempotency Protection** | Unique UUID v4 per trade | Prevents double-spending on duplicate clicks or network retries via `idempotency_key`. |

### 4.1 Financial Calculation Formats

#### 1. Investor Brokerage Calculation
$$\text{brokerage} = \max(\text{min\_fee}, \text{trade\_value} \times \text{brokerage\_rate})$$
* Example: Buying 10 shares of TCS at ₹4,000.00 = Trade Value ₹40,000.00. Brokerage = $\max(1.00, 40000 \times 0.0010) = ₹40.00$. Total cash deducted from investor = ₹40,040.00.

#### 2. Weighted Average Cost Basis (On BUY)
$$\text{new\_avg\_cost} = \frac{(\text{existing\_qty} \times \text{existing\_avg}) + (\text{buy\_qty} \times \text{execution\_price})}{\text{existing\_qty} + \text{buy\_qty}}$$

#### 3. Realized Profit and Loss (On SELL)
$$\text{realized\_pnl} = (\text{sell\_price} - \text{average\_cost}) \times \text{sell\_qty} - \text{sell\_brokerage}$$

#### 4. Unrealized Profit and Loss (Open Positions)
$$\text{unrealized\_pnl} = \sum_{i=1}^{N} \left[ \text{quantity}_i \times (\text{current\_price}_i - \text{average\_buy\_price}_i) \right]$$

---

## 5. Complete Database Schema (21 Tables & Views)

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│      Users      │──────<│ Broker_Clients  │>──────│      Users      │
│  (Role: BROKER) │       │                 │       │ (Role: INVESTOR)│
└────────┬────────┘       └─────────────────┘       └────────┬────────┘
         │                                                   │
         │ 1:1                                               │ 1:1
         ▼                                                   ▼
┌─────────────────┐                                 ┌─────────────────┐
│   Commissions   │                                 │    Accounts     │
└─────────────────┘                                 └────────┬────────┘
                                                             │
                                                             │ 1:N
                                                             ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     Stocks      │──────<│     Orders      │──────<│ Account_Ledger  │
└────────┬────────┘       └────────┬────────┘       │  (Append-Only)  │
         │                         │                └─────────────────┘
         │ 1:N                     │ 1:1
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  Stock_Prices   │       │  Transactions   │──────<│   Commissions   │
│  (Time-Series)  │       └─────────────────┘       └─────────────────┘
└─────────────────┘
```

### Table 1: `Users`
Stores user authentication credentials, assigned roles, and security lockout states.
```sql
CREATE TABLE Users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NULL,
    role ENUM('ADMIN', 'BROKER', 'INVESTOR') NOT NULL,
    status ENUM('ACTIVE', 'INACTIVE', 'SUSPENDED') DEFAULT 'ACTIVE',
    failed_login_attempts INT DEFAULT 0,
    locked_until DATETIME NULL,
    is_demo BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_role (role),
    INDEX idx_users_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Table 2: `Accounts`
Stores virtual cash balances for investors.
```sql
CREATE TABLE Accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    account_number VARCHAR(20) NOT NULL UNIQUE,
    virtual_balance DECIMAL(15,2) NOT NULL DEFAULT 100000.00,
    currency VARCHAR(3) DEFAULT 'INR',
    status ENUM('ACTIVE', 'FROZEN', 'CLOSED') DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_accounts_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE RESTRICT,
    CONSTRAINT chk_virtual_balance_non_negative CHECK (virtual_balance >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Table 3: `Account_Ledger`
Append-only immutable financial audit ledger. Triggers prevent all updates and deletes.
```sql
CREATE TABLE Account_Ledger (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    entry_type ENUM('OPENING_GRANT', 'DEPOSIT', 'BUY', 'SELL', 'FEE', 'ADJUSTMENT') NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    signed_amount DECIMAL(15,2) NOT NULL,
    balance_after DECIMAL(15,2) NOT NULL,
    reference_type VARCHAR(50) NOT NULL,
    reference_id VARCHAR(100) NOT NULL,
    description VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ledger_account FOREIGN KEY (account_id) REFERENCES Accounts(id) ON DELETE RESTRICT,
    INDEX idx_ledger_account_created (account_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Table 4: `Stocks`
Contains master metadata for the 100 listed equities across 14 industry sectors.
```sql
CREATE TABLE Stocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    company_name VARCHAR(150) NOT NULL,
    sector VARCHAR(50) NOT NULL,
    exchange VARCHAR(10) DEFAULT 'NSE',
    base_price DECIMAL(12,4) NOT NULL,
    status ENUM('ACTIVE', 'SUSPENDED', 'DELISTED') DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_stocks_sector (sector),
    INDEX idx_stocks_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Table 5: `Current_Prices`
High-speed, denormalized 1-row-per-stock cache for $O(1)$ read locks during order execution.
```sql
CREATE TABLE Current_Prices (
    stock_id INT PRIMARY KEY,
    price DECIMAL(12,4) NOT NULL,
    previous_close DECIMAL(12,4) NOT NULL,
    day_open DECIMAL(12,4) NOT NULL,
    day_high DECIMAL(12,4) NOT NULL,
    day_low DECIMAL(12,4) NOT NULL,
    volume DECIMAL(18,5) DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_current_prices_stock FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Table 6: `Stock_Prices`
Append-only time-series historical price observations generated by the simulator.
```sql
CREATE TABLE Stock_Prices (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_id INT NOT NULL,
    price DECIMAL(12,4) NOT NULL,
    volume DECIMAL(18,5) DEFAULT 0,
    source ENUM('SIMULATOR', 'SEED', 'MANUAL') DEFAULT 'SIMULATOR',
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_stock_prices_stock FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE CASCADE,
    INDEX idx_stock_prices_series (stock_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Table 7: `Orders`
Records investor order tickets and terminal execution states.
```sql
CREATE TABLE Orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    stock_id INT NOT NULL,
    side ENUM('BUY', 'SELL') NOT NULL,
    order_type ENUM('MARKET', 'LIMIT') DEFAULT 'MARKET',
    quantity INT NOT NULL,
    quoted_price DECIMAL(12,4) NOT NULL,
    execution_price DECIMAL(12,4) NULL,
    status ENUM('PENDING', 'EXECUTED', 'REJECTED', 'CANCELLED', 'FAILED') DEFAULT 'PENDING',
    rejection_reason VARCHAR(255) NULL,
    idempotency_key VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_orders_stock FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE RESTRICT,
    CONSTRAINT chk_orders_quantity_positive CHECK (quantity > 0),
    INDEX idx_orders_user_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Table 8: `Holdings`
Maintains current aggregate open positions and weighted average cost basis per stock.
```sql
CREATE TABLE Holdings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    stock_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    average_buy_price DECIMAL(12,4) NOT NULL DEFAULT 0.0000,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_stock (user_id, stock_id),
    CONSTRAINT fk_holdings_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_holdings_stock FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE RESTRICT,
    CONSTRAINT chk_holdings_qty_non_negative CHECK (quantity >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Table 9: `Transactions`
Audited execution details linked to completed orders.
```sql
CREATE TABLE Transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL UNIQUE,
    user_id INT NOT NULL,
    stock_id INT NOT NULL,
    side ENUM('BUY', 'SELL') NOT NULL,
    quantity INT NOT NULL,
    execution_price DECIMAL(12,4) NOT NULL,
    gross_amount DECIMAL(15,2) NOT NULL,
    brokerage_fee DECIMAL(15,2) NOT NULL,
    net_amount DECIMAL(15,2) NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tx_order FOREIGN KEY (order_id) REFERENCES Orders(id) ON DELETE RESTRICT,
    CONSTRAINT fk_tx_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_tx_stock FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE RESTRICT,
    INDEX idx_tx_user_executed (user_id, executed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Table 10: `Broker_Clients`
Manages multi-tenant broker-to-client assignments.
```sql
CREATE TABLE Broker_Clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    broker_id INT NOT NULL,
    investor_id INT NOT NULL,
    status ENUM('ACTIVE', 'TERMINATED') DEFAULT 'ACTIVE',
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    terminated_at DATETIME NULL,
    UNIQUE KEY uq_broker_investor_active (investor_id, status),
    CONSTRAINT fk_bc_broker FOREIGN KEY (broker_id) REFERENCES Users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_bc_investor FOREIGN KEY (investor_id) REFERENCES Users(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Table 11: `Commission_Rules`
Platform rule matrix defining rates, minimum fees, and effective date ranges.
```sql
CREATE TABLE Commission_Rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rule_type ENUM('INVESTOR_BROKERAGE', 'BROKER_COMMISSION') NOT NULL,
    rate DECIMAL(6,4) NOT NULL,
    min_fee DECIMAL(10,2) DEFAULT 0.00,
    effective_from DATETIME NOT NULL,
    effective_to DATETIME NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Table 12: `Commissions`
Accrued commission earnings awarded to brokers from platform trading fees.
```sql
CREATE TABLE Commissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT NOT NULL UNIQUE,
    broker_id INT NOT NULL,
    investor_id INT NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    status ENUM('EARNED', 'PAID', 'CANCELLED') DEFAULT 'EARNED',
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_comm_tx FOREIGN KEY (transaction_id) REFERENCES Transactions(id) ON DELETE RESTRICT,
    CONSTRAINT fk_comm_broker FOREIGN KEY (broker_id) REFERENCES Users(id) ON DELETE RESTRICT,
    INDEX idx_comm_broker_earned (broker_id, earned_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Supporting Tables (13–19)
13. **`Price_Alerts`**: Target price alerts configured by users (`stock_id`, `target_price`, `direction ENUM('ABOVE', 'BELOW')`, `status ENUM('ACTIVE', 'TRIGGERED', 'CANCELLED')`).
14. **`Watchlist`**: User-saved stock tickers (`user_id`, `stock_id`, `created_at`).
15. **`Audit_Logs`**: Comprehensive system audit log (`user_id`, `action`, `entity_type`, `payload`, `ip_address`, `created_at`).
16. **`AI_Query_History`**: Audit trail of AI and Manual SQL queries (`user_id`, `prompt`, `generated_sql`, `ast_validated`, `execution_time_ms`, `error_message`).
17. **`Saved_Reports`**: Custom saved analytics queries.
18. **`System_Settings`**: Key-value platform settings (`setting_key`, `setting_value`).
19. **`System_Events`**: Simulator health checkpoints and error events.

### Core Database Views (Reporting & Safe AI Layer)
* **`v_market_latest`**: Unifies stock metadata with `Current_Prices`, calculating `day_change` and `day_change_pct` on-the-fly.
* **`v_investor_portfolio`**: Scoped view combining `Holdings`, `Current_Prices`, and cost basis, calculating current valuation and unrealized P&L per position.
* **`v_investor_transactions`**: Formatted view of historical trades with net fees.
* **`v_broker_client_summary`**: Aggregates client counts, total client portfolio balances, and trading volume per broker.
* **`v_admin_trade_facts`**: Platform-wide metrics: total volume, gross fee accruals, active traders, and order completion counts.

---

## 6. Stored Procedures & Database Triggers

### 6.1 Stored Procedure: `sp_execute_trade`
Executes market orders inside MySQL in a single atomic transaction under **fixed row-locking order** to guarantee deadlock immunity:

```
[Inbound Order Request]
          │
          ▼
1. Idempotency Check (If idempotency_key exists, return existing order)
          │
          ▼
2. SELECT ... FOR UPDATE on Accounts (Lock cash balance row)
          │
          ▼
3. SELECT ... FOR UPDATE on Holdings (Lock stock position row)
          │
          ▼
4. SELECT ... FOR SHARE on Current_Prices (Read authoritative market price)
          │
          ▼
5. Validation Logic:
   ├── On BUY:  Does Accounts.virtual_balance >= (gross_amount + brokerage)?
   └── On SELL: Does Holdings.quantity >= sell_quantity?
          │
   ┌──────┴──────┐
   ▼             ▼
[FAIL]         [PASS]
Set REJECTED    Update Accounts.virtual_balance
Commit & Exit   Update/Insert Holdings (Weighted Avg Cost)
                Insert Orders (status = 'EXECUTED')
                Insert Transactions
                Insert Account_Ledger (BUY/SELL entry)
                Insert Account_Ledger (FEE entry)
                Insert Commissions (If investor has active broker)
                COMMIT Transaction
```

### 6.2 Database Triggers
```sql
-- Enforce Ledger Immutability (Block UPDATE)
DELIMITER //
CREATE TRIGGER trg_ledger_block_update
BEFORE UPDATE ON Account_Ledger
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Account_Ledger is strictly append-only. UPDATE operations are prohibited.';
END //

-- Enforce Ledger Immutability (Block DELETE)
CREATE TRIGGER trg_ledger_block_delete
BEFORE DELETE ON Account_Ledger
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Account_Ledger is strictly append-only. DELETE operations are prohibited.';
END //

-- Validate Broker & Client Roles on Assignment
CREATE TRIGGER trg_broker_client_role_check
BEFORE INSERT ON Broker_Clients
FOR EACH ROW
BEGIN
    DECLARE v_broker_role VARCHAR(20);
    DECLARE v_investor_role VARCHAR(20);

    SELECT role INTO v_broker_role FROM Users WHERE id = NEW.broker_id;
    SELECT role INTO v_investor_role FROM Users WHERE id = NEW.investor_id;

    IF v_broker_role != 'BROKER' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Assigned broker must possess role BROKER.';
    END IF;
    IF v_investor_role != 'INVESTOR' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Assigned client must possess role INVESTOR.';
    END IF;
END //
DELIMITER ;
```

---

## 7. Market Simulation Engine

The market simulator runs as an autonomous Python background worker that generates realistic financial price movements without third-party API dependencies.

### 7.1 Mathematical Model: Ornstein-Uhlenbeck (OU) Mean Reversion
To prevent prices from diffusing to infinity or dropping to zero, prices evolve via a discrete **mean-reverting stochastic process**:
$$S_{t+1} = S_t + \theta (\mu - S_t) \Delta t + \sigma S_t \epsilon \sqrt{\Delta t}$$
* $S_t$: Current market price.
* $\mu$: Base anchor price from IPO seed reference.
* $\theta = 0.05$: Mean reversion pull speed toward reference value.
* $\sigma = 0.015$: Bounded Gaussian volatility.
* $\epsilon \sim \mathcal{N}(0, 1)$: Independent standard normal random shock per stock.
* **Non-Zero Guarantee**: The simulator enforces an absolute floor $S_{t+1} \ge \max(1.00, S_t \times 0.20)$ to prevent negative or zero stock quotes.

### 7.2 Concurrency & Advisory Locking
To prevent duplicate tick execution across multiple worker processes, the simulator acquires a MySQL advisory lock before each tick loop:
```sql
SELECT GET_LOCK('stocktrade_simulator', 0);
```
Only the primary process holds the lock; secondary workers skip tick cycles cleanly without database conflict.

### 7.3 Dynamic On-The-Fly OHLC Aggregation
Rather than storing pre-aggregated candle tables, the database aggregates candlestick bars dynamically from the immutable `Stock_Prices` time series:
```sql
SELECT 
    FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(recorded_at) / :interval_sec) * :interval_sec) AS bucket_start,
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

## 8. AI SQL Assistant Architecture (5-Layer Defense)

StockTrade features an institutional AI SQL Assistant operating in two modes: **AI Natural Language Assistant** and **Manual SQL Query Editor**. Both modes share a strict 5-layer execution pipeline.

```
[User Question or Manual SQL Query]
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ Layer 1: Schema-Aware RAG Grounding                    │
│ Exposes only authorized role views in context prompt. │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Layer 2: LLM Failover Router                           │
│ Grok (xAI) ──► Gemini ──► OpenRouter ──► Deterministic │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Layer 3: sqlglot AST Security Validator                │
│ • Enforces SELECT statements only                      │
│ • Blocks DDL/DML (INSERT, UPDATE, DELETE, DROP, ALTER) │
│ • Rejects stacked queries and dangerous functions      │
│ • Enforces role table allowlists                       │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Layer 4: AST Session Tenancy Scoping                   │
│ Injects `user_id = @current_user_id` into WHERE clause │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Layer 5: Read-Only Database Execution                  │
│ Executed via dedicated restricted MySQL user           │
│ (stocktrade_ai_ro) with 2-second timeout & 100 row cap │
└────────────────────────────────────────────────────────┘
```

### Role Table Allowlist for SQL Assistant
* **INVESTOR**: Allowed views: `v_investor_portfolio`, `v_investor_transactions`, `v_market_latest`, `Watchlist`, `Stocks`. Prohibited: `Users`, `Accounts`, `Broker_Clients`, `Commissions`, `Audit_Logs`.
* **BROKER**: Allowed views: `v_broker_client_summary`, `v_investor_transactions`, `v_market_latest`, `Broker_Clients`, `Commissions`. Strictly scoped to assigned `broker_id`.
* **ADMIN**: Full read-only access to all safe views and audit tables.

---

## 9. Security Hardening & Enterprise Controls

1. **Brute-Force Lockout Defense**: 5 consecutive failed login attempts locks the user account for 15 minutes (`Users.locked_until`).
2. **Password Cryptography**: Passwords hashed with `scrypt` via Werkzeug security primitives.
3. **Session Fixation Prevention**: `session.clear()` invoked immediately upon successful authentication to rotate session cookies.
4. **404 Tenant Isolation Policy**: Accessing an unassigned investor profile returns HTTP 404 (Not Found), completely preventing user enumeration attacks.
5. **CSV Formula Injection (DDE) Sanitization**: All cells in CSV exports beginning with `=`, `+`, `-`, `@`, `\t`, `\r` are prepended with an apostrophe (`'`) to disable spreadsheet script execution.
6. **Cross-Site Request Forgery (CSRF)**: All mutating state endpoints require a valid `X-CSRFToken` header.
7. **Security Headers**: Responses include `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, and `Content-Security-Policy`.

---

## 10. Complete REST API Endpoint Directory

### Authentication Endpoints (`/api/v1/auth`)
* `POST /api/v1/auth/login`: Authenticates user; returns session cookie.
* `POST /api/v1/auth/logout`: Invalidates session cookie.
* `GET  /api/v1/auth/session`: Returns authentication status, CSRF token, and user profile.
* `GET  /api/v1/auth/me`: Returns active session identity.

### Market Endpoints (`/market/api/v1/market`)
* `GET /market/api/v1/market/prices`: Returns real-time quotes for all 100 stocks. Supports `?since=` timestamp delta polling.
* `GET /market/api/v1/market/history`: Returns dynamic OHLC candlestick data (`symbol`, `interval` = `1m`, `5m`, `1h`).
* `GET /market/api/v1/market/status`: Returns simulator health metrics, tick count, and status indicator (`green`, `amber`, `red`).

### Investor Endpoints (`/investor/api/v1/investor`)
* `GET  /investor/api/v1/investor/summary`: Returns available cash, holdings valuation, portfolio total, unrealized P&L, realized P&L.
* `GET  /investor/api/v1/investor/holdings`: Returns active stock positions with weighted average cost basis.
* `GET  /investor/api/v1/investor/transactions`: Returns historical trade log.
* `POST /investor/api/v1/investor/orders`: Places a market `BUY` or `SELL` order ticket.
* `POST /investor/api/v1/investor/deposit`: Deposits virtual funds (up to ₹50,000.00/day).
* `GET  /investor/api/v1/investor/watchlist`: Retrieves saved ticker watchlist.
* `POST /investor/api/v1/investor/watchlist`: Adds a stock to watchlist.
* `DELETE /investor/api/v1/investor/watchlist/<stock_id>`: Removes stock from watchlist.
* `GET  /investor/api/v1/investor/alerts`: Returns user price threshold alerts.
* `POST /investor/api/v1/investor/alerts`: Creates a target price alert.
* `GET  /api/v1/reports/transactions-csv`: Downloads formula-sanitized transaction history CSV.

### Broker Endpoints (`/broker/api/v1/broker`)
* `GET  /broker/api/v1/broker/clients`: Lists active assigned clients.
* `POST /broker/api/v1/broker/clients`: Onboards new client with initial ₹1,00,000 grant.
* `GET  /broker/api/v1/broker/client-profile?investor_id=X`: Returns client portfolio (404 enforced if unassigned).
* `POST /broker/api/v1/broker/clients/<id>/end`: Terminates client relationship.
* `GET  /broker/api/v1/broker/analytics`: Returns aggregate commission earnings and trading volume.

### Administrator Endpoints (`/admin/api/v1/admin`)
* `GET    /admin/api/v1/admin/overview`: System-wide counts (capital, users, orders, volume).
* `GET    /admin/api/v1/admin/companies`: Searchable list of all listed equities.
* `POST   /admin/api/v1/admin/companies`: Lists a new company stock.
* `PUT    /admin/api/v1/admin/companies/<id>`: Updates company metadata.
* `DELETE /admin/api/v1/admin/companies/<id>`: Guarded hard-delete (fails if orders/holdings exist).
* `GET    /admin/api/v1/admin/users`: Lists all users, failed login counters, and lockouts.
* `PATCH  /admin/api/v1/admin/users/<id>/status`: Activates or deactivates an account.
* `POST   /admin/api/v1/admin/users/<id>/reset-lockout`: Clears failed login counter and lockout state.
* `GET    /admin/api/v1/admin/simulator/status`: Inspects simulation worker metrics.
* `POST   /admin/api/v1/admin/simulator/control`: `{ action: "pause" | "resume" | "tick" }`.
* `GET    /admin/api/v1/admin/audit-logs`: Searchable audit log trail.

### AI Assistant Endpoints (`/ai/api/v1/ai`)
* `POST /ai/api/v1/ai/query`: Generates, validates, and executes an AI natural language query.
* `POST /ai/api/v1/ai/manual-query`: Validates and executes user-written Manual SQL queries.
* `GET  /ai/api/v1/ai/schema`: Returns authorized views and schema documentation for current role.
* `GET  /ai/api/v1/ai/providers`: LLM provider health and routing status.

---

## 11. Evaluation Accounts & Seed Credentials

| Role | Username | Seed Password | Role Description & Permitted Scope |
|---|---|---|---|
| **System Admin** | `admin` | `Admin@StockTrade2026` | Exchange Administrator: Full oversight, company CRUD, lockout resets, audit logs. |
| **Broker 1** | `broker_arun` | `Broker@StockTrade2026` | Apex Securities: Manages client investors Rahul, Sneha, and Vikram. |
| **Broker 2** | `broker_priya` | `Broker@StockTrade2026` | BlueChip Capital: Manages client investors Ananya and Karan. |
| **Investor 1** | `investor_rahul` | `Investor@StockTrade2026` | Active Investor (Managed by Arun Mehta): Active paper portfolio. |
| **Investor 2** | `investor_sneha` | `Investor@StockTrade2026` | Wealth Management Client (Managed by Arun Mehta): Long-term equities. |
| **Investor 3** | `investor_rohit` | `Investor@StockTrade2026` | Direct Market Participant: Independent self-directed investor (no broker). |

*(All evaluation accounts also accept the universal evaluation demo password: `DemoPassword123!`)*

---

## 12. How to Run, Test, and Verify the Project

### 1. Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: v18.0 or higher
- **MySQL**: 8.0 or higher running on `localhost:3306`

### 2. Database Initialization
Run the idempotent initialization script to provision the schema, check constraints, triggers, stored procedures, 100 Indian equities, and demo accounts:
```powershell
.\.venv\Scripts\python init_db.py
```

### 3. Start Backend & Market Simulator
```powershell
.\.venv\Scripts\python app.py
```
*Backend URL*: `http://127.0.0.1:5000`

### 4. Start Frontend SPA
```powershell
npm --prefix frontend run dev
```
*Frontend URL*: `http://localhost:3000`

### 5. Execute Test Suite
Run the 95-test automated test suite:
```powershell
.\.venv\Scripts\pytest -v
```
All 95 tests pass with 100% success rate, validating ACID trade execution, trigger ledger immutability, AST SQL injection defense, concurrency race condition resistance, and multi-tenant RBAC isolation.
