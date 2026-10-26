import React, { useState, useEffect } from 'react';
import { Building2, Plus, Trash2, Search, RefreshCw, X, AlertCircle } from 'lucide-react';
import { api } from '../../api/client';
import { formatINR } from '../../utils/formatters';

export default function CompaniesView() {
  const [stocks, setStocks] = useState([]);
  const [search, setSearch] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newCompany, setNewCompany] = useState({
    symbol: '',
    company_name: '',
    sector: 'Technology',
    base_price: 500.00
  });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const loadCompanies = async () => {
    try {
      const res = await api.admin.getCompanies();
      if (res.ok) {
        setStocks(res.data || []);
      }
    } catch (err) {
      console.error('Failed to load companies', err);
    }
  };

  useEffect(() => {
    loadCompanies();
  }, []);

  const handleAddCompany = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await api.admin.createCompany({
        ...newCompany,
        base_price: parseFloat(newCompany.base_price)
      });
      if (res.ok) {
        setShowAddModal(false);
        setNewCompany({ symbol: '', company_name: '', sector: 'Technology', base_price: 500.00 });
        loadCompanies();
      } else {
        setError(res.error?.message || 'Creation failed');
      }
    } catch (err) {
      setError(err.message || 'Creation failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (stockId, symbol) => {
    if (!window.confirm(`Attempt hard delete on ${symbol}? System will block if financial orders exist.`)) return;
    try {
      const res = await api.admin.deleteCompany(stockId);
      if (res.ok) {
        loadCompanies();
      } else {
        alert(res.error?.message || 'Delete blocked by safety constraint');
      }
    } catch (err) {
      alert(`Delete rejected: ${err.message}`);
    }
  };

  const filtered = stocks.filter(s =>
    s.symbol.toLowerCase().includes(search.toLowerCase()) ||
    s.company_name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--navy)' }}>
            Listed Companies & Securities Directory
          </h2>
          <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
            Manage equity symbols, base valuations, and sector classifications
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn btn-secondary btn-sm" onClick={loadCompanies}>
            <RefreshCw size={14} /> Refresh
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => setShowAddModal(true)}>
            <Plus size={15} /> Add Security
          </button>
        </div>
      </div>

      <div className="card" style={{ padding: '0.75rem 1rem' }}>
        <div style={{ position: 'relative', maxWidth: '360px' }}>
          <Search size={16} color="var(--muted)" style={{ position: 'absolute', left: '0.65rem', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            placeholder="Search symbol or name..."
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
      </div>

      <div className="card" style={{ padding: '0' }}>
        <div className="table-container" style={{ border: 'none' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Symbol</th>
                <th>Company Name</th>
                <th>Sector</th>
                <th className="numeric">Current Price</th>
                <th style={{ textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(s => (
                <tr key={s.id || s.stock_id}>
                  <td style={{ fontSize: '0.8rem', color: 'var(--muted)', fontFamily: 'monospace' }}>
                    #{s.id || s.stock_id}
                  </td>
                  <td><strong style={{ color: 'var(--navy)' }}>{s.symbol}</strong></td>
                  <td>{s.company_name}</td>
                  <td><span className="badge badge-neutral">{s.sector}</span></td>
                  <td className="numeric font-bold">{formatINR(s.current_price || s.base_price)}</td>
                  <td style={{ textAlign: 'center' }}>
                    <button
                      className="btn btn-danger btn-sm"
                      style={{ padding: '0.2rem 0.5rem' }}
                      onClick={() => handleDelete(s.id || s.stock_id, s.symbol)}
                      title="Guarded Hard Delete"
                    >
                      <Trash2 size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Company Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" style={{ maxWidth: '440px' }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1.25rem', borderBottom: '1px solid var(--border)' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)' }}>List New Security</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowAddModal(false)}><X size={16} /></button>
            </div>
            <form onSubmit={handleAddCompany} style={{ padding: '1.25rem' }}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--navy)', marginBottom: '0.3rem' }}>Symbol</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. ZOMATO"
                  value={newCompany.symbol}
                  onChange={e => setNewCompany({ ...newCompany, symbol: e.target.value.toUpperCase() })}
                  style={{ width: '100%', padding: '0.55rem 0.75rem', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)' }}
                />
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--navy)', marginBottom: '0.3rem' }}>Company Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Zomato Limited"
                  value={newCompany.company_name}
                  onChange={e => setNewCompany({ ...newCompany, company_name: e.target.value })}
                  style={{ width: '100%', padding: '0.55rem 0.75rem', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)' }}
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--navy)', marginBottom: '0.3rem' }}>Sector</label>
                  <input
                    type="text"
                    required
                    value={newCompany.sector}
                    onChange={e => setNewCompany({ ...newCompany, sector: e.target.value })}
                    style={{ width: '100%', padding: '0.55rem 0.75rem', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--navy)', marginBottom: '0.3rem' }}>Base Price (₹)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="1"
                    required
                    value={newCompany.base_price}
                    onChange={e => setNewCompany({ ...newCompany, base_price: e.target.value })}
                    style={{ width: '100%', padding: '0.55rem 0.75rem', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)' }}
                  />
                </div>
              </div>

              {error && (
                <div style={{ color: 'var(--loss)', fontSize: '0.8rem', marginBottom: '1rem', background: 'var(--loss-bg)', padding: '0.5rem', borderRadius: 'var(--radius-sm)' }}>
                  {error}
                </div>
              )}

              <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '0.75rem' }} disabled={submitting}>
                {submitting ? 'Registering...' : 'Add Security to Market'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
