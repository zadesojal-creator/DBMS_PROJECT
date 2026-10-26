import React, { useState } from 'react';
import { X, DollarSign, CheckCircle2 } from 'lucide-react';
import { api } from '../api/client';
import { formatINR } from '../utils/formatters';

export default function DepositModal({ currentBalance, onClose, onDepositSuccess }) {
  const [amount, setAmount] = useState(25000);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const presets = [10000, 25000, 50000];

  const handleDeposit = async () => {
    setError(null);
    const amt = parseFloat(amount);
    if (!amt || amt <= 0) {
      setError('Amount must be positive');
      return;
    }
    if (amt > 50000) {
      setError('Maximum deposit is ₹50,000 per transaction (daily policy limit)');
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.investor.deposit({ amount: amt });
      if (res.ok) {
        setSuccess(res.data);
        if (onDepositSuccess) onDepositSuccess();
      } else {
        setError(res.error?.message || 'Deposit failed');
      }
    } catch (err) {
      setError(err.message || 'Deposit failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: '440px' }} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1.25rem', borderBottom: '1px solid var(--border)' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)' }}>
              Add Virtual Funds
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
              Virtual Cash · Max ₹50,000/day
            </span>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={onClose} style={{ padding: '0.35rem' }}>
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '1.25rem' }}>
          {success ? (
            <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
              <CheckCircle2 size={48} color="var(--gain)" style={{ margin: '0 auto 1rem' }} />
              <h4 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--gain)', marginBottom: '0.5rem' }}>
                Deposit Successful!
              </h4>
              <p style={{ fontSize: '0.875rem', color: 'var(--muted)', marginBottom: '1rem' }}>
                {formatINR(success.deposited_amount)} added to your virtual account.
              </p>
              <div style={{ fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                New Balance: <strong className="num" style={{ color: 'var(--navy)' }}>{formatINR(success.new_virtual_balance)}</strong>
              </div>
              <button className="btn btn-primary" style={{ width: '100%' }} onClick={onClose}>
                Done
              </button>
            </div>
          ) : (
            <div>
              <div style={{ marginBottom: '1rem', background: '#F8FAFC', padding: '0.75rem', borderRadius: 'var(--radius-md)', fontSize: '0.85rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--muted)' }}>Current Balance:</span>
                  <strong className="num">{formatINR(currentBalance)}</strong>
                </div>
              </div>

              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--navy)', marginBottom: '0.4rem' }}>
                  Deposit Amount (₹)
                </label>
                <input
                  type="number"
                  min="1"
                  max="50000"
                  step="1000"
                  value={amount}
                  onChange={e => setAmount(e.target.value)}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', fontSize: '1.1rem', fontVariantNumeric: 'tabular-nums' }}
                />
              </div>

              {/* Preset Buttons */}
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
                {presets.map(p => (
                  <button
                    key={p}
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ flex: 1 }}
                    onClick={() => setAmount(p)}
                  >
                    +{formatINR(p)}
                  </button>
                ))}
              </div>

              {error && (
                <div style={{ color: 'var(--loss)', fontSize: '0.8rem', marginBottom: '1rem', background: 'var(--loss-bg)', padding: '0.5rem', borderRadius: 'var(--radius-sm)' }}>
                  {error}
                </div>
              )}

              <button
                className="btn btn-primary"
                style={{ width: '100%', padding: '0.75rem' }}
                onClick={handleDeposit}
                disabled={submitting}
              >
                {submitting ? 'Processing...' : `Deposit ${formatINR(amount)}`}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
