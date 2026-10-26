/**
 * StockTrade API Client
 * Centralized fetch client with automatic CSRF token handling, credentials, and error wrapping.
 */

let cachedCsrfToken = null;

export function setCsrfToken(token) {
  cachedCsrfToken = token;
}

export function getCsrfToken() {
  if (cachedCsrfToken) return cachedCsrfToken;
  // Try extracting from document cookie
  const match = document.cookie.match(/csrf_access_token=([^;]+)/);
  if (match) return match[1];
  return null;
}

async function request(url, options = {}) {
  const headers = {
    'Accept': 'application/json',
    ...(options.headers || {})
  };

  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  const token = getCsrfToken();
  if (token) {
    headers['X-CSRFToken'] = token;
  }

  options.credentials = 'include';
  options.headers = headers;

  const res = await fetch(url, options);

  // Capture CSRF token if returned in header
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

export const api = {
  // Auth
  auth: {
    login: (identifier, password) => request('/api/v1/auth/login', {
      method: 'POST',
      body: { identifier, password }
    }),
    logout: () => request('/api/v1/auth/logout', { method: 'POST' }),
    session: () => request('/api/v1/auth/session')
  },

  // Market
  market: {
    getPrices: (since = null) => {
      const url = since ? `/market/api/v1/market/prices?since=${encodeURIComponent(since)}` : '/market/api/v1/market/prices';
      return request(url);
    },
    getHistory: (symbol, interval = '5m') => 
      request(`/market/api/v1/market/history?symbol=${symbol}&interval=${interval}`),
    getStatus: () => request('/market/api/v1/market/status')
  },

  // Investor
  investor: {
    getSummary: () => request('/investor/api/v1/investor/summary'),
    getHoldings: () => request('/investor/api/v1/investor/holdings'),
    getTransactions: (limit = 50) => request(`/investor/api/v1/investor/transactions?limit=${limit}`),
    executeOrder: (payload) => request('/investor/api/v1/investor/orders', {
      method: 'POST',
      body: payload
    }),
    deposit: (payload) => request('/investor/api/v1/investor/deposit', {
      method: 'POST',
      body: payload
    }),
    getWatchlist: () => request('/investor/api/v1/investor/watchlist'),
    addToWatchlist: (stockId) => request('/investor/api/v1/investor/watchlist', {
      method: 'POST',
      body: { stock_id: stockId }
    }),
    removeFromWatchlist: (stockId) => request(`/investor/api/v1/investor/watchlist/${stockId}`, {
      method: 'DELETE'
    }),
    getAlerts: (status = null) => {
      const url = status ? `/investor/api/v1/investor/alerts?status=${encodeURIComponent(status)}` : '/investor/api/v1/investor/alerts';
      return request(url);
    },
    createAlert: (payload) => request('/investor/api/v1/investor/alerts', {
      method: 'POST',
      body: payload
    }),
    cancelAlert: (alertId) => request(`/investor/api/v1/investor/alerts/${alertId}`, {
      method: 'DELETE'
    }),
    getAssignedBroker: () => request('/investor/api/v1/investor/broker')
  },

  // Broker
  broker: {
    getClients: () => request('/broker/api/v1/broker/clients'),
    onboardClient: (payload) => request('/broker/api/v1/broker/clients', {
      method: 'POST',
      body: payload
    }),
    getClientProfile: (investorId) => request(`/broker/api/v1/broker/client-profile?investor_id=${investorId}`),
    endAssignment: (investorId) => request(`/broker/api/v1/broker/clients/${investorId}/end`, {
      method: 'POST'
    }),
    getAnalytics: () => request('/broker/api/v1/broker/analytics')
  },

  // Admin
  admin: {
    getOverview: () => request('/admin/api/v1/admin/overview'),
    getCompanies: (sector = null, search = null) => {
      let q = [];
      if (sector) q.push(`sector=${encodeURIComponent(sector)}`);
      if (search) q.push(`search=${encodeURIComponent(search)}`);
      return request(`/admin/api/v1/admin/companies${q.length ? '?' + q.join('&') : ''}`);
    },
    createCompany: (payload) => request('/admin/api/v1/admin/companies', {
      method: 'POST',
      body: payload
    }),
    updateCompany: (id, payload) => request(`/admin/api/v1/admin/companies/${id}`, {
      method: 'PUT',
      body: payload
    }),
    deleteCompany: (id) => request(`/admin/api/v1/admin/companies/${id}`, {
      method: 'DELETE'
    }),
    getUsers: () => request('/admin/api/v1/admin/users'),
    toggleUserStatus: (id, status) => request(`/admin/api/v1/admin/users/${id}/status`, {
      method: 'PATCH',
      body: { status }
    }),
    resetLockout: (id) => request(`/admin/api/v1/admin/users/${id}/reset-lockout`, {
      method: 'POST'
    }),
    getSimulatorStatus: () => request('/admin/api/v1/admin/simulator/status'),
    controlSimulator: (action) => request('/admin/api/v1/admin/simulator/control', {
      method: 'POST',
      body: { action }
    }),
    getAuditLogs: (limit = 100) => request(`/admin/api/v1/admin/audit-logs?limit=${limit}`),
    getCommissionRules: () => request('/admin/api/v1/admin/commission-rules'),
    updateCommissionRule: (payload) => request('/admin/api/v1/admin/commission-rules', {
      method: 'POST',
      body: payload
    })
  },

  // AI Assistant & Manual SQL
  ai: {
    query: (prompt) => request('/ai/api/v1/ai/query', {
      method: 'POST',
      body: { prompt }
    }),
    executeSql: (sql, prompt = '') => request('/ai/api/v1/ai/execute', {
      method: 'POST',
      body: { sql, prompt, provider: 'MANUAL_SQL' }
    }),
    generate: (prompt) => request('/ai/api/v1/ai/generate', {
      method: 'POST',
      body: { prompt }
    }),
    getHistory: () => request('/ai/api/v1/ai/history'),
    getSchema: () => request('/ai/api/v1/ai/schema')
  }
};
