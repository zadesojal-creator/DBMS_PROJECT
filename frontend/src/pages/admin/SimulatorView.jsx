import React, { useState, useEffect } from 'react';
import { Sliders, Play, Pause, Zap, RefreshCw, CheckCircle, ShieldCheck } from 'lucide-react';
import { api } from '../../api/client';
import { formatQty, formatDateTime } from '../../utils/formatters';
import KpiTile from '../../components/KpiTile';

export default function SimulatorView() {
  const [status, setStatus] = useState(null);
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);

  const loadStatus = async () => {
    try {
      const [simRes, rulesRes] = await Promise.all([
        api.admin.getSimulatorStatus(),
        api.admin.getCommissionRules().catch(() => null)
      ]);
      if (simRes.ok) setStatus(simRes.data);
      if (rulesRes?.ok) setRules(rulesRes.data || []);
    } catch (err) {
      console.error('Failed to load simulator status', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleControl = async (action) => {
    setActing(true);
    try {
      const res = await api.admin.controlSimulator(action);
      if (res.ok) {
        loadStatus();
      }
    } catch (err) {
      alert(`Action failed: ${err.message}`);
    } finally {
      setActing(false);
    }
  };

  const isRunning = status?.status === 'RUNNING' || status?.status === 'ACTIVE';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--navy)' }}>
            Market Simulator Controls
          </h2>
          <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
            Autonomous APScheduler background worker with MySQL advisory lock coordination
          </span>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={loadStatus}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <KpiTile
          title="Worker State"
          value={status?.status || 'RUNNING'}
          subtext={`Freshness: ${status?.indicator || 'green'}`}
        />
        <KpiTile
          title="Completed Ticks"
          value={formatQty(status?.ticks_completed || 0)}
          subtext="Consecutive price updates"
        />
        <KpiTile
          title="Last Execution"
          value={status?.last_tick_at ? new Date(status.last_tick_at).toLocaleTimeString('en-IN') : '—'}
          subtext="Recorded timestamp"
        />
      </div>

      <div className="card">
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)', marginBottom: '0.75rem' }}>
          Simulation Actions
        </h3>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {isRunning ? (
            <button
              className="btn btn-danger"
              onClick={() => handleControl('pause')}
              disabled={acting}
            >
              <Pause size={16} /> Pause Simulation
            </button>
          ) : (
            <button
              className="btn btn-primary"
              onClick={() => handleControl('resume')}
              disabled={acting}
            >
              <Play size={16} /> Resume Simulation
            </button>
          )}

          <button
            className="btn btn-secondary"
            onClick={() => handleControl('tick')}
            disabled={acting}
          >
            <Zap size={16} color="var(--amber)" /> Force Single Price Tick
          </button>
        </div>
      </div>

      {/* Commission & Brokerage Rules Management */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)' }}>
              Platform Brokerage & Commission Policies
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
              Configured in Commission_Rules; enforced inside sp_execute_trade
            </span>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          {rules.length === 0 ? (
            <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>No active commission rules found.</div>
          ) : (
            rules.map(r => (
              <div key={r.id} style={{ border: '1px solid #E2E8F0', borderRadius: 'var(--radius-md)', padding: '1rem', background: '#F8FAFC' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <strong style={{ fontSize: '0.9rem', color: 'var(--navy)' }}>
                    {r.rule_type === 'INVESTOR_BROKERAGE' ? 'Investor Brokerage Fee' : 'Broker Commission Split'}
                  </strong>
                  <span className={`badge ${r.is_active ? 'badge-gain' : 'badge-secondary'}`}>
                    {r.is_active ? 'ACTIVE' : 'INACTIVE'}
                  </span>
                </div>
                <div style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--navy)', marginBottom: '0.25rem' }}>
                  {r.rate_pct.toFixed(2)}%
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
                  {r.rule_type === 'INVESTOR_BROKERAGE'
                    ? `Min Fee: ₹${r.min_fee.toFixed(2)} per trade`
                    : 'Platform-funded payout to assigned broker'}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.5rem' }}>
                  Effective: {r.effective_from || 'Genesis'}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)', marginBottom: '0.75rem' }}>
          Mathematics & Concurrency Guarantee
        </h3>
        <p style={{ fontSize: '0.875rem', color: 'var(--muted)', lineHeight: 1.6 }}>
          Prices are evolved via a discrete <strong>Ornstein-Uhlenbeck mean-reverting bounded random walk</strong>:
          <br />
          <code>S(t+1) = S(t) + θ (μ - S(t)) Δt + σ S(t) ε √Δt</code>
          <br />
          where <code>θ = 0.05</code> is reversion speed, <code>μ</code> is sector base price, and <code>σ = 0.015</code> is volatility. 
          To ensure strict single-worker execution across multiple Flask processes or gunicorn workers, 
          the engine acquires a MySQL server-side advisory lock (<code>SELECT GET_LOCK('stocktrade_simulator_lock', 0)</code>) before every tick.
        </p>
      </div>
    </div>
  );
}
