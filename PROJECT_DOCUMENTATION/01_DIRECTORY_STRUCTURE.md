# StockTrade v2 — Directory Structure & File Inventory

This document provides a comprehensive, file-by-file inventory of the entire StockTrade v2 repository. Every file has been inspected directly in source code.

---

## 1. Project Directory Tree

```
DBMSPRJ/
├── .env                              # Local environment variables (git-ignored)
├── .env.aiven                        # Aiven cloud database connection credentials (git-ignored)
├── .env.example                      # Production template of all required environment variables
├── .gitignore                        # Git exclusion rules for secrets, builds, and virtualenvs
├── aiven-ca.pem                      # Aiven Cloud MySQL custom Project CA certificate (git-ignored)
├── app.py                            # Flask application factory, middleware, and error handlers
├── backup_db.ps1                     # PowerShell wrapper for automated MySQL logical backups
├── config.py                         # Typed environment configuration classes (Config, Prod, Dev, Test)
├── DEPLOYMENT_GUIDE.md               # Step-by-step production cloud deployment documentation
├── init_aiven.py                     # Initializer script for provisioning Aiven Cloud MySQL
├── init_db.ps1                       # PowerShell wrapper for initializing local MySQL database
├── Procfile                          # Cloud process execution command for Gunicorn WSGI server
├── PRODUCT_SPEC_MASTER.md            # Comprehensive project product specifications and DBMS criteria
├── project.emd                       # Master DBMS design specifications, features, and schemas
├── PROJECT.md                        # Duplicate master DBMS design document
├── query_db.ps1                      # PowerShell utility for running ad-hoc SQL against stocktrade
├── README.md                         # Quick-start documentation, features, and setup instructions
├── render.yaml                       # Infrastructure-as-Code Blueprint for Render cloud deployment
├── requirements.txt                  # Python dependencies manifest with environment markers
├── run_tests.ps1                     # PowerShell wrapper for running pytest with coverage
├── start.ps1                         # One-click startup script for backend, simulator, and frontend build
├── wsgi.py                           # Production WSGI entry point invoked by Gunicorn
│
├── database/                         # Database DDL schemas, stored procedures, triggers, seed scripts
│   ├── backfill_prices.py            # Historical price generation and stochastic math utilities
│   ├── backup_manager.py             # Hot backup manager, retention policy, and restore verification
│   ├── indexes.sql                   # Performance B-Tree indexes for foreign keys, symbols, dates
│   ├── init_db.py                    # Multi-statement SQL migration runner and database initializer
│   ├── migrations_v2.py              # Schema migration script for financial check constraints & Order_Events
│   ├── procedures.sql                # Authoritative sp_execute_trade & sp_reconcile_financial_integrity
│   ├── schema.sql                    # Core DDL for 14 tables with primary keys, FKs, and check constraints
│   ├── seed_companies.sql            # Seed data for 104 listed equities across 10 sectors
│   ├── seed_demo_users.sql           # Seed data for Admin, Brokers, and Investors with hashed passwords
│   ├── seed_settings_rules.sql       # Seed data for system parameters and commission rate rules
│   ├── triggers.sql                  # 16 database triggers enforcing ledger immutability and role rules
│   ├── views.sql                     # 9 role-scoped projection views for Investor, Broker, Admin, AI
│   └── backups/                      # Directory storing automated timestamped .sql database backups
│
├── docs/                             # Academic DBMS documentation and architecture notes
│   ├── API.md                        # REST API contracts and request/response specifications
│   ├── DBMS_CONCEPTS.md              # In-depth discussion of normalization, ACID, indexing, procedures
│   ├── DECISIONS.md                  # Architectural Decision Records (ADRs) explaining technical choices
│   ├── ERD.md                        # Entity-Relationship diagram definitions and relational schemas
│   ├── NORMALIZATION.md              # 1NF, 2NF, 3NF, and BCNF normalization proofs
│   ├── SECURITY.md                   # Threat modeling, SQL injection defenses, and RBAC matrix
│   └── TEST_REPORT.md                # Verification summary of backend test coverage
│
├── frontend/                         # React 18 / Vite Single-Page Application (SPA)
│   ├── index.html                    # Single-page HTML entry point for React mounting
│   ├── package.json                  # Node dependencies and build scripts (build, dev, preview)
│   ├── package-lock.json             # Exact dependency tree lockfile for npm
│   ├── vite.config.js                # Vite build bundler configuration, outputting to static/dist
│   └── src/                          # React application source code
│       ├── main.jsx                  # React DOM root entry point mounting <App />
│       ├── App.jsx                   # Role-based dashboard shell, navigation routing, and modals
│       ├── api/
│       │   └── client.js             # Centralized fetch client handling CSRF, credentials, and API routes
│       ├── components/               # Reusable UI widgets and modal dialogs
│       │   ├── BullLogo.jsx          # SVG brand logo with glowing bull silhouette
│       │   ├── DepositModal.jsx      # Modal for virtual cash deposits with ledger crediting
│       │   ├── KpiTile.jsx           # Minimalist metric card displaying portfolio and market numbers
│       │   ├── Navbar.jsx            # Top navigation bar with simulated market badge, search, user menu
│       │   ├── OnboardClientModal.jsx# Broker modal for assigning/onboarding new investor clients
│       │   ├── Sidebar.jsx           # Collapsible side navigation bar displaying role-scoped tabs
│       │   ├── SimulatedBadge.jsx    # Pulsing status pill displaying live simulator tick health
│       │   ├── SqlResultViewer.jsx   # Data grid viewer for SQL query results with column sorting
│       │   ├── StockChartModal.jsx   # Interactive financial candlestick/line chart using Chart.js
│       │   └── TradeTicketModal.jsx  # Order placement modal with price confirmation and buy/sell
│       ├── context/
│       │   └── AuthContext.jsx       # Global authentication state, login, logout, session restoration
│       ├── pages/                    # Role-specific terminal views
│       │   ├── Login.jsx             # Asymmetrical dark/light split login terminal with live ticker
│       │   ├── admin/                # Administrator management views
│       │   │   ├── AuditLogsView.jsx # Security event viewer with IP and action filtering
│       │   │   ├── CompaniesView.jsx # Stock directory CRUD, status toggling, and circuit rules
│       │   │   ├── OverviewView.jsx  # System health, trading volume metrics, and user counters
│       │   │   ├── SimulatorView.jsx # Autonomous simulator frequency, volatility, and pause control
│       │   │   └── UsersView.jsx     # User management, account lockouts, and status toggling
│       │   ├── ai/                   # AI Text-to-SQL Assistant views
│       │   │   └── AssistantView.jsx # Natural language assistant, manual SQL editor, query history
│       │   ├── broker/               # Institutional broker views
│       │   │   ├── AnalyticsView.jsx # Commission earnings, volume charts, client trade history
│       │   │   └── ClientsView.jsx   # Client roster, assignment management, client portfolio view
│       │   ├── investor/             # Retail investor trading views
│       │   │   ├── DashboardView.jsx # Portfolio summary, buying power, recent trades, holdings
│       │   │   ├── MarketView.jsx    # Complete stock screener with sector filters and live prices
│       │   │   ├── PortfolioView.jsx # Detailed holdings table with cost basis and unrealized P&L
│       │   │   ├── TransactionsView.jsx # Historical buy/sell execution history and fees
│       │   │   └── WatchlistView.jsx # Monitored stocks and conditional price alert triggers
│       │   └── styles/
│       │       └── index.css         # Global CSS variables, reset, layout, and utility classes
│       └── utils/
│           └── formatters.js         # Currency (INR ₹), percentage (%), and quantity formatters
│
├── models/                           # Database connection pooling and table definitions
│   ├── db.py                         # SQLAlchemy Core engine initialization, connection pools, TLS
│   ├── schema.py                     # SQLAlchemy Table metadata reflection and Core representations
│   └── user.py                       # User entity class conforming to Flask-Login UserMixin
│
├── rag_knowledge/                    # Structured domain markdown files injected into AI prompts
│   ├── business_rules.md             # Financial trading constraints, brokerage formulas, tenancy rules
│   ├── schema_documentation.md       # Exact column definitions and descriptions of allowed views
│   └── sql_examples.md               # Few-shot canonical SQL queries for Investor, Broker, and Admin
│
├── repositories/                     # Data Access Layer (DAL) executing explicit parameterized queries
│   ├── account_repo.py               # Cash balance retrieval, deposit execution, ledger logging
│   ├── alert_repo.py                 # Price alert creation, cancellation, evaluation against quotes
│   ├── audit_repo.py                 # Security event logging and administrative audit log queries
│   ├── broker_repo.py                # Broker client assignments, commissions, and performance analytics
│   ├── holding_repo.py               # Investor stock holding balance queries and portfolio valuations
│   ├── ledger_repo.py                # Double-entry ledger audit trail insertions and verification
│   ├── order_repo.py                 # Order lifecycle insertion, status updates, order events
│   ├── stock_repo.py                 # Stock directory, current quotes, OHLC history aggregation
│   ├── transaction_repo.py           # Trade transaction records, P&L lookups, trade facts
│   ├── user_repo.py                  # User credential validation, lockout tracking, role queries
│   └── watchlist_repo.py             # Watchlist item insertion, deletion, and user scoping
│
├── routes/                           # Flask HTTP Blueprints and API endpoint handlers
│   ├── admin.py                      # /admin: Company CRUD, user management, audit logs, simulator control
│   ├── ai.py                         # /ai: Natural language generation, AST validation, SQL execution
│   ├── auth.py                       # /api/v1/auth: Login, logout, session restoration, CSRF tokens
│   ├── broker.py                     # /broker: Client management, client onboarding, commission analytics
│   ├── investor.py                   # /investor: Portfolio, orders, deposits, watchlists, price alerts
│   ├── market.py                     # /market: Live price polling deltas, OHLC history, SSE streams
│   └── reports.py                    # /reports: CSV statement and trade transaction export endpoints
│
├── services/                         # Business logic services and coordination layer
│   ├── auth_service.py               # Password verification (PBKDF2/scrypt), brute-force lockout logic
│   ├── intent_service.py             # Dynamic entity resolution, sector indexing, deterministic SQL fallback
│   ├── llm_router.py                 # External AI API integration (Grok, Gemini, OpenRouter, Mistral)
│   ├── market_simulator.py           # Autonomous pricing worker, stochastic walk, advisory locking
│   ├── portfolio_service.py          # Portfolio valuation, asset allocation, unrealized P&L calculations
│   ├── query_executor.py             # Scoped query execution under stocktrade_ai_ro, session tenancy
│   ├── rag_service.py                # Context assembly for LLM prompts, sector grounding
│   ├── reconciliation_service.py     # Automated audit reconciling cash, holdings, and ledger entries
│   ├── semantic_validator.py         # AST semantic consistency check matching user intent to SQL
│   ├── sql_validator.py              # sqlglot AST allowlist validation, mutation blocking
│   └── trading_service.py            # Order validation, execution via sp_execute_trade, fee calculations
│
├── static/                           # Static assets served by Flask
│   ├── css/
│   │   └── design-system.css         # CSS design system matching terminal color palette
│   └── dist/                         # Vite-compiled production React application bundle
│       ├── index.html                # Compiled HTML index
│       └── assets/
│           ├── index-D-jiE0oO.js     # Production minified React bundle (506 kB)
│           └── index-DqnV-yR6.css    # Production CSS styles (3.4 kB)
│
├── templates/                        # Jinja2 server-rendered fallback templates
│   ├── base.html                     # Master layout with responsive navbar, flash messages, footer
│   ├── admin/                        # Server-rendered admin pages (audit_logs, companies, overview, users)
│   ├── ai/                           # Server-rendered AI assistant page (assistant.html)
│   ├── auth/                         # Server-rendered login page (login.html)
│   ├── broker/                       # Server-rendered broker pages (analytics, clients, overview)
│   ├── errors/                       # Standard error templates (403.html, 404.html, 500.html)
│   ├── investor/                     # Server-rendered investor pages (account, broker, dashboard, etc.)
│   ├── macros/                       # Reusable Jinja component macros (components.html)
│   └── market/                       # Server-rendered market pages (detail.html, overview.html)
│
├── tests/                            # Pytest automated test suite (136 tests)
│   ├── conftest.py                   # Pytest fixtures for test database, app factory, authenticated clients
│   ├── test_ai_intent_correctness.py # 15 tests verifying sector dynamic resolution and scope
│   ├── test_ai_sql.py                # 37 tests verifying AST safety, mutation rejection, and tenancy
│   ├── test_auth.py                  # 7 tests verifying login, lockout, logout, and session lifecycle
│   ├── test_backup.py                # 3 tests verifying backup creation, discovery, and retention
│   ├── test_broker_clients.py        # 4 tests verifying broker onboarding and tenant isolation
│   ├── test_concurrency.py           # 3 tests verifying concurrent order execution and balance races
│   ├── test_database.py              # 16 tests verifying schema constraints, triggers, and procedures
│   ├── test_investor_features.py     # 6 tests verifying watchlists, price alerts, and statement exports
│   ├── test_market.py                # 14 tests verifying simulator tick speed, math, and SSE feeds
│   ├── test_permissions.py           # 8 tests verifying RBAC access boundaries across portals
│   ├── test_production_readiness_audit.py # 8 tests verifying templates, production config, and TLS
│   ├── test_reconciliation.py        # 4 tests verifying automated financial reconciliation checks
│   ├── test_reports.py               # 2 tests verifying CSV injection sanitization and export
│   └── test_trading.py               # 9 tests verifying atomic buy/sell orders, fees, and rollbacks
│
└── utils/                            # Shared formatting and utility functions
    └── formatters.py                 # Indian Rupee (INR) currency formatting and percentage math
```

---

## 2. File-by-File Technical Inventory

| File Path | Component Category | Primary Purpose | Key Symbols / Classes | Associated Routes / DB Objects | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `app.py` | Core Application | Flask application factory, CSRF, security headers, error handlers | `create_app()`, `login_manager`, `csrf`, `limiter` | Registers all 7 blueprints; `/health`, `/` | **Active / Critical** |
| `wsgi.py` | Deployment Entry | Production entry point for Gunicorn with simulator startup | `app`, `env`, `MarketSimulator` | WSGI `app:app` | **Active / Critical** |
| `config.py` | Configuration | Typed configurations for Development, Testing, Production | `Config`, `ProductionConfig`, `TestingConfig` | Reads `DB_*`, `SECRET_KEY`, `SIMULATOR_*` | **Active / Critical** |
| `models/db.py` | Database Layer | Connection pooling, SQLAlchemy engines, TLS Project CA handling | `init_db_engines()`, `get_db_connection()`, `get_ai_connection()` | Primary & AI connection pools | **Active / Critical** |
| `models/schema.py` | Database Layer | SQLAlchemy Core Table metadata mappings | `users_table`, `orders_table`, `holdings_table`, etc. | Maps 14 relational tables | **Active / Critical** |
| `models/user.py` | Authentication | Flask-Login User model wrapping repository dictionary | `User(UserMixin)` | `Users` table | **Active / Critical** |
| `services/market_simulator.py` | Market Engine | Autonomous pricing engine, stochastic random walk, advisory lock | `MarketSimulator`, `get_instance()`, `hydrate_from_db()` | `Current_Prices`, `v_market_latest` | **Active / Critical** |
| `services/trading_service.py` | Trading Engine | Order placement and stored procedure coordination | `TradingService.execute_order()`, `TradingService.deposit_funds()` | `sp_execute_trade`, `Orders` | **Active / Critical** |
| `services/auth_service.py` | Security / Auth | PBKDF2/scrypt password hashing and brute force tracking | `AuthService.authenticate()`, `role_required()` | `Users`, `Audit_Logs` | **Active / Critical** |
| `services/intent_service.py` | AI Subsystem | Grounded entity extraction, sector synonyms, deterministic SQL fallback | `IntentService.resolve_intent()`, `IntentService.generate_sql()` | `Stocks`, all 9 views | **Active / Critical** |
| `services/semantic_validator.py` | AI Subsystem | Semantic AST consistency guard matching intent to query | `SemanticValidator.validate_consistency()` | Validates generated SQL | **Active / Critical** |
| `services/sql_validator.py` | AI Subsystem | sqlglot AST allowlist validation and mutation blocking | `SQLValidator.validate_sql()` | Restricts queries to SELECT on views | **Active / Critical** |
| `services/query_executor.py` | AI Subsystem | Tenancy-scoped execution under `stocktrade_ai_ro` and audit | `QueryExecutor.execute_scoped_query()`, `log_query_history()` | `AI_Query_History`, all 9 views | **Active / Critical** |
| `services/llm_router.py` | AI Subsystem | Multi-provider LLM API client with exponential backoff | `LLMRouter.complete()` | Calls Grok, Gemini, OpenRouter | **Active / Critical** |
| `services/rag_service.py` | AI Subsystem | Assembles structured prompt context based on role and intent | `RAGService.get_context_for_role()` | Reads `rag_knowledge/*.md` | **Active / Critical** |
| `services/portfolio_service.py` | Business Logic | Investor portfolio valuation, asset allocation, unrealized returns | `PortfolioService.get_portfolio_summary()` | `Holdings`, `Current_Prices` | **Active / Critical** |
| `services/reconciliation_service.py` | Accounting | Automated reconciliation audit of cash, holdings, and ledger | `ReconciliationService.run_full_reconciliation()` | `sp_reconcile_financial_integrity` | **Active / Critical** |
| `repositories/stock_repo.py` | DAL | Stock queries, market directory, OHLC aggregation | `StockRepository.get_market_overview()`, `get_history()` | `Stocks`, `v_market_latest` | **Active / Critical** |
| `repositories/account_repo.py` | DAL | Cash balance queries and deposit transaction operations | `AccountRepository.get_by_user_id()`, `deposit()` | `Accounts`, `Account_Ledger` | **Active / Critical** |
| `repositories/holding_repo.py` | DAL | Holding balances, cost bases, quantity checks | `HoldingRepository.get_by_user_and_stock()` | `Holdings` | **Active / Critical** |
| `repositories/order_repo.py` | DAL | Order record lifecycle and status transitions | `OrderRepository.create()`, `update_status()` | `Orders`, `Order_Events` | **Active / Critical** |
| `repositories/transaction_repo.py` | DAL | Trade transaction queries and P&L history | `TransactionRepository.get_by_user()` | `Transactions` | **Active / Critical** |
| `repositories/broker_repo.py` | DAL | Broker client assignments, commissions, and analytics | `BrokerRepository.get_clients()`, `get_analytics()` | `Broker_Clients`, `Commissions` | **Active / Critical** |
| `repositories/user_repo.py` | DAL | User lookups, lockout resets, password updates | `UserRepository.get_by_identifier()`, `record_login_failure()` | `Users` | **Active / Critical** |
| `repositories/audit_repo.py` | DAL | Security audit log insertion and retrieval | `AuditRepository.log()`, `get_recent()` | `Audit_Logs` | **Active / Critical** |
| `repositories/watchlist_repo.py` | DAL | Watchlist CRUD operations per investor | `WatchlistRepository.get_watchlist()`, `add()` | `Watchlist` | **Active / Critical** |
| `repositories/alert_repo.py` | DAL | Conditional price alerts CRUD and evaluation | `AlertRepository.get_alerts()`, `create_alert()` | `Price_Alerts` | **Active / Critical** |
| `repositories/ledger_repo.py` | DAL | Double-entry financial ledger operations | `LedgerRepository.record()` | `Account_Ledger` | **Active / Critical** |
| `routes/auth.py` | HTTP Blueprint | Authentication endpoints: login, logout, session, CSRF | `auth_bp`, `api_login()`, `api_session()`, `api_logout()` | `/api/v1/auth/*` | **Active / Critical** |
| `routes/market.py` | HTTP Blueprint | Market directory, polling deltas, OHLC chart data, SSE | `market_bp`, `api_prices()`, `api_history()`, `api_status()` | `/market/*` | **Active / Critical** |
| `routes/investor.py` | HTTP Blueprint | Investor trading, portfolio, watchlists, alerts, broker info | `investor_bp`, `api_orders()`, `api_holdings()`, `api_deposit()` | `/investor/*` | **Active / Critical** |
| `routes/broker.py` | HTTP Blueprint | Broker client management, onboarding, commissions, analytics | `broker_bp`, `api_clients()`, `api_analytics()` | `/broker/*` | **Active / Critical** |
| `routes/admin.py` | HTTP Blueprint | Admin company CRUD, user lockouts, audit logs, simulator | `admin_bp`, `api_companies()`, `api_users()`, `api_audit_logs()` | `/admin/*` | **Active / Critical** |
| `routes/ai.py` | HTTP Blueprint | AI natural language query, SQL execution, schema, history | `ai_bp`, `api_query()`, `api_generate()`, `api_execute()` | `/ai/*` | **Active / Critical** |
| `routes/reports.py` | HTTP Blueprint | CSV export endpoints for transaction history and statements | `reports_bp`, `export_transactions()`, `export_statement()` | `/reports/*` | **Active / Critical** |
| `frontend/src/App.jsx` | React UI | Master terminal shell, role tab routing, modal controllers | `<App />`, `currentTab`, `renderContent()` | Mounts role pages | **Active / Critical** |
| `frontend/src/api/client.js` | React UI | Centralized HTTP client managing CSRF tokens and endpoints | `api`, `request()`, `setCsrfToken()` | Calls all backend endpoints | **Active / Critical** |
| `frontend/src/pages/Login.jsx` | React UI | Asymmetrical split-screen terminal login with live market ticker | `<Login />`, `handleLogin()`, `demoAccounts` | `/` | **Active / Critical** |
| `frontend/src/pages/ai/AssistantView.jsx` | React UI | Dual-mode AI assistant & manual SQL console with result viewer | `<AssistantView />`, `handleAiSubmit()`, `handleManualSqlSubmit()` | `/ai/assistant` | **Active / Critical** |
| `frontend/src/pages/investor/DashboardView.jsx` | React UI | Investor terminal with buying power, portfolio value, orders | `<DashboardView />` | Tab: `dashboard` | **Active / Critical** |
| `frontend/src/pages/investor/MarketView.jsx` | React UI | Stock screener with sector pills, search, quick trade modal | `<MarketView />` | Tab: `market` | **Active / Critical** |
| `frontend/src/pages/investor/PortfolioView.jsx` | React UI | Holdings inventory with unrealized P&L and cost basis | `<PortfolioView />` | Tab: `portfolio` | **Active / Critical** |
| `frontend/src/pages/investor/TransactionsView.jsx` | React UI | Executed trades, execution prices, brokerage fees, CSV export | `<TransactionsView />` | Tab: `transactions` | **Active / Critical** |
| `frontend/src/pages/investor/WatchlistView.jsx` | React UI | Monitored ticker list and price alert creation interface | `<WatchlistView />` | Tab: `watchlist` | **Active / Critical** |
| `frontend/src/pages/broker/ClientsView.jsx` | React UI | Client roster, account balances, onboarding modal trigger | `<ClientsView />` | Tab: `clients` | **Active / Critical** |
| `frontend/src/pages/broker/AnalyticsView.jsx` | React UI | Broker commission breakdown, trade volume, client statistics | `<AnalyticsView />` | Tab: `analytics` | **Active / Critical** |
| `frontend/src/pages/admin/OverviewView.jsx` | React UI | High-level system overview, trade fact KPIs, volume counters | `<OverviewView />` | Tab: `overview` | **Active / Critical** |
| `frontend/src/pages/admin/CompaniesView.jsx` | React UI | Equity directory CRUD, status toggling, sector management | `<CompaniesView />` | Tab: `companies` | **Active / Critical** |
| `frontend/src/pages/admin/UsersView.jsx` | React UI | User account status toggling and brute-force lockout resets | `<UsersView />` | Tab: `users` | **Active / Critical** |
| `frontend/src/pages/admin/AuditLogsView.jsx` | React UI | Security audit logs with filterable actions and IPs | `<AuditLogsView />` | Tab: `audit-logs` | **Active / Critical** |
| `frontend/src/pages/admin/SimulatorView.jsx` | React UI | Market simulator speed slider, volatility control, pause toggle | `<SimulatorView />` | Tab: `simulator` | **Active / Critical** |
| `database/schema.sql` | Database DDL | 14 relational tables with constraints and foreign keys | DDL: `Users`, `Accounts`, `Stocks`, `Holdings`, `Orders`... | Core schema | **Active / Critical** |
| `database/procedures.sql` | Database Logic | Atomic trade execution and financial reconciliation procedures | `sp_execute_trade`, `sp_reconcile_financial_integrity` | Core procedures | **Active / Critical** |
| `database/triggers.sql` | Database Logic | 16 triggers enforcing ledger immutability and role restrictions | `trg_ledger_block_update`, `trg_ledger_block_delete`, etc. | Core triggers | **Active / Critical** |
| `database/views.sql` | Database Logic | 9 security projection views for role tenancy and AI assistant | `v_market_latest`, `v_investor_portfolio`, etc. | Core views | **Active / Critical** |
| `database/indexes.sql` | Database Logic | B-Tree performance indexes on foreign keys, symbols, dates | DDL indexes on `Orders`, `Transactions`, `Holdings` | Performance indices | **Active / Critical** |
| `database/seed_companies.sql` | Seed Data | 104 equities across 10 sectors with realistic Indian market base prices | `INSERT INTO Stocks`, `INSERT INTO Current_Prices` | Seed data | **Active / Critical** |
| `database/seed_demo_users.sql` | Seed Data | 9 evaluation users with PBKDF2/scrypt hashed passwords | `INSERT INTO Users`, `INSERT INTO Accounts` | Seed data | **Active / Critical** |
| `database/seed_settings_rules.sql` | Seed Data | System configuration parameters and commission rate rules | `INSERT INTO System_Settings`, `Commission_Rules` | Seed data | **Active / Critical** |
