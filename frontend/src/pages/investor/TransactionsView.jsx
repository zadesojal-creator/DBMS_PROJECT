import React, { useState, useEffect } from 'react';
import { Download, RefreshCw, FileText } from 'lucide-react';
import { api } from '../../api/client';
import { formatINR, formatQty, formatDateTime } from '../../utils/formatters';

export default function TransactionsView() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadTransactions = async () => {
    try {
      const res = await api.investor.getTransactions(100);
      if (res.ok) {
        setTransactions(res.data || []);
      }
    } catch (err) {
      console.error('Failed to load transactions', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTransactions();
  }, []);

  const handleDownloadCsv = () => {
    window.location.href = '/api/v1/reports/transactions-csv';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--navy)' }}>
            Transaction History & Audit Ledger
          </h2>
          <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
            Immutable record of all executed trades and cash balance movements
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn btn-secondary btn-sm" onClick={loadTransactions}>
            <RefreshCw size={14} /> Refresh
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleDownloadCsv}>
            <Download size={14} /> Export CSV
          </button>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="card" style={{ padding: '0' }}>
        <div className="table-container" style={{ border: 'none' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Tx ID</th>
                <th>Timestamp</th>
                <th>Symbol & Side</th>
                <th className="numeric">Quantity</th>
                <th className="numeric">Execution Price</th>
                <th className="numeric">Gross Amount</th>
                <th className="numeric">Brokerage Fee</th>
                <th className="numeric">Net Cash</th>
              </tr>
            </thead>
            <tbody>
              {transactions.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '2rem', color: 'var(--muted)' }}>
                    No transactions recorded yet.
                  </td>
                </tr>
              ) : (
                transactions.map(t => {
                  const isBuy = t.side === 'BUY';
                  return (
                    <tr key={t.transaction_id}>
                      <td style={{ fontSize: '0.8rem', color: 'var(--muted)', fontFamily: 'monospace' }}>
                        #{t.transaction_id}
                      </td>
                      <td style={{ fontSize: '0.8rem' }}>{formatDateTime(t.executed_at)}</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className={`badge ${isBuy ? 'badge-gain' : 'badge-loss'}`}>
                            {t.side}
                          </span>
                          <strong style={{ color: 'var(--navy)' }}>{t.symbol}</strong>
                        </div>
                      </td>
                      <td className="numeric">{formatQty(t.quantity)}</td>
                      <td className="numeric">{formatINR(t.execution_price)}</td>
                      <td className="numeric">{formatINR(t.gross_amount)}</td>
                      <td className="numeric" style={{ color: 'var(--muted)' }}>{formatINR(t.brokerage_fee)}</td>
                      <td className="numeric font-bold" style={{ color: isBuy ? 'var(--loss)' : 'var(--gain)' }}>
                        {isBuy ? `-${formatINR(t.net_amount)}` : `+${formatINR(t.net_amount)}`}
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
