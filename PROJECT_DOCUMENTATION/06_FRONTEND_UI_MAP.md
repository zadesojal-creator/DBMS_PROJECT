# StockTrade v2 — Frontend & UI Architecture Map

This document catalogs the complete user interface implementation across both the **React 18 Single-Page Application (SPA)** and the **Jinja2 server-rendered fallback templates**, establishing the source of truth for all components and styling conventions.

---

## 1. Dual-UI Architecture & Source of Truth

StockTrade v2 features a dual-presentation architecture designed for high availability:

1. **Primary Interface: React 18 SPA (Vite Bundled)**:
   - Location: `frontend/src/`
   - Build Output: `static/dist/`
   - Served by Flask at `/`, `/app`, and `/assets/*` via `app.py`.
   - Reactive, client-side tab navigation managed in `frontend/src/App.jsx`.
   - Rich interactive features: live Chart.js candlestick charts, dynamic trade tickets, instant search filtering, real-time ticker badges, and interactive SQL result viewers.

2. **Secondary Interface: Jinja2 Server-Rendered Views**:
   - Location: `templates/`
   - Served by Flask blueprint endpoints (e.g. `/market/`, `/investor/dashboard`, `/broker/clients`, `/admin/overview`).
   - Enables standard multi-page browser navigation without JavaScript dependencies.
   - Master layout defined in `templates/base.html`, using macros from `templates/macros/components.html`.

---

## 2. Design System & CSS Conventions

The visual presentation adheres to a fintech terminal aesthetic. The palette balances dark institutional navy with crisp white and glowing teal accents.

### Color Tokens (`static/css/design-system.css` & `frontend/src/styles/index.css`)

```css
:root {
  /* Brand Accents */
  --teal: #00A884;              /* Brand accent, active tabs, buttons */
  --teal-glow: rgba(0, 168, 132, 0.25);
  --cyan: #14B8A6;              /* Gradient highlight */
  
  /* Market Action Colors */
  --green: #10B981;             /* Positive price delta / Buy side */
  --green-bg: #ECFDF5;
  --red: #EF4444;               /* Negative price delta / Sell side */
  --red-bg: #FEF2F2;

  /* Dark Terminal Surface (Left Side & Brand Elements) */
  --terminal-navy: #09151C;     /* Deep midnight background */
  --terminal-teal: #0E2A2F;     /* Subtle teal container background */
  --navy: #0F172A;              /* Heading slate */

  /* Neutral Surfaces (Right Side & Main Content) */
  --bg: #F8FAFC;                /* App body background */
  --surface: #FFFFFF;           /* Card & modal containers */
  --surface-alt: #F1F5F9;       /* Input backgrounds & table headers */
  --border: #E2E8F0;            /* Subtle borders & dividers */
  --muted: #64748B;             /* Subtitles & metadata text */

  /* Layout Spacing & Radius */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}
```

---

## 3. Page & Route Presentation Inventory

| Route / View | React Component | Jinja2 Template | Primary Data Displayed | User Actions Available |
| :--- | :--- | :--- | :--- | :--- |
| **Login Terminal** | `frontend/src/pages/Login.jsx` | `templates/auth/login.html` | Asymmetrical split login card, live market ticker tape, bull silhouette | Enter credentials; toggle password visibility; click demo account pill; login error alert |
| **Investor Dashboard** | `frontend/src/pages/investor/DashboardView.jsx` | `templates/investor/dashboard.html` | Buying power KPI, total portfolio value, realized P&L, recent trades list | Quick deposit trigger, buy/sell trade ticket trigger, stock search |
| **Stock Screener (Market)**| `frontend/src/pages/investor/MarketView.jsx` | `templates/market/overview.html` | 104 equities table with sector tags, prices, 24h change %, volume | Filter by sector pill, search by ticker/company, open chart modal, open trade modal |
| **Portfolio Positions** | `frontend/src/pages/investor/PortfolioView.jsx` | `templates/investor/portfolio.html` | Open positions: symbol, quantity, avg cost, current price, market value, P&L % | Sell position trigger, buy more trigger, export holdings |
| **Trade Transactions** | `frontend/src/pages/investor/TransactionsView.jsx` | `templates/investor/transactions.html` | Executed trades table: side badge, quantity, executed price, fee, realized P&L | Download CSV statement, filter by date |
| **Watchlist & Alerts** | `frontend/src/pages/investor/WatchlistView.jsx` | `templates/investor/watchlist.html` | Personal monitored stocks table; active price alerts list | Remove stock from watchlist, create `ABOVE`/`BELOW` alert, cancel active alert |
| **Broker Roster** | `frontend/src/pages/broker/ClientsView.jsx` | `templates/broker/clients.html` | Assigned clients table: investor name, email, cash, volume, commissions | Onboard new client modal trigger, view client profile drawer, end assignment |
| **Broker Analytics** | `frontend/src/pages/broker/AnalyticsView.jsx` | `templates/broker/analytics.html` | Total commission earned KPI, client turnover chart, daily earnings breakdown | Date range filter, view trade attribution details |
| **Admin Overview** | `frontend/src/pages/admin/OverviewView.jsx` | `templates/admin/overview.html` | System-wide counters: total users, active stocks, daily trade turnover, fees | Trigger financial reconciliation audit, view system health |
| **Company Directory** | `frontend/src/pages/admin/CompaniesView.jsx` | `templates/admin/companies.html` | Listed companies CRUD table: symbol, sector, exchange, status badge | Add new equity modal, edit company, toggle active/inactive status |
| **User Directory** | `frontend/src/pages/admin/UsersView.jsx` | `templates/admin/users.html` | User accounts table: username, role, status, failed login count, lockout badge | Reset lockout trigger, toggle user active/inactive status |
| **Security Audit Logs** | `frontend/src/pages/admin/AuditLogsView.jsx` | `templates/admin/audit_logs.html` | Immutable audit log table: timestamp, user, action badge, entity, IP address | Filter by action type, filter by IP address |
| **Simulator Control** | `frontend/src/pages/admin/SimulatorView.jsx` | None (SPA only) | Ticking status pill, tick frequency slider, volatility multiplier | Pause/resume simulation, adjust tick speed, change volatility |
| **AI SQL Console** | `frontend/src/pages/ai/AssistantView.jsx` | `templates/ai/assistant.html` | Dual-mode console: Natural language prompt input & Manual SQL editor | Submit plain-English prompt, edit/run SQL, view result grid, view query history |

---

## 4. Reusable Frontend Component Inventory (`frontend/src/components/`)

1. **`BullLogo.jsx`**: Minimalist geometric vector SVG logo depicting a charging bull with subtle emerald gradients.
2. **`Navbar.jsx`**: Fixed top terminal bar displaying the brand wordmark, `<SimulatedBadge />`, global stock search input, active user full name, role pill, and sign-out button.
3. **`Sidebar.jsx`**: Collapsible left navigation drawer containing role-specific navigation pills (`Dashboard`, `Market`, `Watchlist`, `Portfolio`, `Transactions`, `Clients`, `Analytics`, `AI Assistant`, etc.).
4. **`SimulatedBadge.jsx`**: Live status pill that polls `/market/api/v1/market/status` every 5 seconds. Displays a glowing green dot when ticking, amber when paused, and red if stale.
5. **`KpiTile.jsx`**: Minimalist metric card displaying title, formatted numerical value (currency or percentage), positive/negative trend icon, and optional sub-caption.
6. **`TradeTicketModal.jsx`**: Modal order submission dialog:
   - Displays real-time stock quote and day change.
   - BUY / SELL side selector with distinct color themes (green for buy, red for sell).
   - Real-time quantity stepper and total gross calculation.
   - Automated brokerage fee estimate (0.10% or ₹1.00 min) and total net settlement value.
   - Idempotent submission with disabled state during in-flight network requests.
7. **`DepositModal.jsx`**: Virtual cash deposit dialog with preset quick-select buttons (+₹10,000, +₹50,000, +₹100,000) and custom input field with instant ledger credit preview.
8. **`StockChartModal.jsx`**: Full-screen or modal interactive chart dialog powered by `Chart.js` rendering historical OHLC candlestick/line data across 1D, 1W, and 1M intervals.
9. **`OnboardClientModal.jsx`**: Broker modal allowing selection of unassigned investor accounts from a dropdown list to establish an active broker-investor assignment.
10. **`SqlResultViewer.jsx`**: Universal tabular data grid rendering columns and rows returned by the AI SQL Assistant or Manual SQL Console. Automatically detects numeric and monetary columns, formats timestamps, and provides client-side column header sorting.

---

## 5. Client API Integration & CSRF Handling (`frontend/src/api/client.js`)

All frontend network requests pass through the unified `request()` wrapper in `frontend/src/api/client.js`:

```javascript
async function request(url, options = {}) {
  const headers = {
    'Accept': 'application/json',
    ...(options.headers || {})
  };

  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  // Automatically attach CSRF token if present
  const token = getCsrfToken();
  if (token) {
    headers['X-CSRFToken'] = token;
  }

  options.credentials = 'include';
  options.headers = headers;

  const res = await fetch(url, options);

  // Capture CSRF token updated in response headers
  const headerCsrf = res.headers.get('X-CSRFToken');
  if (headerCsrf) {
    cachedCsrfToken = headerCsrf;
  }

  const json = await res.json().catch(() => null);

  if (!res.ok) {
    const errorMsg = json?.error?.message || json?.message || `HTTP ${res.status}: ${res.statusText}`;
    const err = new Error(errorMsg);
    err.status = res.status;
    err.code = json?.error?.code;
    err.data = json;
    throw err;
  }

  return json;
}
```

### Critical Preserved Behaviors:
- **Automatic CSRF Header Capture**: Any mutating route (`POST`, `PUT`, `DELETE`) automatically includes `X-CSRFToken`.
- **Session Credentials**: All requests include `credentials: 'include'` to pass Flask's encrypted session cookie across ports (e.g. 3000 $\to$ 5000 in development).
- **Asymmetrical Split Login Screen**: The high-end dark brand side (60%) and crisp white login card (40%) must not be reverted to a generic centered login box.
- **Tab Persistence**: Active tab state is preserved based on user role upon login (`admin` $\to$ `overview`, `broker` $\to$ `clients`, `investor` $\to$ `dashboard`).
