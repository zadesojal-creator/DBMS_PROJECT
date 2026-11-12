# StockTrade v2 — Project Technical Overview

**System Name**: StockTrade v2  
**Type**: Academic Database Management Systems (DBMS) Capstone Project & Virtual Financial Trading Simulator  
**Core Technologies**: Python 3.11+, Flask 3.0, SQLAlchemy 2.0 Core, PyMySQL 1.1, MySQL 8.0 / InnoDB, React 18, Vite 5, Gunicorn 21, sqlglot 20  
**Target Exchanges**: Simulated National Stock Exchange (NSE) & Bombay Stock Exchange (BSE)  
**Database Deployment**: Managed Aiven Cloud MySQL 8.0 / Native MySQL on Linux/Windows  
**Application Hosting**: Render Web Service (Single Worker Process, 8 Worker Threads)  
**Test Suite Status**: 136 / 136 Tests Passing (100%)  

---

## 1. Project Purpose & Academic Learning Objectives

StockTrade v2 is built specifically to demonstrate rigorous, enterprise-grade **Database Management Systems (DBMS)** concepts within a live financial simulator. While the application provides an attractive, human-crafted fintech user interface and an AI-powered text-to-SQL console, the software architecture prioritizes **database correctness, transaction semantics, and financial accounting integrity** above cosmetic additions.

### Core DBMS Concepts Demonstrated

1. **Relational Schema Normalization & Integrity**:
   - Normalized across Third Normal Form (3NF) and Boyce-Codd Normal Form (BCNF) with explicit entity separation for users, accounts, ledgers, stocks, orders, transactions, commissions, broker relationships, and security audit logs.
   - Primary keys (`BIGINT AUTO_INCREMENT`), foreign keys with explicit referential actions (`ON DELETE RESTRICT` / `CASCADE`), unique constraints, and domain check constraints (`CHECK (virtual_balance >= 0)`, `CHECK (quantity > 0)`).

2. **ACID Transactions & Row-Level Locking**:
   - Concurrency control and serialized financial state updates using MySQL InnoDB row-level locking (`SELECT ... FOR UPDATE`).
   - Atomic execution of trades via stored procedure `sp_execute_trade`, guaranteeing that balance verification, order status changes, holding adjustments, cash movements, commission deductions, and ledger insertions occur within an all-or-nothing database transaction boundary.

3. **Append-Only Financial Ledger & Trigger-Enforced Immutability**:
   - Double-entry accounting principles implemented in `Account_Ledger`.
   - Database-level triggers (`trg_ledger_block_update`, `trg_ledger_block_delete`, `trg_transactions_no_update`, `trg_commissions_no_update`) that raise SQLSTATE `'45000'` signals to forbid any update or deletion of executed financial transactions.

4. **Multi-Role Tenant Isolation & Security**:
   - Three distinct operational roles: **Admin**, **Broker**, and **Investor**.
   - Tenant isolation enforced via session variables (`@current_user_id`) and parameter bindings (`:auth_user_id`) at both the SQL query layer and database view projection layer.
   - Defense-in-depth read-only AI SQL assistant operating under a least-privilege database user (`stocktrade_ai_ro`) with abstract syntax tree (AST) safety validation via `sqlglot`.

5. **Autonomous Market Simulation Engine**:
   - High-frequency in-memory stochastic pricing engine (0.50s ticks, ~2.0 ticks/sec) mimicking geometric Brownian motion with sector-specific volatility and circuit breakers.
   - Decoupled batch persistence (1.0s DB flush interval) using MySQL advisory locks (`GET_LOCK('stocktrade_simulator')`) to prevent connection pool exhaustion across web worker threads.

---

## 2. Technology Stack & Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLIENT BROWSERS & DEVICES                          │
│         React 18 SPA (Vite Bundled)  /  Jinja2 Server-Rendered Views        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS / Port 443
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             RENDER WEB SERVICE                              │
│  Gunicorn 21 WSGI Server (1 Master Process, 8 Worker Threads, wsgi:app)     │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        FLASK 3 APPLICATION FACTORY                    │  │
│  │   • Flask-Login (Session Auth)       • Flask-WTF (CSRF Protection)    │  │
│  │   • Flask-Limiter (Rate Limiting)    • Custom Jinja INR/Formatters    │  │
│  │   • Security Headers Middleware      • Error Handlers (JSON + HTML)   │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│                                      │                                      │
│  ┌───────────────────────────────────┴───────────────────────────────────┐  │
│  │                             BLUEPRINTS                                │  │
│  │   /api/v1/auth   (routes/auth.py)       /market   (routes/market.py)  │  │
│  │   /investor      (routes/investor.py)   /broker   (routes/broker.py)  │  │
│  │   /admin         (routes/admin.py)      /ai       (routes/ai.py)      │  │
│  │   /reports       (routes/reports.py)                                  │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│                                      │                                      │
│  ┌───────────────────────────────────┴───────────────────────────────────┐  │
│  │                        SERVICES & BUSINESS LOGIC                      │  │
│  │   • MarketSimulator (services/market_simulator.py - Singleton Thread) │  │
│  │   • TradingService  (services/trading_service.py - sp_execute_trade)  │  │
│  │   • AuthService     (services/auth_service.py - Session & Lockouts)   │  │
│  │   • IntentService   (services/intent_service.py - Semantic Resolver)  │  │
│  │   • SemanticValidator (services/semantic_validator.py - AST Guard)    │  │
│  │   • SQLValidator    (services/sql_validator.py - sqlglot Safety)      │  │
│  │   • QueryExecutor   (services/query_executor.py - Tenancy & Logging)  │  │
│  │   • LLMRouter       (services/llm_router.py - Grok/Gemini/OpenRouter) │  │
│  │   • Reconciliation  (services/reconciliation_service.py)              │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│                                      │                                      │
│  ┌───────────────────────────────────┴───────────────────────────────────┐  │
│  │                    SQLALCHEMY 2.0 CORE CONNECTION POOLS               │  │
│  │   • Primary DML Pool (_engine): Pool size 10, max overflow 20        │  │
│  │   • AI Read-Only Pool (_ai_engine): Pool size 5, max overflow 10      │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │ Encrypted TLS (Project CA) / Port 3306/11232
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MANAGED AIVEN MYSQL 8.0 / INNODB                       │
│                                                                             │
│   • 14 Core Relational Tables (Users, Accounts, Ledger, Stocks, Orders...)  │
│   • 9 Role-Scoped Projection Views (v_market_latest, v_investor_portfolio..)│
│   • 2 Stored Procedures (sp_execute_trade, sp_reconcile_financial_integrity)│
│   • 16 Immutability, Audit & Role Enforcement Triggers                      │
│   • InnoDB B-Tree Indexes on Foreign Keys, Symbols, Timestamps & Actions    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack Reference Table

| Layer | Component | Version | Role in StockTrade v2 |
| :--- | :--- | :--- | :--- |
| **Runtime** | Python | 3.11+ | Core application execution environment |
| **Framework** | Flask | 3.0.x | HTTP routing, blueprint modularization, application factory |
| **WSGI Server** | Gunicorn | 21.2+ | Production HTTP server with thread-based worker model |
| **Database** | MySQL / InnoDB | 8.0+ | Relational storage, ACID transactions, procedures, triggers |
| **DB Driver** | PyMySQL | 1.1+ | Pure Python MySQL client with TLS certificate validation |
| **DB Layer** | SQLAlchemy Core | 2.0+ | Explicit parameterized SQL execution, connection pooling |
| **AST Parser** | sqlglot | 20.0+ | SQL query parsing, semantic validation, mutation blocking |
| **Authentication** | Flask-Login | 0.6.3 | Server-side user session management and session cookies |
| **Security** | Flask-WTF | 1.2.1 | CSRF token generation and validation for mutating routes |
| **Rate Limiter** | Flask-Limiter | 3.5.0 | In-memory token bucket rate limiting per IP address |
| **Frontend UI** | React | 18.3.1 | Single-Page Application (SPA) reactive user interface |
| **Build Tool** | Vite | 5.2.11 | Fast ES module bundling, React JSX compilation |
| **Charting** | Chart.js | 4.4.2 | Interactive OHLC financial candlestick and line charts |
| **Icons** | Lucide React | 0.378.0 | Minimalist iconography across terminal and dashboards |
| **Template Engine**| Jinja2 | 3.1.x | Server-rendered HTML views for zero-JS browser clients |

---

## 4. Current Operational Status

- **Backend Test Suite**: 136 tests passing across all 15 test modules.
- **Frontend Assets**: Clean Vite build residing in `static/dist/` (assets: `index-D-jiE0oO.js`, `index-DqnV-yR6.css`).
- **Database Engine**: Fully configured for both local development (`stocktrade`, `stocktrade_test`) and Aiven Cloud MySQL (`mysql-...aivencloud.com`) with TLS Project CA verification.
- **Autonomous Services**: Market simulator starts seamlessly on application launch and automatically flushes price ticks to MySQL `Current_Prices`.
- **AI Text-to-SQL**: Multi-stage intent parsing and semantic consistency engine active, preventing unrelated queries and guaranteeing role-tenancy isolation.
