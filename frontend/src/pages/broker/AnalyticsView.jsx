import React, { useState, useEffect } from 'react';
import {
  PieChart,
  TrendingUp,
  DollarSign,
  Award,
  RefreshCw,
  Users,
  Activity,
  Percent,
  ShieldCheck,
  ArrowUpRight,
  ArrowDownRight,
  BarChart3,
  Calendar
} from 'lucide-react';
import { api } from '../../api/client';
import { formatINR, formatQty } from '../../utils/formatters';
import KpiTile from '../../components/KpiTile';

export default function AnalyticsView() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadAnalytics = async () => {
    try {
      const res = await api.broker.getAnalytics();
      if (res.ok) {
        setStats(res.data);
      }
    } catch (err) {
      console.error('Failed to load broker analytics', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

  const totalComm = stats?.total_commissions ?? stats?.total_commission ?? 0;
  const totalTrades = stats?.total_trades || 0;
  const investors = stats?.investor_commissions || [];
  const tradeAnalysis = stats?.trade_analysis || {};
  const topStocks = tradeAnalysis?.top_stocks || [];

  // Aggregates across all assigned clients
  const totalClientBalance = investors.reduce((acc, inv) => acc + (inv.virtual_balance || 0), 0);
  const totalClientTurnover = tradeAnalysis?.total_turnover || investors.reduce((acc, inv) => acc + (inv.total_volume || 0), 0);
  const buyTrades = tradeAnalysis?.buy_orders || 0;
  const sellTrades = tradeAnalysis?.sell_orders || 0;
  const buyTurnover = tradeAnalysis?.buy_turnover || 0;
  const sellTurnover = tradeAnalysis?.sell_turnover || 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
            <PieChart size={24} color="var(--teal)" />
            <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--navy)' }}>
              Commission & Trade Analysis Console
            </h2>
          </div>
          <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
            Real-time investor-wise commission attribution, client trade turnover, and order flow telemetry
          </span>
        </div>
        <button
          className="btn btn-secondary btn-sm"
          onClick={loadAnalytics}
          disabled={loading}
          style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
        >
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
          {loading ? 'Refreshing...' : 'Refresh Analytics'}
        </button>
      </div>

      {/* Primary KPI Tiles */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <KpiTile
          title="Total Commission Earned"
          value={formatINR(totalComm)}
          subtext="Platform-funded broker revenue"
        />
        <KpiTile
          title="Client Trading Turnover"
          value={formatINR(totalClientTurnover)}
          subtext="Gross volume across client orders"
        />
        <KpiTile
          title="Executed Client Trades"
          value={formatQty(totalTrades)}
          subtext={`${buyTrades} Buys • ${sellTrades} Sells`}
        />
        <KpiTile
          title="Managed Client Capital"
          value={formatINR(totalClientBalance)}
          subtext={`${investors.length} Assigned Investor Accounts`}
        />
      </div>

      {/* ========================================================================= */}
      {/* INVESTOR-WISE COMMISSION BREAKDOWN TABLE                                  */}
      {/* ========================================================================= */}
      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{
          padding: '1.25rem 1.5rem',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
          background: '#FAFAFA'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Users size={18} color="var(--navy)" />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)' }}>
                Investor-Wise Commission Breakdown
              </h3>
            </div>
            <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
              Breakdown of trade volumes, platform commissions generated, and contribution share per assigned investor
            </span>
          </div>

          <span className="badge badge-secondary" style={{ fontSize: '0.75rem' }}>
            {investors.length} Assigned Investors
          </span>
        </div>

        <div className="table-container" style={{ border: 'none' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Investor Client</th>
                <th>Status</th>
                <th className="numeric">Virtual Balance</th>
                <th className="numeric">Trades (Buy/Sell)</th>
                <th className="numeric">Trading Turnover</th>
                <th className="numeric">Commission Earned</th>
                <th style={{ width: '160px' }}>Contribution %</th>
                <th className="numeric">Avg Trade Size</th>
                <th>Last Activity</th>
              </tr>
            </thead>
            <tbody>
              {investors.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--muted)' }}>
                    No assigned investors found. Onboard client investors to begin tracking commissions.
                  </td>
                </tr>
              ) : (
                investors.map((inv) => {
                  const contribPct = Number(inv.contribution_pct || 0);
                  const isTopContributor = contribPct > 0 && contribPct >= 50;

                  return (
                    <tr key={inv.investor_id}>
                      <td>
                        <strong style={{ color: 'var(--navy)' }}>{inv.investor_name}</strong>
                        <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>
                          ID: #{inv.investor_id} &bull; {inv.investor_email}
                        </div>
                      </td>
                      <td>
                        <span className={`badge ${inv.investor_status === 'ACTIVE' ? 'badge-gain' : 'badge-neutral'}`} style={{ fontSize: '0.7rem' }}>
                          {inv.investor_status}
                        </span>
                      </td>
                      <td className="numeric font-semibold">
                        {formatINR(inv.virtual_balance)}
                      </td>
                      <td className="numeric">
                        <strong>{inv.total_trades}</strong>
                        <div style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>
                          <span style={{ color: 'var(--gain)', fontWeight: 600 }}>{inv.buy_trades}B</span> / <span style={{ color: 'var(--loss)', fontWeight: 600 }}>{inv.sell_trades}S</span>
                        </div>
                      </td>
                      <td className="numeric font-semibold">
                        {formatINR(inv.total_volume)}
                      </td>
                      <td className="numeric font-bold" style={{ color: inv.commission_generated > 0 ? 'var(--gain)' : 'var(--muted)' }}>
                        {formatINR(inv.commission_generated)}
                      </td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 600 }}>
                            <span style={{ color: isTopContributor ? 'var(--teal)' : 'var(--navy)' }}>
                              {contribPct.toFixed(1)}%
                            </span>
                          </div>
                          <div style={{ width: '100%', height: '6px', background: '#E2E8F0', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{
                              width: `${Math.min(contribPct, 100)}%`,
                              height: '100%',
                              background: contribPct > 0 ? 'var(--teal)' : '#CBD5E1',
                              borderRadius: '3px',
                              transition: 'width 0.3s ease'
                            }} />
                          </div>
                        </div>
                      </td>
                      <td className="numeric" style={{ fontSize: '0.8rem' }}>
                        {inv.total_trades > 0 ? formatINR(inv.avg_trade_size) : '—'}
                      </td>
                      <td style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>
                        {inv.last_activity || inv.assigned_at || '—'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
            {investors.length > 0 && (
              <tfoot>
                <tr style={{ background: '#F8FAFC', fontWeight: 700, borderTop: '2px solid var(--border)' }}>
                  <td>Total / Combined</td>
                  <td>—</td>
                  <td className="numeric">{formatINR(totalClientBalance)}</td>
                  <td className="numeric">{totalTrades}</td>
                  <td className="numeric">{formatINR(totalClientTurnover)}</td>
                  <td className="numeric" style={{ color: 'var(--gain)' }}>{formatINR(totalComm)}</td>
                  <td>100.0%</td>
                  <td className="numeric">
                    {totalTrades > 0 ? formatINR(totalClientTurnover / totalTrades) : '—'}
                  </td>
                  <td>—</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* TRADE ACTIVITY & CLIENT EQUITY ANALYSIS                                  */}
      {/* ========================================================================= */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.25rem' }}>
        {/* Card 1: Order Flow & Side Distribution */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.85rem' }}>
            <Activity size={18} color="var(--teal)" />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--navy)' }}>
              Client Order Flow & Side Distribution
            </h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Split Bar */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                <span style={{ color: 'var(--gain)' }}>BUY Orders: {buyTrades} ({totalTrades > 0 ? ((buyTrades / totalTrades) * 100).toFixed(0) : 0}%)</span>
                <span style={{ color: 'var(--loss)' }}>SELL Orders: {sellTrades} ({totalTrades > 0 ? ((sellTrades / totalTrades) * 100).toFixed(0) : 0}%)</span>
              </div>
              <div style={{ display: 'flex', height: '10px', borderRadius: '5px', overflow: 'hidden', background: '#E2E8F0' }}>
                <div style={{ width: `${totalTrades > 0 ? (buyTrades / totalTrades) * 100 : 50}%`, background: 'var(--gain)' }} />
                <div style={{ width: `${totalTrades > 0 ? (sellTrades / totalTrades) * 100 : 50}%`, background: 'var(--loss)' }} />
              </div>
            </div>

            {/* Metrics Breakdown */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div style={{ background: '#F0FDF4', border: '1px solid #DCFCE7', borderRadius: 'var(--radius-md)', padding: '0.85rem' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#15803D', textTransform: 'uppercase', marginBottom: '0.2rem' }}>
                  Buy Turnover & Commissions
                </div>
                <div className="num font-bold" style={{ fontSize: '1.1rem', color: '#15803D' }}>
                  {formatINR(buyTurnover)}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#166534', marginTop: '0.2rem' }}>
                  Broker Comm: <strong>{formatINR(tradeAnalysis?.buy_commission || 0)}</strong>
                </div>
              </div>

              <div style={{ background: '#FEF2F2', border: '1px solid #FEE2E2', borderRadius: 'var(--radius-md)', padding: '0.85rem' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#B91C1C', textTransform: 'uppercase', marginBottom: '0.2rem' }}>
                  Sell Turnover & Commissions
                </div>
                <div className="num font-bold" style={{ fontSize: '1.1rem', color: '#B91C1C' }}>
                  {formatINR(sellTurnover)}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#991B1B', marginTop: '0.2rem' }}>
                  Broker Comm: <strong>{formatINR(tradeAnalysis?.sell_commission || 0)}</strong>
                </div>
              </div>
            </div>

            <div style={{ fontSize: '0.8rem', color: 'var(--muted)', background: '#F8FAFC', padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-sm)' }}>
              Brokerage rule is applied symmetrically to both executed Buys and Sells at <strong>0.10% gross</strong>, with <strong>40% attributed</strong> to the broker.
            </div>
          </div>
        </div>

        {/* Card 2: Top Traded Equities among Managed Clients */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.85rem' }}>
            <BarChart3 size={18} color="var(--primary)" />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--navy)' }}>
              Top Traded Securities by Clients
            </h3>
          </div>

          {topStocks.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--muted)', fontSize: '0.85rem' }}>
              No client trades recorded yet.
            </div>
          ) : (
            <div className="table-container" style={{ border: 'none' }}>
              <table className="data-table" style={{ fontSize: '0.8rem' }}>
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th className="numeric">Orders</th>
                    <th className="numeric">Quantity</th>
                    <th className="numeric">Total Turnover</th>
                    <th className="numeric">Comm. Earned</th>
                  </tr>
                </thead>
                <tbody>
                  {topStocks.map((stk) => (
                    <tr key={stk.symbol}>
                      <td>
                        <strong style={{ color: 'var(--navy)' }}>{stk.symbol}</strong>
                        <div style={{ fontSize: '0.7rem', color: 'var(--muted)', maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {stk.company_name}
                        </div>
                      </td>
                      <td className="numeric font-semibold">{stk.total_orders}</td>
                      <td className="numeric">{formatQty(stk.total_quantity)}</td>
                      <td className="numeric font-semibold">{formatINR(stk.total_turnover)}</td>
                      <td className="numeric font-bold" style={{ color: 'var(--gain)' }}>
                        {formatINR(stk.commission_generated)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Policy & Tenancy Audit Card */}
      <div className="card" style={{ background: '#F8FAFC', borderLeft: '4px solid var(--teal)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
          <ShieldCheck size={18} color="var(--teal)" />
          <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--navy)' }}>
            Regulatory Accounting & Platform-Funded Broker Policy
          </h4>
        </div>
        <p style={{ fontSize: '0.825rem', color: 'var(--muted)', lineHeight: 1.6, margin: 0 }}>
          Under the StockTrade regulatory model, broker commissions are <strong>platform-funded</strong> and 
          do not add any additional charges or spreads to your assigned investors. When an assigned investor executes a trade, 
          the system applies the prevailing <code>BROKER_COMMISSION</code> rule (40%) to the collected trading brokerage, 
          instantly creating an immutable audit record in the <code>Commissions</code> database table with verified foreign key references 
          to the underlying trade execution. All analytics displayed above are strictly isolated to your assigned client portfolio.
        </p>
      </div>
    </div>
  );
}
