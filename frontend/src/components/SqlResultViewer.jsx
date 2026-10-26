import React, { useState, useMemo } from 'react';
import { Table as TableIcon, BarChart2, TrendingUp, PieChart } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Bar, Line, Doughnut } from 'react-chartjs-2';
import { formatINR } from '../utils/formatters';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const PALETTE = [
  '#0EA5E9', '#14B8A6', '#6366F1', '#F59E0B', '#10B981',
  '#EC4899', '#8B5CF6', '#F97316', '#06B6D4', '#84CC16'
];

export default function SqlResultViewer({ columns = [], rows = [], durationMs = 0, rowCount = 0 }) {
  const [activeTab, setActiveTab] = useState('table'); // 'table' | 'bar' | 'line' | 'doughnut'

  // Detect column types
  const { numericCols, textCols } = useMemo(() => {
    if (!rows || rows.length === 0) return { numericCols: [], textCols: [] };
    const first = rows[0];
    const nCols = [];
    const tCols = [];
    const allCols = columns.length > 0 ? columns : Object.keys(first);

    allCols.forEach(col => {
      const hasNumber = rows.some(r => typeof r[col] === 'number');
      if (hasNumber) {
        nCols.push(col);
      } else {
        tCols.push(col);
      }
    });
    return { numericCols: nCols, textCols: tCols };
  }, [columns, rows]);

  // Selected chart dimensions
  const [selectedLabelCol, setSelectedLabelCol] = useState('');
  const [selectedMetricCol, setSelectedMetricCol] = useState('');

  // Auto-select initial dimensions
  const currentLabelCol = selectedLabelCol || (textCols.length > 0 ? textCols[0] : (columns[0] || ''));
  const currentMetricCol = selectedMetricCol || (numericCols.length > 0 ? numericCols[0] : '');

  const hasChartableData = numericCols.length > 0 && rows.length > 0;

  // Prepare chart dataset
  const chartData = useMemo(() => {
    if (!hasChartableData) return null;
    const labels = rows.map((r, i) => {
      const val = r[currentLabelCol];
      return val !== null && val !== undefined ? String(val) : `#${i + 1}`;
    });
    const dataValues = rows.map(r => Number(r[currentMetricCol] || 0));

    return {
      labels,
      datasets: [
        {
          label: currentMetricCol.replace(/_/g, ' ').toUpperCase(),
          data: dataValues,
          backgroundColor: activeTab === 'doughnut'
            ? labels.map((_, i) => PALETTE[i % PALETTE.length])
            : 'rgba(14, 165, 233, 0.75)',
          borderColor: activeTab === 'doughnut'
            ? '#FFFFFF'
            : '#0EA5E9',
          borderWidth: activeTab === 'doughnut' ? 2 : 1.5,
          borderRadius: activeTab === 'bar' ? 4 : 0,
          fill: activeTab === 'line',
          tension: 0.25
        }
      ]
    };
  }, [rows, currentLabelCol, currentMetricCol, hasChartableData, activeTab]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: activeTab === 'doughnut' || activeTab === 'line',
        position: 'bottom',
        labels: {
          boxWidth: 12,
          font: { size: 11, family: 'sans-serif' }
        }
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const raw = context.raw;
            const isCurrency = ['price', 'value', 'amount', 'pnl', 'fee', 'balance', 'cost'].some(k => currentMetricCol.toLowerCase().includes(k));
            return isCurrency ? ` ${context.dataset.label}: ${formatINR(raw)}` : ` ${context.dataset.label}: ${raw.toLocaleString()}`;
          }
        }
      }
    },
    scales: activeTab === 'doughnut' ? {} : {
      x: {
        grid: { display: false },
        ticks: { font: { size: 10 }, maxRotation: 45 }
      },
      y: {
        grid: { color: 'rgba(0, 0, 0, 0.05)' },
        ticks: {
          font: { size: 10 },
          callback: (val) => {
            const isCurrency = ['price', 'value', 'amount', 'pnl', 'fee', 'balance', 'cost'].some(k => currentMetricCol.toLowerCase().includes(k));
            return isCurrency && Math.abs(val) >= 1000 ? `₹${(val / 1000).toFixed(0)}k` : val;
          }
        }
      }
    }
  };

  if (!rows || rows.length === 0) {
    return (
      <div className="card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--muted)', fontSize: '0.85rem' }}>
        Query executed successfully with 0 matching database records.
      </div>
    );
  }

  const colsToRender = columns.length > 0 ? columns : Object.keys(rows[0]);

  return (
    <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
      {/* Result Toolbar */}
      <div style={{
        padding: '0.75rem 1rem',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.75rem',
        background: '#F8FAFC'
      }}>
        {/* Left: Metrics & Row Count */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--navy)' }}>
            Query Results ({rowCount || rows.length} rows)
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--muted)', background: '#E2E8F0', padding: '0.15rem 0.45rem', borderRadius: 'var(--radius-sm)', fontWeight: 500 }}>
            {durationMs} ms
          </span>
        </div>

        {/* Right: View Toggles & Chart Dimension Selectors */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          {hasChartableData && activeTab !== 'table' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem' }}>
              <span style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>X-Axis:</span>
              <select
                className="form-control"
                style={{ fontSize: '0.75rem', padding: '0.2rem 0.4rem', height: 'auto' }}
                value={currentLabelCol}
                onChange={e => setSelectedLabelCol(e.target.value)}
              >
                {colsToRender.map(c => (
                  <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>
                ))}
              </select>

              <span style={{ color: 'var(--muted)', fontSize: '0.75rem', marginLeft: '0.25rem' }}>Metric:</span>
              <select
                className="form-control"
                style={{ fontSize: '0.75rem', padding: '0.2rem 0.4rem', height: 'auto' }}
                value={currentMetricCol}
                onChange={e => setSelectedMetricCol(e.target.value)}
              >
                {numericCols.map(c => (
                  <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
          )}

          {/* View Modes */}
          <div style={{ display: 'inline-flex', background: '#E2E8F0', padding: '0.15rem', borderRadius: 'var(--radius-sm)' }}>
            <button
              type="button"
              className={`btn btn-sm ${activeTab === 'table' ? 'btn-primary' : ''}`}
              style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', border: 'none', background: activeTab === 'table' ? 'var(--primary)' : 'transparent', color: activeTab === 'table' ? '#fff' : 'var(--navy)' }}
              onClick={() => setActiveTab('table')}
              title="Table View"
            >
              <TableIcon size={13} /> Table
            </button>
            {hasChartableData && (
              <>
                <button
                  type="button"
                  className={`btn btn-sm ${activeTab === 'bar' ? 'btn-primary' : ''}`}
                  style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', border: 'none', background: activeTab === 'bar' ? 'var(--primary)' : 'transparent', color: activeTab === 'bar' ? '#fff' : 'var(--navy)' }}
                  onClick={() => setActiveTab('bar')}
                  title="Bar Chart"
                >
                  <BarChart2 size={13} /> Bar
                </button>
                <button
                  type="button"
                  className={`btn btn-sm ${activeTab === 'line' ? 'btn-primary' : ''}`}
                  style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', border: 'none', background: activeTab === 'line' ? 'var(--primary)' : 'transparent', color: activeTab === 'line' ? '#fff' : 'var(--navy)' }}
                  onClick={() => setActiveTab('line')}
                  title="Line Chart"
                >
                  <TrendingUp size={13} /> Line
                </button>
                <button
                  type="button"
                  className={`btn btn-sm ${activeTab === 'doughnut' ? 'btn-primary' : ''}`}
                  style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', border: 'none', background: activeTab === 'doughnut' ? 'var(--primary)' : 'transparent', color: activeTab === 'doughnut' ? '#fff' : 'var(--navy)' }}
                  onClick={() => setActiveTab('doughnut')}
                  title="Doughnut Chart"
                >
                  <PieChart size={13} /> Donut
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Main View Body */}
      {activeTab === 'table' ? (
        <div className="table-container" style={{ border: 'none', maxHeight: '380px' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '40px', textAlign: 'center', color: 'var(--muted)', fontSize: '0.75rem' }}>#</th>
                {colsToRender.map(col => (
                  <th key={col} style={{ textTransform: 'capitalize' }} className={numericCols.includes(col) ? 'numeric' : ''}>
                    {col.replace(/_/g, ' ')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr key={idx}>
                  <td style={{ textAlign: 'center', color: 'var(--muted)', fontSize: '0.75rem' }}>{idx + 1}</td>
                  {colsToRender.map((col, cIdx) => {
                    const val = row[col];
                    const isNum = typeof val === 'number';
                    const isCurrency = isNum && ['price', 'cost', 'balance', 'amount', 'pnl', 'fee', 'value'].some(k => col.toLowerCase().includes(k));
                    return (
                      <td key={cIdx} className={isNum ? 'numeric' : ''}>
                        {val === null || val === undefined ? (
                          <span style={{ color: 'var(--muted)' }}>—</span>
                        ) : isCurrency ? (
                          formatINR(val)
                        ) : (
                          String(val)
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ height: '340px', padding: '1.25rem', position: 'relative' }}>
          {chartData && (
            activeTab === 'bar' ? (
              <Bar data={chartData} options={chartOptions} />
            ) : activeTab === 'line' ? (
              <Line data={chartData} options={chartOptions} />
            ) : (
              <Doughnut data={chartData} options={chartOptions} />
            )
          )}
        </div>
      )}
    </div>
  );
}
