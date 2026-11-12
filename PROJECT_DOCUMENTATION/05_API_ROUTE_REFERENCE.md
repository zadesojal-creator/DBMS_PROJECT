# StockTrade v2 — REST API & Route Reference

This document catalogs every HTTP route registered in StockTrade v2, documenting handler functions, authentication/role requirements, parameter schemas, database dependencies, and frontend callers.

---

## 1. Authentication Blueprint (`routes/auth.py` — Prefix: `/api/v1/auth`)

| Method | URL Pattern | Endpoint | Auth | Role | Request Parameters / Body | Response Schema / Important Fields | DB Objects & Services | Frontend Caller |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/login` | `auth.login` | None | Any | None | Server-rendered HTML (`templates/auth/login.html`) | `Users` | Direct browser navigation |
| `POST` | `/api/v1/auth/login` | `auth.api_login` | None | Any | JSON: `{identifier, password}` | `200 OK`: `{ok: true, data: {user: {id, username, email, full_name, role}}}`<br>`401`: `{ok: false, error: "Invalid credentials"}`<br>`403`: `{ok: false, error: "Account locked"}` | `UserRepository`<br>`AuthService`<br>`Audit_Logs` | `frontend/src/api/client.js`<br>`api.auth.login()` |
| `GET` | `/api/v1/auth/session` | `auth.api_session` | None | Any | Session Cookie | `200 OK`: `{ok: true, data: {authenticated: bool, user: {...}}}` | `Users` | `frontend/src/context/AuthContext.jsx` |
| `POST` | `/api/v1/auth/logout` | `auth.api_logout` | Required | Any | None | `200 OK`: `{ok: true, data: {message: "Logged out"}}` | `Audit_Logs` | `frontend/src/api/client.js`<br>`api.auth.logout()` |

---

## 2. Market Blueprint (`routes/market.py` — Prefix: `/market`)

| Method | URL Pattern | Endpoint | Auth | Role | Request Parameters / Body | Response Schema / Important Fields | DB Objects & Services | Frontend Caller |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/market/` | `market.overview` | Required | Any | None | Server-rendered HTML (`templates/market/overview.html`) | `v_market_latest` | Direct browser navigation |
| `GET` | `/market/<symbol>` | `market.stock_detail`| Required | Any | Path: `symbol` (e.g. `TCS`) | Server-rendered HTML (`templates/market/detail.html`) | `Stocks`<br>`Current_Prices` | Direct browser navigation |
| `GET` | `/market/api/v1/market/prices` | `market.api_prices` | None | Any | Query: `since` (optional ISO timestamp) | `200 OK`: `{ok: true, data: [{stock_id, symbol, company_name, sector, current_price, previous_close, day_change, day_change_pct, volume, updated_at}]}` | `MarketSimulator._stocks`<br>`v_market_latest` | `frontend/src/api/client.js`<br>`api.market.getPrices()` |
| `GET` | `/market/api/v1/market/history`| `market.api_history`| None | Any | Query: `symbol` (required), `interval` (`1m`, `5m`, `1h`, `1d`) | `200 OK`: `{ok: true, data: {symbol, interval, candles: [{time, open, high, low, close, volume}]}}` | `Stock_Prices`<br>`Stock_Price_Hourly` | `frontend/src/components/StockChartModal.jsx` |
| `GET` | `/market/api/v1/market/status` | `market.api_status` | None | Any | None | `200 OK`: `{ok: true, data: {is_running, tick_interval_sec, total_ticks, is_stale}}` | `MarketSimulator` instance | `frontend/src/components/SimulatedBadge.jsx` |
| `GET` | `/market/api/v1/market/stream` | `market.api_stream` | None | Any | None | Server-Sent Events (`text/event-stream`): `data: {prices: [...]}` | `MarketSimulator._subscribers` | SSE EventSource client |

---

## 3. Investor Blueprint (`routes/investor.py` — Prefix: `/investor`)

| Method | URL Pattern | Endpoint | Auth | Role | Request Parameters / Body | Response Schema / Important Fields | DB Objects & Services | Frontend Caller |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/investor/dashboard` | `investor.dashboard` | Required | INVESTOR | None | Server-rendered HTML (`templates/investor/dashboard.html`) | `Accounts`, `Holdings` | Direct browser navigation |
| `GET` | `/investor/portfolio` | `investor.portfolio` | Required | INVESTOR | None | Server-rendered HTML (`templates/investor/portfolio.html`) | `v_investor_portfolio` | Direct browser navigation |
| `GET` | `/investor/trade` | `investor.trade` | Required | INVESTOR | None | Server-rendered HTML (`templates/investor/trade.html`) | `Stocks`, `Accounts` | Direct browser navigation |
| `GET` | `/investor/transactions` | `investor.transactions` | Required | INVESTOR | None | Server-rendered HTML (`templates/investor/transactions.html`) | `v_investor_transactions` | Direct browser navigation |
| `GET` | `/investor/watchlist` | `investor.watchlist` | Required | INVESTOR | None | Server-rendered HTML (`templates/investor/watchlist.html`) | `Watchlist` | Direct browser navigation |
| `GET` | `/investor/account` | `investor.account` | Required | INVESTOR | None | Server-rendered HTML (`templates/investor/account.html`) | `Accounts`, `Account_Ledger` | Direct browser navigation |
| `GET` | `/investor/broker` | `investor.broker` | Required | INVESTOR | None | Server-rendered HTML (`templates/investor/broker.html`) | `Broker_Clients`, `Users` | Direct browser navigation |
| `GET` | `/investor/api/v1/investor/summary` | `investor.api_summary` | Required | INVESTOR | None | `200 OK`: `{ok: true, data: {virtual_balance, total_portfolio_value, holdings_value, unrealized_pnl, realized_pnl}}` | `PortfolioService`<br>`Accounts`, `Holdings` | `frontend/src/api/client.js`<br>`api.investor.getSummary()` |
| `GET` | `/investor/api/v1/investor/holdings`| `investor.api_holdings`| Required | INVESTOR | None | `200 OK`: `{ok: true, data: [{stock_id, symbol, company_name, quantity, avg_cost, current_price, market_value, unrealized_pnl}]}` | `v_investor_portfolio` | `frontend/src/api/client.js`<br>`api.investor.getHoldings()` |
| `POST` | `/investor/api/v1/investor/orders` | `investor.api_orders` | Required | INVESTOR | JSON: `{stock_id, side, quantity, idempotency_key}` | `201 Created`: `{ok: true, data: {order_id, transaction_id, execution_price, status: "EXECUTED", gross_amount, brokerage_fee, net_amount}}`<br>`422`: Validation error | `sp_execute_trade`<br>`TradingService` | `frontend/src/components/TradeTicketModal.jsx` |
| `POST` | `/investor/api/v1/investor/deposit`| `investor.api_deposit`| Required | INVESTOR | JSON: `{amount, idempotency_key}` | `200 OK`: `{ok: true, data: {new_balance, deposit_amount, ledger_entry_id}}` | `Accounts`<br>`Account_Ledger` | `frontend/src/components/DepositModal.jsx` |
| `GET` | `/investor/api/v1/investor/transactions`| `investor.api_transactions`| Required | INVESTOR | Query: `limit` (default 50) | `200 OK`: `{ok: true, data: [{transaction_id, symbol, side, quantity, execution_price, net_amount, realized_pnl, executed_at}]}` | `v_investor_transactions` | `frontend/src/pages/investor/TransactionsView.jsx` |
| `GET` | `/investor/api/v1/investor/watchlist`| `investor.api_watchlist`| Required | INVESTOR | None | `200 OK`: `{ok: true, data: [{stock_id, symbol, company_name, sector, current_price, day_change_pct}]}` | `Watchlist`<br>`v_market_latest` | `frontend/src/pages/investor/WatchlistView.jsx` |
| `POST` | `/investor/api/v1/investor/watchlist`| `investor.api_add_watchlist`| Required | INVESTOR | JSON: `{stock_id}` | `201 Created`: `{ok: true, data: {stock_id, added_at}}` | `Watchlist` | `frontend/src/pages/investor/WatchlistView.jsx` |
| `DELETE`| `/investor/api/v1/investor/watchlist/<id>`| `investor.api_del_watchlist`| Required | INVESTOR | Path: `id` (stock_id) | `200 OK`: `{ok: true, data: {message: "Removed"}}` | `Watchlist` | `frontend/src/pages/investor/WatchlistView.jsx` |
| `GET` | `/investor/api/v1/investor/alerts` | `investor.api_alerts` | Required | INVESTOR | Query: `status` (default `ACTIVE`) | `200 OK`: `{ok: true, data: [{alert_id, symbol, target_price, condition_type, status, created_at}]}` | `Price_Alerts` | `frontend/src/pages/investor/WatchlistView.jsx` |
| `POST` | `/investor/api/v1/investor/alerts` | `investor.api_create_alert`| Required | INVESTOR | JSON: `{stock_id, target_price, condition_type}` | `201 Created`: `{ok: true, data: {alert_id, status: "ACTIVE"}}` | `Price_Alerts` | `frontend/src/pages/investor/WatchlistView.jsx` |
| `DELETE`| `/investor/api/v1/investor/alerts/<id>`| `investor.api_cancel_alert`| Required | INVESTOR | Path: `id` (alert_id) | `200 OK`: `{ok: true, data: {message: "Cancelled"}}` | `Price_Alerts` | `frontend/src/pages/investor/WatchlistView.jsx` |
| `GET` | `/investor/api/v1/investor/broker` | `investor.api_assigned_broker`| Required | INVESTOR | None | `200 OK`: `{ok: true, data: {has_broker, broker: {id, full_name, email, firm, assigned_at}}}` | `Broker_Clients`<br>`Users` | `frontend/src/api/client.js`<br>`api.investor.getAssignedBroker()` |

---

## 4. Broker Blueprint (`routes/broker.py` — Prefix: `/broker`)

| Method | URL Pattern | Endpoint | Auth | Role | Request Parameters / Body | Response Schema / Important Fields | DB Objects & Services | Frontend Caller |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/broker/overview` | `broker.overview` | Required | BROKER | None | Server-rendered HTML (`templates/broker/overview.html`) | `Stocks` | Direct browser navigation |
| `GET` | `/broker/clients` | `broker.clients` | Required | BROKER | None | Server-rendered HTML (`templates/broker/clients.html`) | `v_broker_client_summary` | Direct browser navigation |
| `GET` | `/broker/analytics` | `broker.analytics` | Required | BROKER | None | Server-rendered HTML (`templates/broker/analytics.html`) | `v_broker_commissions` | Direct browser navigation |
| `GET` | `/broker/api/v1/broker/clients` | `broker.api_clients` | Required | BROKER | None | `200 OK`: `{ok: true, data: [{investor_id, investor_name, investor_email, virtual_balance, total_trades, total_volume, total_commission_generated}]}` | `v_broker_client_summary` | `frontend/src/pages/broker/ClientsView.jsx` |
| `POST` | `/broker/api/v1/broker/clients` | `broker.api_onboard` | Required | BROKER | JSON: `{investor_id}` | `201 Created`: `{ok: true, data: {investor_id, broker_id, assigned_at}}` | `Broker_Clients`<br>`Users` | `frontend/src/components/OnboardClientModal.jsx` |
| `GET` | `/broker/api/v1/broker/client-profile`| `broker.api_client_profile`| Required | BROKER | Query: `investor_id` | `200 OK`: `{ok: true, data: {profile, holdings, recent_transactions}}`<br>`404`: Client not assigned | `v_broker_client_transactions`<br>`Holdings` | `frontend/src/pages/broker/ClientsView.jsx` |
| `POST` | `/broker/api/v1/broker/clients/<id>/end`| `broker.api_end_assignment`| Required | BROKER | Path: `id` (investor_id) | `200 OK`: `{ok: true, data: {message: "Assignment ended"}}` | `Broker_Clients` | `frontend/src/pages/broker/ClientsView.jsx` |
| `GET` | `/broker/api/v1/broker/analytics` | `broker.api_analytics` | Required | BROKER | None | `200 OK`: `{ok: true, data: {total_commission, client_count, volume_30d, daily_commissions}}` | `v_broker_commissions` | `frontend/src/pages/broker/AnalyticsView.jsx` |

---

## 5. Admin Blueprint (`routes/admin.py` — Prefix: `/admin`)

| Method | URL Pattern | Endpoint | Auth | Role | Request Parameters / Body | Response Schema / Important Fields | DB Objects & Services | Frontend Caller |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/admin/overview` | `admin.overview` | Required | ADMIN | None | Server-rendered HTML (`templates/admin/overview.html`) | `Stocks`, `Users` | Direct browser navigation |
| `GET` | `/admin/companies` | `admin.companies` | Required | ADMIN | None | Server-rendered HTML (`templates/admin/companies.html`) | `Stocks` | Direct browser navigation |
| `GET` | `/admin/users` | `admin.users` | Required | ADMIN | None | Server-rendered HTML (`templates/admin/users.html`) | `v_admin_user_audit` | Direct browser navigation |
| `GET` | `/admin/audit-logs` | `admin.audit_logs` | Required | ADMIN | None | Server-rendered HTML (`templates/admin/audit_logs.html`) | `v_admin_audit_logs` | Direct browser navigation |
| `GET` | `/admin/api/v1/admin/overview` | `admin.api_overview` | Required | ADMIN | None | `200 OK`: `{ok: true, data: {total_users, active_stocks, trade_volume_today, fees_collected}}` | `v_admin_trade_facts`<br>`Users`, `Stocks` | `frontend/src/pages/admin/OverviewView.jsx` |
| `GET` | `/admin/api/v1/admin/companies` | `admin.api_companies` | Required | ADMIN | Query: `sector`, `status` | `200 OK`: `{ok: true, data: [{id, symbol, company_name, sector, exchange, status}]}` | `Stocks` | `frontend/src/pages/admin/CompaniesView.jsx` |
| `POST` | `/admin/api/v1/admin/companies` | `admin.api_create_company`| Required | ADMIN | JSON: `{symbol, company_name, sector, exchange, initial_price}` | `201 Created`: `{ok: true, data: {id, symbol}}` | `Stocks`<br>`Current_Prices` | `frontend/src/pages/admin/CompaniesView.jsx` |
| `PUT` | `/admin/api/v1/admin/companies/<id>`| `admin.api_update_company`| Required | ADMIN | Path: `id`, JSON: `{company_name, sector, status}` | `200 OK`: `{ok: true, data: {message: "Updated"}}` | `Stocks` | `frontend/src/pages/admin/CompaniesView.jsx` |
| `DELETE`| `/admin/api/v1/admin/companies/<id>`| `admin.api_delete_company`| Required | ADMIN | Path: `id` | `200 OK`: `{ok: true, data: {message: "Deactivated"}}` | `Stocks` (soft delete: status='INACTIVE') | `frontend/src/pages/admin/CompaniesView.jsx` |
| `GET` | `/admin/api/v1/admin/users` | `admin.api_users` | Required | ADMIN | None | `200 OK`: `{ok: true, data: [{id, username, email, full_name, role, status, failed_login_attempts, is_locked, locked_until}]}` | `v_admin_user_audit` | `frontend/src/pages/admin/UsersView.jsx` |
| `POST` | `/admin/api/v1/admin/users/<id>/reset-lockout` | `admin.api_reset_lockout` | Required | ADMIN | Path: `id` (user_id) | `200 OK`: `{ok: true, data: {message: "Lockout cleared"}}` | `Users` | `frontend/src/pages/admin/UsersView.jsx` |
| `POST` | `/admin/api/v1/admin/users/<id>/status` | `admin.api_toggle_user_status`| Required | ADMIN | Path: `id`, JSON: `{status: "ACTIVE"|"INACTIVE"}` | `200 OK`: `{ok: true, data: {message: "Status updated"}}` | `Users` | `frontend/src/pages/admin/UsersView.jsx` |
| `GET` | `/admin/api/v1/admin/audit-logs` | `admin.api_audit_logs`| Required | ADMIN | Query: `limit` (default 100), `action` | `200 OK`: `{ok: true, data: [{log_id, username, role, action, entity_type, entity_id, ip_address, created_at}]}` | `v_admin_audit_logs` | `frontend/src/pages/admin/AuditLogsView.jsx` |
| `GET` | `/admin/api/v1/admin/simulator/status` | `admin.api_simulator_status`| Required | ADMIN | None | `200 OK`: `{ok: true, data: {is_running, is_paused, tick_interval_sec, total_ticks}}` | `MarketSimulator` | `frontend/src/pages/admin/SimulatorView.jsx` |
| `POST` | `/admin/api/v1/admin/simulator/control`| `admin.api_simulator_control`| Required | ADMIN | JSON: `{action: "pause"|"resume"|"speed", value}` | `200 OK`: `{ok: true, data: {status: "updated"}}` | `MarketSimulator` | `frontend/src/pages/admin/SimulatorView.jsx` |
| `POST` | `/admin/api/v1/admin/reconcile` | `admin.api_reconcile`| Required | ADMIN | None | `200 OK`: `{ok: true, data: {discrepancies_found: int, audit_results: [...]}}` | `sp_reconcile_financial_integrity` | Backend / CLI admin tool |

---

## 6. AI Assistant Blueprint (`routes/ai.py` — Prefix: `/ai`)

| Method | URL Pattern | Endpoint | Auth | Role | Request Parameters / Body | Response Schema / Important Fields | DB Objects & Services | Frontend Caller |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/ai/assistant` | `ai.assistant` | Required | Any | None | Server-rendered HTML (`templates/ai/assistant.html`) | None | Direct browser navigation |
| `POST` | `/ai/api/v1/ai/generate` | `ai.api_generate` | Required | Any | JSON: `{prompt}` | `200 OK`: `{ok: true, data: {sql, tables, explanation, validation_status: "VALID", provider}}` | `IntentService`<br>`LLMRouter`<br>`SQLValidator` | `frontend/src/pages/ai/AssistantView.jsx` |
| `POST` | `/ai/api/v1/ai/execute` | `ai.api_execute` | Required | Any | JSON: `{sql, prompt, provider}` | `200 OK`: `{ok: true, data: {executed_sql, columns, rows, row_count, duration_ms, summary, provider}}`<br>`422`: AST validation rejected | `stocktrade_ai_ro`<br>`QueryExecutor`<br>`AI_Query_History` | `frontend/src/pages/ai/AssistantView.jsx`<br>(Manual SQL console) |
| `POST` | `/ai/api/v1/ai/query` | `ai.api_query` | Required | Any | JSON: `{prompt}` | `200 OK`: `{ok: true, data: {generated_sql, executed_sql, provider_used, columns, rows, row_count, duration_ms, summary, explanation}}` | Combined Intent + AST + Execute pipeline | `frontend/src/pages/ai/AssistantView.jsx`<br>(AI Assistant tab) |
| `GET` | `/ai/api/v1/ai/history` | `ai.api_history` | Required | Any | Query: `limit` (default 20, max 100) | `200 OK`: `{ok: true, data: [{id, prompt, generated_sql, validation_status, duration_ms, created_at}]}` | `AI_Query_History` | `frontend/src/pages/ai/AssistantView.jsx` (History drawer) |
| `GET` | `/ai/api/v1/ai/schema` | `ai.api_schema` | Required | Any | None | `200 OK`: `{ok: true, data: [{view, description, columns, sample}]}` | In-memory schema definitions | `frontend/src/pages/ai/AssistantView.jsx` (Schema drawer) |

---

## 7. Reports Blueprint & Root Application Routes

| Method | URL Pattern | Endpoint | Auth | Role | Request Parameters / Body | Response Schema / Important Fields | DB Objects & Services | Frontend Caller |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/reports/api/v1/reports/transactions/csv`| `reports.export_transactions`| Required | Any | Query: `limit` (default 500) | `200 OK`: RFC 4180 CSV attachment (`Content-Disposition: attachment; filename=transactions_....csv`) | `Transactions`<br>`Stocks` | `frontend/src/pages/investor/TransactionsView.jsx` |
| `GET` | `/health` | `health` | None | Any | None | `200 OK`: `{status: "healthy", system: "StockTrade Simulated Platform", timestamp: "..."}` | None (Flask runtime) | Render health check / uptime monitor |
| `GET` | `/` and `/app` | `index` | None | Any | None | Serves `static/dist/index.html` (React SPA) or redirects to login/portal if HTML client | `static/dist/index.html` | Client root URL |
| `GET` | `/assets/<path>` | `serve_assets` | None | Any | Path: asset filename | Raw JS/CSS with MIME type (`text/javascript`, `text/css`) | `static/dist/assets/*` | React index asset loaders |
