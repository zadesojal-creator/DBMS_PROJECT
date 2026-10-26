import React, { useState, useEffect } from 'react';
import { LayoutDashboard, Users, Building2, TrendingUp, DollarSign, RefreshCw } from 'lucide-react';
import { api } from '../../api/client';
import { formatINR, formatQty } from '../../utils/formatters';
import KpiTile from '../../components/KpiTile';

export default function OverviewView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const res = await api.admin.getOverview();
      if (res.ok) {
        setData(res.data);
      }
    } catch (err) {
      console.error('Failed to load admin overview', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--navy)' }}>
            System Administration Overview
          </h2>
          <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
            High-level platform health, user accounts, and market depth
          </span>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={loadData}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <KpiTile
          title="Total User Accounts"
          value={formatQty(data?.total_users || 0)}
          subtext="Admins, Brokers, and Investors"
        />
        <KpiTile
          title="Listed Equities"
          value={formatQty(data?.total_stocks || 100)}
          subtext="Across 14 Industry Sectors"
        />
        <KpiTile
          title="System Trades"
          value={formatQty(data?.total_orders || 0)}
          subtext="Executed market orders"
        />
        <KpiTile
          title="Virtual Circulating Cash"
          value={formatINR(data?.total_capital || 0)}
          subtext="Sum of all investor accounts"
        />
      </div>

      <div className="card">
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)', marginBottom: '0.75rem' }}>
          Database Architecture & Storage Summary
        </h3>
        <p style={{ fontSize: '0.875rem', color: 'var(--muted)', lineHeight: 1.6 }}>
          StockTrade runs on MySQL 8 with an InnoDB engine and <code>utf8mb4</code> character set. 
          All financial calculations are performed in <code>DECIMAL(15,2)</code> and <code>DECIMAL(12,4)</code> with zero floating-point drift. 
          Trade execution is isolated under <code>READ COMMITTED</code> transactions with explicit row locks in a fixed order (Account &rarr; Holding &rarr; Current_Prices) to prevent deadlocks and enforce double reconciliation invariants.
        </p>
      </div>
    </div>
  );
}
