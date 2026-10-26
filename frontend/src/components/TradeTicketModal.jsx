import React, { useState } from 'react';
import { X, AlertCircle, CheckCircle2, ArrowRight } from 'lucide-react';
import { api } from '../api/client';
import { formatINR, formatPrice } from '../utils/formatters';

export default function TradeTicketModal({ stock, availableCash, currentHoldingQty, onClose, onOrderExecuted }) {
  const [side, setSide] = useState('BUY');
  const [quantity, setQuantity] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [confirmStep, setConfirmStep] = useState(false);
  const [error, setError] = useState(null);
  const [successData, setSuccessData] = useState(null);

  if (!stock) return null;

  const currentPrice = Number(stock.current_price ?? stock.price ?? 0);
  const qty = parseInt(quantity, 10) || 0;
  const tradeValue = qty * currentPrice;
  // Brokerage rule: max(1.00, 0.10% of trade_value)
  const estimatedBrokerage = Math.max(1.0, tradeValue * 0.001);
  const netEstimatedTotal = side === 'BUY' ? (tradeValue + estimatedBrokerage) : (tradeValue - estimatedBrokerage);

  // Validation
  let validationError = null;
  if (qty <= 0) {
    validationError = 'Quantity must be at least 1 share';
  } else if (side === 'BUY' && netEstimatedTotal > availableCash) {
    validationError = `Insufficient funds. Need ${formatINR(netEstimatedTotal)}, have ${formatINR(availableCash)}`;
  } else if (side === 'SELL' && qty > (currentHoldingQty || 0)) {
    validationError = `Insufficient shares. You hold ${currentHoldingQty || 0} shares, attempting to sell ${qty}`;
  }

  const handleExecute = async () => {
    setError(null);
    setSubmitting(true);
    const idempotencyKey = `req_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

    try {
      const res = await api.investor.executeOrder({
        stock_id: stock.stock_id || stock.id,
        side,
        quantity: qty,
        idempotency_key: idempotencyKey,
        quoted_price: currentPrice
      });

      if (res.ok) {
        setSuccessData(res.data);
        if (onOrderExecuted) onOrderExecuted();
      } else {
        setError(res.error?.message || 'Order failed');
      }
    } catch (err) {
      if (err.status === 409) {
        setError('Price moved significantly since quote. Please review updated estimate and confirm again.');
      } else {
        setError(err.message || 'Trade execution failed');
      }
      setConfirmStep(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: '480px' }} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1.25rem', borderBottom: '1px solid var(--border)' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)' }}>
              Trade Ticket: {stock.symbol}
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
              Market Order · Live Execution
            </span>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={onClose} style={{ padding: '0.35rem' }}>
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '1.25rem' }}>
          {successData ? (
            !successData.execution_price || successData.gross_amount === undefined || successData.net_amount === undefined ? (
              <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
                <AlertCircle size={48} color="var(--loss)" style={{ margin: '0 auto 1rem' }} />
                <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--loss)', marginBottom: '0.5rem' }}>
                  Execution Response Data Error
                </h4>
                <p style={{ fontSize: '0.85rem', color: 'var(--muted)', marginBottom: '1.5rem' }}>
                  The trade record was missing required financial details from the server.
                </p>
                <button className="btn btn-secondary" style={{ width: '100%' }} onClick={onClose}>
                  Close
                </button>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
                <CheckCircle2 size={48} color="var(--gain)" style={{ margin: '0 auto 1rem' }} />
                <h4 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--gain)', marginBottom: '0.5rem' }}>
                  Order Executed Successfully!
                </h4>
                <p style={{ fontSize: '0.875rem', color: 'var(--muted)', marginBottom: '1.5rem' }}>
                  {side} {successData.executed_quantity || successData.quantity} shares of {stock.symbol} at {formatINR(successData.execution_price)}
                </p>
                <div className="card" style={{ background: '#F8FAFC', textAlign: 'left', marginBottom: '1.5rem', fontSize: '0.825rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                    <span>Gross Value:</span>
                    <strong className="num">{formatINR(successData.gross_amount ?? successData.gross_value)}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                    <span>Brokerage Fee:</span>
                    <strong className="num">{formatINR(successData.brokerage_fee ?? successData.brokerage)}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border)', paddingTop: '0.35rem' }}>
                    <span>{side === 'BUY' ? 'Total Cash Debit:' : 'Net Cash Credit:'}</span>
                    <strong className="num" style={{ color: side === 'BUY' ? 'var(--loss)' : 'var(--gain)' }}>
                      {formatINR(successData.net_amount)}
                    </strong>
                  </div>
                </div>
                <button className="btn btn-primary" style={{ width: '100%' }} onClick={onClose}>
                  Done
                </button>
              </div>
            )
          ) : confirmStep ? (
            <div>
              <div style={{ background: '#FEF3C7', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '1rem' }}>
                <AlertCircle size={20} color="var(--amber)" />
                <span style={{ fontSize: '0.85rem', color: '#92400E', fontWeight: 500 }}>
                  Confirm your simulated order before submission.
                </span>
              </div>

              <div className="card" style={{ background: '#F8FAFC', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span>Side & Stock:</span>
                  <strong>{side} {stock.symbol}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span>Quantity:</span>
                  <strong className="num">{qty}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span>Est. Market Price:</span>
                  <strong className="num">{formatPrice(currentPrice)}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span>Brokerage (0.10% min ₹1):</span>
                  <strong className="num">{formatINR(estimatedBrokerage)}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border)', paddingTop: '0.5rem', fontSize: '0.95rem' }}>
                  <strong>{side === 'BUY' ? 'Total Cost:' : 'Net Proceeds:'}</strong>
                  <strong className="num" style={{ color: side === 'BUY' ? 'var(--loss)' : 'var(--gain)' }}>
                    {formatINR(netEstimatedTotal)}
                  </strong>
                </div>
              </div>

              {error && (
                <div style={{ color: 'var(--loss)', fontSize: '0.85rem', marginBottom: '1rem', background: 'var(--loss-bg)', padding: '0.6rem', borderRadius: 'var(--radius-sm)' }}>
                  {error}
                </div>
              )}

              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setConfirmStep(false)} disabled={submitting}>
                  Back
                </button>
                <button className={`btn ${side === 'BUY' ? 'btn-primary' : 'btn-danger'}`} style={{ flex: 1 }} onClick={handleExecute} disabled={submitting}>
                  {submitting ? 'Executing...' : `Confirm ${side}`}
                </button>
              </div>
            </div>
          ) : (
            <div>
              {/* Buy / Sell Toggle */}
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
                <button
                  type="button"
                  className={`btn ${side === 'BUY' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ flex: 1, padding: '0.6rem' }}
                  onClick={() => setSide('BUY')}
                >
                  BUY
                </button>
                <button
                  type="button"
                  className={`btn ${side === 'SELL' ? 'btn-danger' : 'btn-secondary'}`}
                  style={{ flex: 1, padding: '0.6rem' }}
                  onClick={() => setSide('SELL')}
                >
                  SELL
                </button>
              </div>

              {/* Stock Price & Available Context */}
              <div style={{ background: '#F8FAFC', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', fontSize: '0.85rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                  <span style={{ color: 'var(--muted)' }}>Current Price:</span>
                  <span className="num" style={{ fontWeight: 600 }}>{formatPrice(currentPrice)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                  <span style={{ color: 'var(--muted)' }}>Available Cash:</span>
                  <span className="num" style={{ fontWeight: 600 }}>{formatINR(availableCash)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--muted)' }}>Current Holdings:</span>
                  <span className="num" style={{ fontWeight: 600 }}>{currentHoldingQty || 0} shares</span>
                </div>
              </div>

              {/* Quantity Input */}
              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--navy)', marginBottom: '0.4rem' }}>
                  Quantity (Shares)
                </label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={quantity}
                  onChange={e => setQuantity(e.target.value)}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', fontSize: '1rem', fontVariantNumeric: 'tabular-nums' }}
                />
              </div>

              {/* Breakdown */}
              <div className="card" style={{ background: '#F8FAFC', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                  <span style={{ color: 'var(--muted)' }}>Trade Value:</span>
                  <span className="num">{formatINR(tradeValue)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                  <span style={{ color: 'var(--muted)' }}>Brokerage (0.10%, min ₹1):</span>
                  <span className="num">{formatINR(estimatedBrokerage)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border)', paddingTop: '0.4rem', fontWeight: 600 }}>
                  <span>{side === 'BUY' ? 'Estimated Total Payable:' : 'Estimated Net Proceeds:'}</span>
                  <span className="num" style={{ color: side === 'BUY' ? 'var(--navy)' : 'var(--gain)', fontSize: '1rem' }}>
                    {formatINR(netEstimatedTotal)}
                  </span>
                </div>
              </div>

              {validationError && (
                <div style={{ color: 'var(--loss)', fontSize: '0.8rem', marginBottom: '1rem', background: 'var(--loss-bg)', padding: '0.5rem', borderRadius: 'var(--radius-sm)' }}>
                  {validationError}
                </div>
              )}

              {error && (
                <div style={{ color: 'var(--loss)', fontSize: '0.8rem', marginBottom: '1rem', background: 'var(--loss-bg)', padding: '0.5rem', borderRadius: 'var(--radius-sm)' }}>
                  {error}
                </div>
              )}

              <button
                className={`btn ${side === 'BUY' ? 'btn-primary' : 'btn-danger'}`}
                style={{ width: '100%', padding: '0.75rem' }}
                disabled={Boolean(validationError)}
                onClick={() => setConfirmStep(true)}
              >
                Review {side} Order <ArrowRight size={16} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
