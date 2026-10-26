import React, { useState, useEffect } from 'react';
import { Star, Bell, PlusCircle, Trash2, BarChart2, ShoppingCart, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';
import { api } from '../../api/client';
import { formatINR, formatPct, formatQty, formatDateTime } from '../../utils/formatters';
import StockChartModal from '../../components/StockChartModal';
import TradeTicketModal from '../../components/TradeTicketModal';

export default function WatchlistView({ allStocks = [] }) {
  const [watchlist, setWatchlist] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeAlertTab, setActiveAlertTab] = useState('ALL');

  // Modals state
  const [selectedStockForChart, setSelectedStockForChart] = useState(null);
  const [selectedStockForTrade, setSelectedStockForTrade] = useState(null);
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [prefilledAlertStock, setPrefilledAlertStock] = useState(null);

  // Form states for creating alert
  const [alertStockId, setAlertStockId] = useState('');
  const [alertTargetPrice, setAlertTargetPrice] = useState('');
  const [alertCondition, setAlertCondition] = useState('ABOVE');
  const [alertSubmitting, setAlertSubmitting] = useState(false);
  const [alertError, setAlertError] = useState('');

  // Quick add watchlist
  const [quickAddStockId, setQuickAddStockId] = useState('');

  const loadData = async () => {
    try {
      const [wlRes, alRes] = await Promise.all([
        api.investor.getWatchlist(),
        api.investor.getAlerts()
      ]);
      if (wlRes.ok) setWatchlist(wlRes.data || []);
      if (alRes.ok) setAlerts(alRes.data || []);
    } catch (err) {
      console.error('Error loading watchlist and alerts', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleRemoveWatchlist = async (stockId) => {
    try {
      const res = await api.investor.removeFromWatchlist(stockId);
      if (res.ok) {
        setWatchlist(prev => prev.filter(w => w.stock_id !== stockId));
      }
    } catch (err) {
      alert(`Failed to remove: ${err.message}`);
    }
  };

  const handleQuickAddWatchlist = async (e) => {
    e.preventDefault();
    if (!quickAddStockId) return;
    try {
      const res = await api.investor.addToWatchlist(parseInt(quickAddStockId, 10));
      if (res.ok) {
        setQuickAddStockId('');
        loadData();
      }
    } catch (err) {
      alert(`Failed to add stock: ${err.message}`);
    }
  };

  const handleOpenAlertModal = (stock = null) => {
    setPrefilledAlertStock(stock);
    if (stock) {
      setAlertStockId(String(stock.stock_id || stock.id));
      const curr = Number(stock.current_price ?? stock.price ?? 100);
      setAlertTargetPrice(String(Math.round(curr * 1.02 * 100) / 100));
    } else {
      setAlertStockId(allStocks[0]?.id ? String(allStocks[0].id) : '');
      setAlertTargetPrice('');
    }
    setAlertCondition('ABOVE');
    setAlertError('');
    setShowAlertModal(true);
  };

  const handleCreateAlert = async (e) => {
    e.preventDefault();
    setAlertError('');
    setAlertSubmitting(true);
    try {
      const res = await api.investor.createAlert({
        stock_id: parseInt(alertStockId, 10),
        target_price: parseFloat(alertTargetPrice),
        condition_type: alertCondition
      });
      if (res.ok) {
        setShowAlertModal(false);
        loadData();
      }
    } catch (err) {
      setAlertError(err.message || 'Failed to create price alert');
    } finally {
      setAlertSubmitting(false);
    }
  };

  const handleCancelAlert = async (alertId) => {
    try {
      const res = await api.investor.cancelAlert(alertId);
      if (res.ok) {
        loadData();
      }
    } catch (err) {
      alert(`Failed to cancel alert: ${err.message}`);
    }
  };

  const filteredAlerts = alerts.filter(a => {
    if (activeAlertTab === 'ACTIVE') return a.status === 'ACTIVE';
    if (activeAlertTab === 'TRIGGERED') return a.status === 'TRIGGERED';
    if (activeAlertTab === 'CANCELLED') return a.status === 'CANCELLED';
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--navy)' }}>
            Watchlist & Price Threshold Alerts
          </h2>
          <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
            Real-time equity monitoring and server-evaluated price triggers
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn btn-secondary btn-sm" onClick={loadData}>
            <RefreshCw size={14} /> Refresh
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => handleOpenAlertModal()}>
            <Bell size={14} /> New Price Alert
          </button>
        </div>
      </div>

      {/* Watchlist Card */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Star size={18} color="var(--amber)" fill="var(--amber)" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)' }}>
              My Watchlist ({watchlist.length})
            </h3>
          </div>

          {/* Quick Add Dropdown */}
          <form onSubmit={handleQuickAddWatchlist} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <select
              className="form-control"
              style={{ fontSize: '0.8rem', padding: '0.35rem 0.6rem', width: '220px' }}
              value={quickAddStockId}
              onChange={e => setQuickAddStockId(e.target.value)}
            >
              <option value="">+ Add stock to watchlist...</option>
              {allStocks.map(s => (
                <option key={s.id || s.stock_id} value={s.id || s.stock_id}>
                  {s.symbol} — {s.company_name}
                </option>
              ))}
            </select>
            <button type="submit" className="btn btn-secondary btn-sm" disabled={!quickAddStockId}>
              Add
            </button>
          </form>
        </div>

        {watchlist.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--muted)', fontSize: '0.9rem' }}>
            Your watchlist is empty. Select any stock from the dropdown above or click the star icon in the Market Directory to track stocks here.
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Symbol & Company</th>
                  <th>Sector</th>
                  <th className="numeric">Current Price</th>
                  <th className="numeric">Day Change</th>
                  <th className="numeric">Day High</th>
                  <th className="numeric">Day Low</th>
                  <th className="numeric">Volume</th>
                  <th style={{ textAlign: 'center' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {watchlist.map(w => {
                  const currPrice = Number(w.current_price || 0);
                  const change = Number(w.day_change || 0);
                  const changePct = Number(w.day_change_pct || 0);
                  const isUp = change >= 0;

                  return (
                    <tr key={w.stock_id}>
                      <td>
                        <strong style={{ color: 'var(--navy)' }}>{w.symbol}</strong>
                        <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{w.company_name}</div>
                      </td>
                      <td>
                        <span className="badge badge-secondary" style={{ fontSize: '0.75rem' }}>{w.sector}</span>
                      </td>
                      <td className="numeric font-semibold" style={{ fontSize: '0.95rem' }}>
                        {formatINR(currPrice)}
                      </td>
                      <td className={`numeric font-semibold ${isUp ? 'text-gain' : 'text-loss'}`} style={{ color: isUp ? 'var(--gain)' : 'var(--loss)' }}>
                        {isUp ? '+' : ''}{formatINR(change)} ({formatPct(changePct)})
                      </td>
                      <td className="numeric" style={{ color: 'var(--muted)' }}>{formatINR(w.day_high || currPrice)}</td>
                      <td className="numeric" style={{ color: 'var(--muted)' }}>{formatINR(w.day_low || currPrice)}</td>
                      <td className="numeric">{formatQty(w.volume || 0)}</td>
                      <td style={{ textAlign: 'center' }}>
                        <div style={{ display: 'inline-flex', gap: '0.35rem' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '0.2rem 0.5rem' }}
                            onClick={() => setSelectedStockForChart(w)}
                            title="Open Candlestick Chart"
                          >
                            <BarChart2 size={13} />
                          </button>
                          <button
                            className="btn btn-primary btn-sm"
                            style={{ padding: '0.2rem 0.5rem' }}
                            onClick={() => setSelectedStockForTrade(w)}
                            title="Trade Stock"
                          >
                            <ShoppingCart size={13} /> Trade
                          </button>
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '0.2rem 0.5rem' }}
                            onClick={() => handleOpenAlertModal(w)}
                            title="Set Price Alert"
                          >
                            <Bell size={13} color="var(--navy)" />
                          </button>
                          <button
                            className="btn btn-danger btn-sm"
                            style={{ padding: '0.2rem 0.45rem' }}
                            onClick={() => handleRemoveWatchlist(w.stock_id)}
                            title="Remove from Watchlist"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Price Alerts Card */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Bell size={18} color="var(--navy)" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)' }}>
              Configured Price Alerts
            </h3>
          </div>

          {/* Filter Pills */}
          <div style={{ display: 'flex', gap: '0.4rem' }}>
            {['ALL', 'ACTIVE', 'TRIGGERED', 'CANCELLED'].map(tab => (
              <button
                key={tab}
                className={`btn btn-sm ${activeAlertTab === tab ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
                onClick={() => setActiveAlertTab(tab)}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {filteredAlerts.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--muted)', fontSize: '0.85rem' }}>
            No price alerts found under the "{activeAlertTab}" filter.
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Security</th>
                  <th>Condition</th>
                  <th className="numeric">Target Price</th>
                  <th className="numeric">Current Price</th>
                  <th>Status</th>
                  <th>Created At</th>
                  <th>Triggered At</th>
                  <th style={{ textAlign: 'center' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredAlerts.map(a => {
                  const isTriggered = a.status === 'TRIGGERED';
                  const isActive = a.status === 'ACTIVE';
                  const isAbove = a.condition_type === 'ABOVE';

                  return (
                    <tr key={a.alert_id}>
                      <td>
                        <strong style={{ color: 'var(--navy)' }}>{a.symbol}</strong>
                        <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{a.company_name}</div>
                      </td>
                      <td>
                        <span style={{ fontWeight: 600, fontSize: '0.8rem', color: isAbove ? 'var(--gain)' : 'var(--loss)' }}>
                          {isAbove ? '>= Price Rises Above' : '<= Price Drops Below'}
                        </span>
                      </td>
                      <td className="numeric font-bold">{formatINR(a.target_price)}</td>
                      <td className="numeric font-semibold">{formatINR(a.current_price || 0)}</td>
                      <td>
                        {isTriggered && <span className="badge badge-gain">TRIGGERED</span>}
                        {isActive && <span className="badge badge-primary">ACTIVE</span>}
                        {a.status === 'CANCELLED' && <span className="badge badge-secondary">CANCELLED</span>}
                      </td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>{formatDateTime(a.created_at)}</td>
                      <td style={{ fontSize: '0.8rem', color: isTriggered ? 'var(--gain)' : 'var(--muted)' }}>
                        {a.triggered_at ? formatDateTime(a.triggered_at) : '—'}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        {isActive ? (
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                            onClick={() => handleCancelAlert(a.alert_id)}
                          >
                            Cancel
                          </button>
                        ) : (
                          <button
                            className="btn btn-danger btn-sm"
                            style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                            onClick={() => handleCancelAlert(a.alert_id)}
                            title="Delete"
                          >
                            <Trash2 size={12} />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Alert Modal */}
      {showAlertModal && (
        <div className="modal-backdrop">
          <div className="modal-card" style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)' }}>
                Create Price Threshold Alert
              </h3>
              <button className="btn-close" onClick={() => setShowAlertModal(false)}>&times;</button>
            </div>

            <form onSubmit={handleCreateAlert}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {alertError && (
                  <div style={{ background: '#FEE2E2', color: 'var(--loss)', padding: '0.6rem 0.8rem', borderRadius: 'var(--radius-sm)', fontSize: '0.85rem' }}>
                    {alertError}
                  </div>
                )}

                <div>
                  <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--navy)', marginBottom: '0.25rem', display: 'block' }}>
                    Select Equity
                  </label>
                  <select
                    className="form-control"
                    value={alertStockId}
                    onChange={e => {
                      setAlertStockId(e.target.value);
                      const found = allStocks.find(s => String(s.id || s.stock_id) === e.target.value);
                      if (found) {
                        const curr = Number(found.current_price ?? found.price ?? 100);
                        setAlertTargetPrice(String(Math.round(curr * 1.02 * 100) / 100));
                      }
                    }}
                    required
                  >
                    {allStocks.map(s => (
                      <option key={s.id || s.stock_id} value={s.id || s.stock_id}>
                        {s.symbol} — {s.company_name} (₹{Number(s.current_price ?? s.price ?? 0).toFixed(2)})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--navy)', marginBottom: '0.25rem', display: 'block' }}>
                    Alert Trigger Condition
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                    <button
                      type="button"
                      className={`btn ${alertCondition === 'ABOVE' ? 'btn-primary' : 'btn-secondary'}`}
                      style={{ fontSize: '0.85rem' }}
                      onClick={() => setAlertCondition('ABOVE')}
                    >
                      &gt;= Rises Above
                    </button>
                    <button
                      type="button"
                      className={`btn ${alertCondition === 'BELOW' ? 'btn-primary' : 'btn-secondary'}`}
                      style={{ fontSize: '0.85rem' }}
                      onClick={() => setAlertCondition('BELOW')}
                    >
                      &lt;= Drops Below
                    </button>
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--navy)', marginBottom: '0.25rem', display: 'block' }}>
                    Target Price (₹ INR)
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.05"
                    className="form-control"
                    placeholder="e.g. 2500.00"
                    value={alertTargetPrice}
                    onChange={e => setAlertTargetPrice(e.target.value)}
                    required
                  />
                  <span style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.25rem', display: 'block' }}>
                    Evaluated autonomously by the Python market simulator on each tick batch flush.
                  </span>
                </div>
              </div>

              <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.25rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowAlertModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={alertSubmitting}>
                  {alertSubmitting ? 'Creating...' : 'Set Alert'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Stock Chart Modal */}
      {selectedStockForChart && (
        <StockChartModal
          stock={selectedStockForChart}
          onClose={() => setSelectedStockForChart(null)}
          onOpenTrade={(st) => setSelectedStockForTrade(st)}
        />
      )}

      {/* Trade Modal */}
      {selectedStockForTrade && (
        <TradeTicketModal
          stock={selectedStockForTrade}
          availableCash={100000}
          onClose={() => setSelectedStockForTrade(null)}
          onOrderExecuted={loadData}
        />
      )}
    </div>
  );
}
