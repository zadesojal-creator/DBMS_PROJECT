import React, { useState, useEffect } from 'react';
import { X, TrendingUp, BarChart2 } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Filler,
  Legend
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { api } from '../api/client';
import { formatINR, formatPct } from '../utils/formatters';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Filler,
  Legend
);

export default function StockChartModal({ stock, onClose, onOpenTrade }) {
  const [interval, setIntervalVal] = useState('5m');
  const [candles, setCandles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!stock?.symbol) return;
    setLoading(true);
    setError(null);
    api.market.getHistory(stock.symbol, interval)
      .then(res => {
        if (res.ok) {
          setCandles(res.data.candles || []);
        } else {
          setError('Failed to load chart candles');
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [stock?.symbol, interval]);

  if (!stock) return null;

  const labels = candles.map(c => {
    const d = new Date(c.bucket || c.time);
    return interval === '1h' 
      ? d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric', hour: '2-digit' })
      : d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  });

  const closePrices = candles.map(c => c.close);
  const isUp = candles.length > 1 && candles[candles.length - 1].close >= candles[0].close;
  const strokeColor = isUp ? '#138A5B' : '#C73E3E';
  const fillColor = isUp ? 'rgba(19, 138, 91, 0.08)' : 'rgba(199, 62, 62, 0.08)';

  const chartData = {
    labels,
    datasets: [
      {
        label: `${stock.symbol} Close (₹)`,
        data: closePrices,
        borderColor: strokeColor,
        backgroundColor: fillColor,
        fill: true,
        tension: 0.2,
        pointRadius: candles.length > 50 ? 0 : 2,
        borderWidth: 2,
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: (context) => {
            const idx = context.dataIndex;
            const c = candles[idx];
            if (!c) return `Close: ₹${context.raw}`;
            return [
              `Close: ₹${c.close.toFixed(2)}`,
              `Open: ₹${c.open.toFixed(2)}`,
              `High: ₹${c.high.toFixed(2)}`,
              `Low: ₹${c.low.toFixed(2)}`,
              `Volume: ${c.volume.toLocaleString('en-IN')}`
            ];
          }
        }
      }
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { maxTicksLimit: 8, font: { size: 10 } }
      },
      y: {
        grid: { color: '#E3E8EE' },
        ticks: {
          callback: (v) => `₹${v}`,
          font: { size: 10 }
        }
      }
    }
  };

  const latestCandle = candles.length > 0 ? candles[candles.length - 1] : null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: '780px' }} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1.25rem', borderBottom: '1px solid var(--border)' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--navy)' }}>{stock.symbol}</span>
              <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>{stock.company_name}</span>
              <span className="badge badge-neutral">{stock.sector}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '0.35rem' }}>
              <span className="num" style={{ fontSize: '1.4rem', fontWeight: 700 }}>
                {formatINR(stock.current_price ?? stock.price ?? (latestCandle ? latestCandle.close : 0))}
              </span>
              <span className={`badge ${(stock.change_pct ?? stock.day_change_pct ?? 0) >= 0 ? 'badge-gain' : 'badge-loss'}`}>
                {formatPct(stock.change_pct ?? stock.day_change_pct)}
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {onOpenTrade && (
              <button className="btn btn-primary btn-sm" onClick={() => { onClose(); onOpenTrade(stock); }}>
                Trade {stock.symbol}
              </button>
            )}
            <button className="btn btn-secondary btn-sm" onClick={onClose} style={{ padding: '0.4rem' }}>
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Intervals & Stats */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1.25rem', background: '#F8FAFC', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {['1m', '5m', '1h'].map(int => (
              <button
                key={int}
                className={`btn btn-sm ${interval === int ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '0.2rem 0.6rem' }}
                onClick={() => setIntervalVal(int)}
              >
                {int.toUpperCase()}
              </button>
            ))}
          </div>

          {latestCandle && (
            <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', color: 'var(--muted)' }} className="tabular">
              <span>O: <strong style={{ color: 'var(--text-main)' }}>{latestCandle.open.toFixed(2)}</strong></span>
              <span>H: <strong style={{ color: 'var(--gain)' }}>{latestCandle.high.toFixed(2)}</strong></span>
              <span>L: <strong style={{ color: 'var(--loss)' }}>{latestCandle.low.toFixed(2)}</strong></span>
              <span>C: <strong style={{ color: 'var(--text-main)' }}>{latestCandle.close.toFixed(2)}</strong></span>
            </div>
          )}
        </div>

        {/* Chart Canvas */}
        <div style={{ height: '360px', padding: '1rem 1.25rem', position: 'relative' }}>
          {loading && (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(255,255,255,0.7)', zIndex: 5 }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--muted)' }}>Loading price candles...</span>
            </div>
          )}
          {error ? (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--loss)' }}>
              {error}
            </div>
          ) : (
            <Line data={chartData} options={chartOptions} />
          )}
        </div>
      </div>
    </div>
  );
}
