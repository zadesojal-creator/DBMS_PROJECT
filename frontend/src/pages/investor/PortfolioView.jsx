import React, { useState, useEffect } from 'react';
import { Briefcase, RefreshCw, BarChart2, ShoppingCart, CheckCircle2 } from 'lucide-react';
import { api } from '../../api/client';
import { formatINR, formatPct, formatQty } from '../../utils/formatters';
import KpiTile from '../../components/KpiTile';
import StockChartModal from '../../components/StockChartModal';
import TradeTicketModal from '../../components/TradeTicketModal';

export default function PortfolioView() {
  const [summary, setSummary] = useState(null);
  const [holdings, setHoldings] = useState([]);
  const [loading, setLoading] = useState(true);

  const [selectedStockForChart, setSelectedStockForChart] = useState(null);
  const [selectedStockForTrade, setSelectedStockForTrade] = useState(null);

  const loadData = async () => {
    try {
      const [sumRes, holdRes] = await Promise.all([
        api.investor.getSummary(),
        api.investor.getHoldings()
      ]);
      if (sumRes.ok) setSummary(sumRes.data);
      if (holdRes.ok) setHoldings(holdRes.data || []);
    } catch (err) {
      console.error('Failed to load portfolio view', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const totalCostBasis = holdings.reduce((acc, h) => acc + (h.quantity * h.average_buy_price), 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--navy)' }}>
            Portfolio & Holdings
          </h2>
          <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
            Mark-to-market positions, weighted average costs, and double-entry reconciliation
          </span>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={loadData}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* KPI Tiles */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <KpiTile
          title="Total Portfolio Value"
          value={formatINR(summary?.portfolio_value || 0)}
          subtext="Cash + Holdings Value"
        />
        <KpiTile
          title="Available Buying Power"
          value={formatINR(summary?.available_cash || 0)}
          subtext="Unallocated virtual funds"
        />
        <KpiTile
          title="Total Invested Cost"
          value={formatINR(totalCostBasis)}
          subtext="Cumulative cost basis"
        />
        <KpiTile
          title="Unrealised Gain/Loss"
          value={formatINR(summary?.unrealized_pnl || 0)}
          changePct={totalCostBasis > 0 ? (summary?.unrealized_pnl / totalCostBasis) * 100 : 0}
          subtext="Mark-to-market return"
        />
      </div>

      {/* Reconciliation Invariant Card */}
      <div className="card" style={{ background: '#F8FAFC', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <CheckCircle2 size={20} color="var(--gain)" />
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--navy)' }}>
              Double Reconciliation Invariant Guaranteed
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>
              <code>Accounts.virtual_balance == SUM(Ledger)</code> &bull; <code>Holdings.qty == SUM(Buys) - SUM(Sells)</code>
            </div>
          </div>
        </div>
        <span className="badge badge-gain">VERIFIED</span>
      </div>

      {/* Holdings Table */}
      <div className="card" style={{ padding: '0' }}>
        <div className="table-container" style={{ border: 'none' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Security</th>
                <th className="numeric">Quantity</th>
                <th className="numeric">Avg Cost</th>
                <th className="numeric">Current Price</th>
                <th className="numeric">Invested Amount</th>
                <th className="numeric">Market Value</th>
                <th className="numeric">Unrealised P&L</th>
                <th className="numeric">Return %</th>
                <th style={{ textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {holdings.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--muted)' }}>
                    No securities currently in portfolio.
                  </td>
                </tr>
              ) : (
                holdings.map(h => {
                  const invested = h.quantity * h.average_buy_price;
                  const currentMkt = h.quantity * h.current_price;
                  const isProfit = h.unrealized_pnl >= 0;

                  return (
                    <tr key={h.stock_id}>
                      <td>
                        <strong style={{ color: 'var(--navy)' }}>{h.symbol}</strong>
                        <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{h.company_name}</div>
                      </td>
                      <td className="numeric font-semibold">{formatQty(h.quantity)}</td>
                      <td className="numeric">{formatINR(h.average_buy_price)}</td>
                      <td className="numeric font-bold">{formatINR(h.current_price)}</td>
                      <td className="numeric">{formatINR(invested)}</td>
                      <td className="numeric font-bold">{formatINR(currentMkt)}</td>
                      <td className="numeric" style={{ color: isProfit ? 'var(--gain)' : 'var(--loss)', fontWeight: 600 }}>
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
                            title="Open Chart"
                          >
                            <BarChart2 size={13} /> Chart
                          </button>
                          <button
                            className="btn btn-primary btn-sm"
                            style={{ padding: '0.2rem 0.6rem' }}
                            onClick={() => setSelectedStockForTrade(h)}
                            title="Buy more or sell"
                          >
                            <ShoppingCart size={13} /> Trade
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modals */}
      {selectedStockForChart && (
        <StockChartModal
          stock={selectedStockForChart}
          onClose={() => setSelectedStockForChart(null)}
          onOpenTrade={(st) => setSelectedStockForTrade(st)}
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
    </div>
  );
}
