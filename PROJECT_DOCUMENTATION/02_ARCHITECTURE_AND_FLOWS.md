# StockTrade v2 — Architecture & Application Execution Flows

This document details the software architecture, component boundaries, and end-to-end execution flows of StockTrade v2 based on direct source code analysis.

---

## 1. High-Level Architecture Overview

StockTrade v2 employs a hybrid architecture:
- **Client Layer**: A modern React 18 Single-Page Application (SPA) built with Vite, complemented by a complete set of Jinja2 server-rendered fallback templates.
- **Web / Application Layer**: Flask 3.0 configured via an Application Factory (`app.py`), running behind Gunicorn with 1 worker process and 8 threads.
- **Autonomous Worker**: An in-memory, thread-driven stochastic market simulation engine with decoupled database batch persistence.
- **Data Access & Business Layer**: Strict service-to-repository-to-database boundaries using explicit parameterized SQL via SQLAlchemy 2.0 Core.
- **Database Engine**: Native MySQL 8.0 / InnoDB enforcing ACID transaction boundaries, row-level locking (`SELECT ... FOR UPDATE`), append-only ledger immutability via triggers, and authoritative trade execution via stored procedures.

---

## 2. Mermaid Architecture & Execution Flow Diagrams

### Diagram 1: High-Level Application Architecture

```mermaid
flowchart TB
    subgraph ClientLayer["Client Layer (Browser)"]
        SPA["React 18 SPA (Vite Bundled)<br>Chart.js • Lucide • CSS Design System"]
        JinjaFallback["Jinja2 Fallback Views<br>(Zero-JS / Static Browser Mode)"]
    end

    subgraph Ingress["Web Server & Ingress"]
        Gunicorn["Gunicorn 21 WSGI Server<br>1 Master Process • 8 Worker Threads<br>(Bound to 0.0.0.0:$PORT)"]
    end

    subgraph AppFactory["Flask 3 Application (app.py)"]
        Middleware["Security Headers • CSRF Protection • Rate Limiter"]
        AuthContext["Flask-Login Session Manager (Cookie: session)"]
        Blueprints["7 Registered Blueprints:<br>auth • market • investor • broker • admin • ai • reports"]
    end

    subgraph ServiceLayer["Service & Business Logic Layer"]
        TradingSvc["TradingService<br>(sp_execute_trade coordinator)"]
        Simulator["MarketSimulator Singleton<br>(500ms Ticks • 1.0s DB Flush)"]
        AuthSvc["AuthService<br>(PBKDF2/scrypt • Lockouts)"]
        AISubsystem["AI SQL Subsystem<br>IntentService • SemanticValidator • SQLValidator • QueryExecutor"]
        Reconciliation["ReconciliationService<br>(sp_reconcile_financial_integrity)"]
    end

    subgraph DBConnectionLayer["Database Connection Layer (models/db.py)"]
        PrimaryPool["Primary DML Pool (_engine)<br>Pool: 10, Overflow: 20, Recycle: 1800s"]
        AIPool["AI Read-Only Pool (_ai_engine)<br>Pool: 5, Overflow: 10, Recycle: 1800s"]
    end

    subgraph MySQLStorage["Cloud Database (Aiven MySQL 8.0 / InnoDB)"]
        Tables["14 Normalized Tables<br>(Users, Accounts, Ledger, Stocks, Orders...)"]
        Views["9 Security Projection Views<br>(v_market_latest, v_investor_portfolio...)"]
        Procedures["Stored Procedures<br>(sp_execute_trade, sp_reconcile...)"]
        Triggers["16 Integrity Triggers<br>(trg_ledger_block_update/delete...)"]
    end

    SPA -->|REST API Calls & SSE Stream| Gunicorn
    JinjaFallback -->|Standard HTTP GET/POST| Gunicorn
    Gunicorn --> AppFactory
    AppFactory --> Middleware
    Middleware --> AuthContext
    AuthContext --> Blueprints
    Blueprints --> ServiceLayer
    ServiceLayer --> DBConnectionLayer
    DBConnectionLayer -->|TLS Encrypted Connection| MySQLStorage
```

---

### Diagram 2: Application Startup Sequence

```mermaid
sequenceDiagram
    autonumber
    participant WSGI as wsgi.py / Gunicorn
    participant Factory as app.py (create_app)
    participant Cfg as config.py (Config)
    participant DBPool as models/db.py (init_db_engines)
    participant Simulator as services/market_simulator.py
    participant MySQL as MySQL 8.0 (Aiven / Local)

    WSGI->>Factory: create_app(FLASK_ENV)
    Factory->>Cfg: Load configuration class (ProductionConfig / DevConfig)
    Cfg-->>Factory: app.config populated (Secret Key, DB credentials, TLS paths)
    
    Factory->>DBPool: init_db_engines(app.config)
    DBPool->>DBPool: Resolve TLS Project CA & Create SQLAlchemy Core Engines
    DBPool-->>Factory: _engine and _ai_engine initialized
    
    Factory->>Factory: Initialize Extensions (Flask-Login, CSRFProtect, Limiter)
    Factory->>Factory: Register 7 Blueprints (auth, market, investor, broker, admin, ai, reports)
    Factory->>Factory: Register Error Handlers & Security Headers Middleware
    Factory-->>WSGI: Flask application instance ready
    
    opt START_SIMULATOR == true
        WSGI->>Simulator: MarketSimulator.get_instance().start()
        Simulator->>MySQL: Acquire MySQL Advisory Lock: GET_LOCK('stocktrade_simulator', 0)
        MySQL-->>Simulator: Lock Acquired (Value: 1)
        Simulator->>MySQL: SELECT * FROM v_market_latest (Hydrate in-memory prices)
        MySQL-->>Simulator: 104 active stock records loaded
        Simulator->>Simulator: Launch background Tick Thread (0.50s) & Flush Thread (1.0s)
    end
    
    WSGI->>WSGI: Bind HTTP worker threads to 0.0.0.0:$PORT
```

---

### Diagram 3: Browser Request-to-Response Flow

```mermaid
flowchart TD
    Req["Incoming Browser Request"] --> StaticCheck{"Request Path<br>Starts with /assets/ or is /favicon.ico?"}
    
    StaticCheck -- Yes --> ServeAsset["send_from_directory('static/dist/assets')<br>(Vite JS/CSS with Cache-Control)"]
    StaticCheck -- No --> IndexCheck{"Path is '/' or '/app'?"}
    
    IndexCheck -- Yes --> CheckDist{"dist/index.html exists?"}
    CheckDist -- Yes --> ServeSPA["Serve static/dist/index.html (React SPA)"]
    CheckDist -- No --> FallbackRedirect["Redirect to auth.login or role dashboard"]
    
    IndexCheck -- No --> SecHeaders["Execute Pre-Request Hooks & CSRF Check"]
    SecHeaders --> RateLimit{"Flask-Limiter<br>Exceeded 120/min?"}
    
    RateLimit -- Yes --> Err429["Return HTTP 429 Too Many Requests"]
    RateLimit -- No --> AuthCheck{"Route decorated with<br>@login_required?"}
    
    AuthCheck -- Yes --> CheckSess{"Session Cookie Valid &<br>current_user.is_authenticated?"}
    CheckSess -- No --> Err401["Return HTTP 401 or Redirect to /login"]
    CheckSess -- Yes --> RoleCheck{"Route decorated with<br>@role_required(ROLE)?"}
    RoleCheck -- No --> Err403["Return HTTP 403 Forbidden"]
    RoleCheck -- Yes --> DispatchHandler["Execute Blueprint Route Handler"]
    
    AuthCheck -- No --> DispatchHandler
    
    DispatchHandler --> GenResponse["Generate JSON / Render HTML Template"]
    GenResponse --> PostHook["After-Request Hook:<br>Inject Security Headers & X-CSRFToken"]
    PostHook --> FinalResp["Send HTTP Response to Client"]
```

---

### Diagram 4: Database Connection Lifecycle & Pool Management

```mermaid
flowchart LR
    subgraph FlaskThread["Flask Worker Thread"]
        Handler["Route / Service Logic"]
    end

    subgraph ContextManagers["models/db.py Context Managers"]
        DBCred["get_db_connection()<br>engine.connect()"]
        DBTx["get_db_transaction()<br>engine.begin()"]
        AICred["get_ai_connection()<br>_ai_engine.connect()"]
    end

    subgraph PoolState["SQLAlchemy 2.0 Connection Pool"]
        PrePing{"Pool Pre-Ping Check<br>(SELECT 1)"}
        ActiveConn["Active Connection Checked Out"]
        RecycleCheck{"Age > 1800s?"}
    end

    subgraph MySQLSession["MySQL Server (InnoDB Session)"]
        TxBlock["BEGIN ... COMMIT / ROLLBACK"]
        ReadOnlySession["SET SESSION TRANSACTION READ ONLY<br>SET @current_user_id = :uid"]
    end

    Handler --> DBCred & DBTx & AICred
    DBCred & DBTx --> PrePing
    AICred --> PrePing
    PrePing -- Stale/Dead --> RecycleCheck
    RecycleCheck --> ActiveConn
    PrePing -- Alive --> ActiveConn

    ActiveConn --> TxBlock
    ActiveConn --> ReadOnlySession

    TxBlock -->|Auto-Commit on Exit / Rollback on Exception| ReturnPool["Return Connection to Pool<br>(Clean state restored)"]
    ReadOnlySession -->|SET @current_user_id = NULL| ReturnPool
```

---

### Diagram 5: Market Simulation & Decoupled Price Update Flow

```mermaid
sequenceDiagram
    autonumber
    participant SimWorker as MarketSimulator (Tick Thread)
    participant Memory as In-Memory Price Cache (_stocks)
    participant FlushWorker as MarketSimulator (Flush Thread)
    participant MySQL as MySQL Current_Prices & Stock_Prices
    participant SSE as SSE Subscriber Queue

    loop Every 500 milliseconds (2 ticks / second)
        SimWorker->>Memory: Read current prices per symbol
        SimWorker->>SimWorker: Calculate geometric Brownian motion step with sector volatility
        SimWorker->>SimWorker: Enforce circuit limit check (±10% from previous close)
        SimWorker->>Memory: Write updated price, day_change, day_high, day_low, volume
        SimWorker->>SSE: Broadcast delta packet to connected clients
    end

    loop Every 1.0 second (Decoupled Batch Flush)
        FlushWorker->>Memory: Acquire _cache_lock & snapshot modified prices
        FlushWorker->>MySQL: Execute batch UPDATE on Current_Prices
        FlushWorker->>MySQL: Execute batch INSERT into Stock_Prices (audit tick history)
        FlushWorker->>FlushWorker: Update last_flush_time timestamp
    end
```

---

### Diagram 6: Buy/Sell Order Execution Flow (sp_execute_trade)

```mermaid
sequenceDiagram
    autonumber
    participant Client as Investor Client
    participant Route as routes/investor.py (api_orders)
    participant Svc as services/trading_service.py
    participant MySQL as MySQL 8.0 (sp_execute_trade)
    participant Ledger as Account_Ledger (Double-Entry)

    Client->>Route: POST /investor/api/v1/investor/orders {stock_id, side, quantity}
    Route->>Svc: TradingService.execute_order(user_id, stock_id, side, quantity)
    
    Svc->>Svc: Validate positive quantity & fetch current quote
    Svc->>Svc: Calculate estimated gross amount & minimum brokerage fee (₹1.00 or 0.10%)
    
    Svc->>MySQL: CALL sp_execute_trade(user_id, stock_id, side, quantity, price, fee, @order_id, @status, @err)
    
    critical Atomic Database Transaction (InnoDB)
        MySQL->>MySQL: Lock Account: SELECT virtual_balance FROM Accounts WHERE user_id = :uid FOR UPDATE
        MySQL->>MySQL: Lock Holding: SELECT quantity, avg_cost FROM Holdings WHERE user_id = :uid AND stock_id = :sid FOR UPDATE
        
        alt BUY Order
            MySQL->>MySQL: Verify (virtual_balance >= required_cash)
            MySQL->>MySQL: Deduct cash: UPDATE Accounts SET virtual_balance = virtual_balance - required_cash
            MySQL->>MySQL: Recalculate Weighted-Average Cost: ((old_qty * old_cost) + (new_qty * price)) / total_qty
            MySQL->>MySQL: Upsert Holding: INSERT ... ON DUPLICATE KEY UPDATE quantity = quantity + :qty, avg_cost = :new_wac
        else SELL Order
            MySQL->>MySQL: Verify (holding_quantity >= sell_quantity)
            MySQL->>MySQL: Credit cash: UPDATE Accounts SET virtual_balance = virtual_balance + (gross - fee)
            MySQL->>MySQL: Decrement Holding: UPDATE Holdings SET quantity = quantity - :qty
            MySQL->>MySQL: Calculate Realized P&L: (execution_price - avg_cost) * quantity
        end
        
        MySQL->>MySQL: INSERT into Orders (status = 'EXECUTED')
        MySQL->>MySQL: INSERT into Order_Events (event_type = 'TRADE_EXECUTED')
        MySQL->>MySQL: INSERT into Transactions (gross_amount, fee, net_amount, realized_pnl)
        MySQL->>MySQL: Calculate Broker Commission (40% of fee) & INSERT into Commissions
        MySQL->>Ledger: INSERT double-entry ledger rows (immutable via trigger)
    end
    
    MySQL-->>Svc: Returns @order_id, @status = 'EXECUTED', @realized_pnl
    Svc-->>Route: Formatted trade execution receipt payload
    Route-->>Client: HTTP 201 Created {ok: true, data: {order_id, status: "EXECUTED", cash_balance...}}
```

---

### Diagram 7: AI SQL Generation, Validation & Scoped Execution Flow

```mermaid
flowchart TD
    UserPrompt["User Natural Language Prompt<br>(e.g. 'Show me all banking stocks')"] --> IntentSvc["IntentService.resolve_intent(prompt, role)"]
    
    IntentSvc --> DomainCheck{"Is prompt in<br>supported DB domain?"}
    DomainCheck -- No --> IntentReject["Log UNSUPPORTED_DOMAIN in AI_Query_History<br>Return helpful clarification message (No SQL executed)"]
    
    DomainCheck -- Yes --> RAG["RAGService.get_context_for_role(role, intent)"]
    RAG --> LLMCall["LLMRouter.complete(messages, json_mode=True)<br>(Tries Grok -> Gemini -> OpenRouter with timeout)"]
    
    LLMCall --> ParseJSON{"Valid JSON output<br>with 'sql' key?"}
    ParseJSON -- No --> FallbackIntent["IntentService.generate_sql(intent, role)<br>(Deterministic Schema-Aware SQL Fallback)"]
    
    ParseJSON -- Yes --> ASTVal["SQLValidator.validate_sql(raw_sql, role)<br>(sqlglot AST inspection)"]
    ASTVal -- Mutations or Disallowed Tables --> FallbackIntent
    
    ASTVal -- Safe AST --> SemVal["SemanticValidator.validate_consistency(prompt, intent, sql, role)"]
    SemVal -- Mismatched Sector or Arbitrary LIMIT --> FallbackIntent
    SemVal -- Consistent --> FinalSQL["Sanitized SQL Approved for Execution"]
    FallbackIntent --> FinalSQL

    FinalSQL --> QueryExec["QueryExecutor.execute_scoped_query(...)"]
    
    subgraph ExecutionSubsystem["Execution Under stocktrade_ai_ro (models/db.py)"]
        QueryExec --> SetReadOnly["SET SESSION TRANSACTION READ ONLY;"]
        SetReadOnly --> SetTenancy["SET @current_user_id = :user_id;"]
        SetTenancy --> SetTimeout["SET max_execution_time = 5000;"]
        SetTimeout --> ExecQuery["Execute SELECT on Role-Scoped View"]
        ExecQuery --> FetchRows["Fetch max 500 rows"]
        FetchRows --> ResetTenancy["SET @current_user_id = NULL;"]
    end
    
    ExecutionSubsystem --> GroundedSummary["QueryExecutor.generate_grounded_analysis(rows, columns, intent)"]
    GroundedSummary --> AuditHistory["QueryExecutor.log_query_history(...) into AI_Query_History"]
    AuditHistory --> APIResponse["Return HTTP 200 {ok: true, data: {executed_sql, rows, summary, provider}}"]
```

---

### Diagram 8: Authentication & Role-Based Authorization Flow

```mermaid
flowchart TD
    LoginReq["User submits credentials to /api/v1/auth/login<br>{identifier, password}"] --> RepoLookup["UserRepository.get_by_identifier(identifier)"]
    
    RepoLookup --> UserExists{"User exists?"}
    UserExists -- No --> DummyHash["Execute dummy hash check (timing attack prevention)"]
    DummyHash --> LogAuditFail["Log LOGIN_FAILED in Audit_Logs<br>Return HTTP 401 Invalid Credentials"]
    
    UserExists -- Yes --> CheckLockout{"Is account locked?<br>(locked_until > NOW())"}
    CheckLockout -- Yes --> LogAuditLock["Log LOGIN_LOCKED in Audit_Logs<br>Return HTTP 403 Account Temporarily Locked"]
    
    CheckLockout -- No --> CheckPW{"AuthService.verify_password()<br>(Werkzeug PBKDF2 / scrypt)"}
    CheckPW -- No --> IncFail["Increment failed_login_attempts"]
    IncFail --> CheckBrute{"Failed attempts >= 5?"}
    CheckBrute -- Yes --> LockAccount["Set locked_until = NOW() + 15 mins<br>Log SECURITY_LOCKOUT in Audit_Logs"]
    CheckBrute -- No --> LogAuditFail
    LockAccount --> LogAuditFail
    
    CheckPW -- Yes --> ResetFail["Reset failed_login_attempts = 0<br>Update last_login_at = NOW()"]
    ResetFail --> FlaskLogin["login_user(user, remember=False)"]
    FlaskLogin --> SetCookie["Set session cookie (HttpOnly, SameSite=Lax)"]
    SetCookie --> LogSuccess["Log LOGIN_SUCCESS in Audit_Logs"]
    LogSuccess --> ReturnUser["Return HTTP 200 {ok: true, data: {user: {id, username, role, full_name}}}"]
    
    ReturnUser --> RoleRouting{"User Role"}
    RoleRouting -- ADMIN --> AdminPortal["Permitted: /admin/*, /market/*, /ai/*<br>Blocked: /investor/*, /broker/*"]
    RoleRouting -- BROKER --> BrokerPortal["Permitted: /broker/*, /market/*, /ai/*<br>Blocked: /admin/*, /investor/*"]
    RoleRouting -- INVESTOR --> InvestorPortal["Permitted: /investor/*, /market/*, /ai/*<br>Blocked: /admin/*, /broker/*"]
```
