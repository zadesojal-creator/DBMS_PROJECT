import React from 'react';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

export default function KpiTile({ title, value, subtext, changePct, isCurrency = true }) {
  const hasChange = changePct !== undefined && changePct !== null;
  const numChange = Number(changePct);
  const isPositive = numChange > 0;
  const isNegative = numChange < 0;

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          {title}
        </span>
        {hasChange && (
          <span className={`badge ${isPositive ? 'badge-gain' : isNegative ? 'badge-loss' : 'badge-neutral'}`}>
            {isPositive ? <ArrowUpRight size={12} /> : isNegative ? <ArrowDownRight size={12} /> : <Minus size={12} />}
            {isPositive ? `+${numChange.toFixed(2)}%` : `${numChange.toFixed(2)}%`}
          </span>
        )}
      </div>

      <div className="num" style={{ fontSize: '1.65rem', fontWeight: 700, color: 'var(--navy)' }}>
        {value}
      </div>

      {subtext && (
        <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>
          {subtext}
        </div>
      )}
    </div>
  );
}
