import React, { useState, useEffect } from 'react';
import { ShieldAlert, RefreshCw, Filter, Search } from 'lucide-react';
import { api } from '../../api/client';
import { formatDateTime } from '../../utils/formatters';

export default function AuditLogsView() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterAction, setFilterAction] = useState('ALL');
  const [search, setSearch] = useState('');

  const loadLogs = async () => {
    try {
      const res = await api.admin.getAuditLogs(150);
      if (res.ok) {
        setLogs(res.data || []);
      }
    } catch (err) {
      console.error('Failed to load audit logs', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const actions = ['ALL', ...Array.from(new Set(logs.map(l => l.action).filter(Boolean)))];

  const filtered = logs.filter(l => {
    const matchesAction = filterAction === 'ALL' || l.action === filterAction;
    const matchesSearch = !search ||
      (l.user_id && String(l.user_id).includes(search)) ||
      (l.action && l.action.toLowerCase().includes(search.toLowerCase())) ||
      (l.ip_address && l.ip_address.includes(search));
    return matchesAction && matchesSearch;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--navy)' }}>
            Security & Compliance Audit Trail
          </h2>
          <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
            Append-only tamper-resistant record of logins, security events, and administrative mutations
          </span>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={loadLogs}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div className="card" style={{ padding: '0.75rem 1rem', display: 'flex', gap: '1rem', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: '0.75rem', flex: 1, maxWidth: '400px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={16} color="var(--muted)" style={{ position: 'absolute', left: '0.65rem', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Search user ID, action, or IP..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{
                width: '100%',
                padding: '0.45rem 0.65rem 0.45rem 2.2rem',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.85rem',
                outline: 'none'
              }}
            />
          </div>

          <select
            value={filterAction}
            onChange={e => setFilterAction(e.target.value)}
            style={{
              padding: '0.45rem 0.65rem',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.85rem',
              outline: 'none',
              background: 'var(--card)'
            }}
          >
            {actions.map(a => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </div>

        <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
          Showing <strong>{filtered.length}</strong> events
        </div>
      </div>

      <div className="card" style={{ padding: '0' }}>
        <div className="table-container" style={{ border: 'none' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Log ID</th>
                <th>Timestamp</th>
                <th>Action</th>
                <th>User ID</th>
                <th>IP Address</th>
                <th>Status</th>
                <th>Payload / Context</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2rem', color: 'var(--muted)' }}>
                    No matching audit log entries.
                  </td>
                </tr>
              ) : (
                filtered.map(l => {
                  const isFail = l.status === 'FAILED' || l.action?.includes('FAIL') || l.action?.includes('LOCKOUT');
                  return (
                    <tr key={l.id}>
                      <td style={{ fontSize: '0.8rem', color: 'var(--muted)', fontFamily: 'monospace' }}>
                        #{l.id}
                      </td>
                      <td style={{ fontSize: '0.8rem' }}>{formatDateTime(l.created_at)}</td>
                      <td>
                        <strong style={{ color: 'var(--navy)' }}>{l.action}</strong>
                      </td>
                      <td style={{ fontSize: '0.85rem' }}>{l.user_id ? `User #${l.user_id}` : 'System / Anonymous'}</td>
                      <td style={{ fontSize: '0.8rem', fontFamily: 'monospace' }}>{l.ip_address || '127.0.0.1'}</td>
                      <td>
                        <span className={`badge ${isFail ? 'badge-loss' : 'badge-gain'}`}>
                          {l.status || (isFail ? 'FLAGGED' : 'SUCCESS')}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.75rem', color: 'var(--muted)', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {typeof l.payload === 'object' ? JSON.stringify(l.payload) : (l.payload || '—')}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
