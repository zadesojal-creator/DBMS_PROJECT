import React, { useState, useEffect } from 'react';
import { PlusCircle, ArrowUpRight, ArrowDownRight, TrendingUp, RefreshCw, BarChart2, UserCheck, Shield } from 'lucide-react';
import { api } from '../../api/client';
import { formatINR, formatPct, formatQty, formatDateTime } from '../../utils/formatters';
import KpiTile from '../../components/KpiTile';
import DepositModal from '../../components/DepositModal';
import TradeTicketModal from '../../components/TradeTicketModal';
import StockChartModal from '../../components/StockChartModal';

export default function DashboardView() {
  const [summary, setSummary] = useState(null);
  const [holdings, setHoldings] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDepositModal, setShowDepositModal] = useState(false);
  const [selectedStockForTrade, setSelectedStockForTrade] = useState(null);
  const [selectedStockForChart, setSelectedStockForChart] = useState(null);

  const loadData = async () => {
    try {
      const [sumRes, holdRes, txRes] = await Promise.all([
        api.investor.getSummary(),
        api.investor.getHoldings(),
        api.investor.getTransactions(5)
      ]);
      if (sumRes.ok) setSummary(sumRes.data);
      if (holdRes.ok) setHoldings(holdRes.data || []);
      if (txRes.ok) setTransactions(txRes.data || []);
    } catch (err) {
      console.error('Failed to load investor dashboard data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Poll prices every 5 seconds to update live value
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !summary) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--muted)' }}>Loading financial dashboard...</div>;
  }

  const pnlPct = summary?.unrealized_pnl && summary?.holdings_market_value
    ? (summary.unrealized_pnl / (summary.holdings_market_value - summary.unrealized_pnl || 1)) * 100
    : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top Banner & Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--navy)' }}>Portfolio Overview</h2>
          <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
            Real-time valuation based on latest simulated exchange quotes
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn btn-secondary btn-sm" onClick={loadData} title="Refresh data">
            <RefreshCw size={14} /> Refresh
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => setShowDepositModal(true)}>
            <PlusCircle size={15} /> Add Virtual Cash
          </button>
        </div>
      </div>

      {/* KPI Tiles Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <KpiTile
          title="Portfolio Value"
          value={formatINR(summary?.portfolio_value || 0)}
          subtext="Cash + Holdings Market Value"
        />
        <KpiTile
          title="Available Cash"
          value={formatINR(summary?.available_cash || 0)}
          subtext="Unencumbered buying power"
        />
        <KpiTile
          title="Holdings Value"
          value={formatINR(summary?.holdings_market_value || 0)}
          subtext={`${holdings.length} Active Positions`}
        />
        <KpiTile
          title="Unrealised P&L"
          value={formatINR(summary?.unrealized_pnl || 0)}
          changePct={pnlPct}
          subtext="Based on current market prices"
        />
        <KpiTile
          title="Realised P&L"
          value={formatINR(summary?.realized_pnl || 0)}
          subtext="Net of trading brokerage fees"
        />
      </div>

      {/* Assigned Broker & Fee Policy Card */}
      <div className="card" style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: '#EFF6FF', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <UserCheck size={20} color="var(--primary)" />
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--muted)', letterSpacing: '0.05em' }}>
                Assigned Broker Relationship
              </div>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--navy)' }}>
                {summary?.assigned_broker ? (
                  <>
                    {summary.assigned_broker.broker_name} <span style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--muted)' }}>(Broker #{summary.assigned_broker.broker_id} &bull; {summary.assigned_broker.broker_email})</span>
                  </>
                ) : (
                  <span style={{ color: 'var(--muted)' }}>Direct Platform Investor (Self-Directed)</span>
                )}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Trading Brokerage Policy</div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--navy)' }}>
                0.10% per executed trade <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>(min ₹1.00)</span>
              </div>
            </div>
            <div style={{ height: '30px', width: '1px', background: '#CBD5E1' }} />
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Broker Attribution</div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--gain)' }}>
                40% Platform-Funded Commission
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Holdings Section */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)' }}>Current Holdings</h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>Weighted average cost basis with real-time mark-to-market</span>
          </div>
        </div>

        {holdings.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--muted)', fontSize: '0.9rem' }}>
            No open stock positions yet. Visit the Market Directory to buy your first shares.
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Symbol & Company</th>
                  <th className="numeric">Quantity</th>
                  <th className="numeric">Avg Cost</th>
                  <th className="numeric">Current Price</th>
                  <th className="numeric">Market Value</th>
                  <th className="numeric">Unrealised P&L</th>
                  <th className="numeric">Return %</th>
                  <th style={{ textAlign: 'center' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map(h => {
                  const mktVal = h.quantity * h.current_price;
                  const isProfit = h.unrealized_pnl >= 0;
                  return (
                    <tr key={h.stock_id}>
                      <td>
                        <strong style={{ color: 'var(--navy)' }}>{h.symbol}</strong>
                        <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{h.company_name}</div>
                      </td>
                      <td className="numeric">{formatQty(h.quantity)}</td>
                      <td className="numeric">{formatINR(h.average_buy_price)}</td>
                      <td className="numeric font-semibold">{formatINR(h.current_price)}</td>
                      <td className="numeric font-semibold">{formatINR(mktVal)}</td>
                      <td className={`numeric ${isProfit ? 'text-gain' : 'text-loss'}`} style={{ color: isProfit ? 'var(--gain)' : 'var(--loss)', fontWeight: 600 }}>
                        {formatINR(h.unrealized_pnl)}
                      </td>
                      <td className="numeric">
                        <span className={`badge ${isProfit ? 'badge-gain' : 'badge-loss'}`}>
                          {formatPct(h.return_pct)}
                        </span>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <div style={{ display: 'inline-flex', gap: '0.4rem' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '0.2rem 0.5rem' }}
                            onClick={() => setSelectedStockForChart(h)}
                            title="View Chart"
                          >
                            <BarChart2 size={13} /> Chart
                          </button>
                          <button
                            className="btn btn-danger btn-sm"
                            style={{ padding: '0.2rem 0.6rem' }}
                            onClick={() => setSelectedStockForTrade(h)}
                          >
                            Sell
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

      {/* Recent Transactions */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)' }}>Recent Executions</h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>Committed trades with full brokerage audit records</span>
          </div>
        </div>

        {transactions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--muted)', fontSize: '0.85rem' }}>
            No trades executed yet.
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th className="numeric">Quantity</th>
                  <th className="numeric">Price</th>
                  <th className="numeric">Gross</th>
                  <th className="numeric">Brokerage Fee</th>
                  <th className="numeric">Net Cash</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map(t => {
                  const isBuy = t.side === 'BUY';
                  return (
                    <tr key={t.transaction_id}>
                      <td style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>{formatDateTime(t.executed_at)}</td>
                      <td><strong>{t.symbol}</strong></td>
                      <td>
                        <span className={`badge ${isBuy ? 'badge-gain' : 'badge-loss'}`}>
                          {t.side}
                        </span>
                      </td>
                      <td className="numeric">{formatQty(t.quantity)}</td>
                      <td className="numeric">{formatINR(t.execution_price)}</td>
                      <td className="numeric">{formatINR(t.gross_amount)}</td>
                      <td className="numeric" style={{ color: 'var(--muted)' }}>{formatINR(t.brokerage_fee)}</td>
                      <td className="numeric" style={{ fontWeight: 600, color: isBuy ? 'var(--loss)' : 'var(--gain)' }}>
                        {isBuy ? `-${formatINR(t.net_amount)}` : `+${formatINR(t.net_amount)}`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modals */}
      {showDepositModal && (
        <DepositModal
          currentBalance={summary?.available_cash || 0}
          onClose={() => setShowDepositModal(false)}
          onDepositSuccess={loadData}
        />
      )}

      {selectedStockForTrade && (
        <TradeTicketModal
          stock={selectedStockForTrade}
          availableCash={summary?.available_cash || 0}
          currentHoldingQty={holdings.find(h => h.stock_id === (selectedStockForTrade.stock_id || selectedStockForTrade.id))?.quantity || 0}
          onClose={() => setSelectedStockForTrade(null)}
          onOrderExecuted={loadData}
        />
      )}

      {selectedStockForChart && (
        <StockChartModal
          stock={selectedStockForChart}
          onClose={() => setSelectedStockForChart(null)}
          onOpenTrade={(st) => setSelectedStockForTrade(st)}
        />
      )}
    </div>
  );
}
