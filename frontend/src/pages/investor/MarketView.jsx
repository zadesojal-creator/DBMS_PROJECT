import React, { useState, useEffect, useRef } from 'react';
import { Search, Filter, BarChart2, ShoppingCart, RefreshCw, ArrowUpDown, Star } from 'lucide-react';
import { api } from '../../api/client';
import { formatINR, formatPct } from '../../utils/formatters';
import StockChartModal from '../../components/StockChartModal';
import TradeTicketModal from '../../components/TradeTicketModal';

export default function MarketView({ initialStocks = [] }) {
  const [stocks, setStocks] = useState(initialStocks);
  const [search, setSearch] = useState('');
  const [selectedSector, setSelectedSector] = useState('ALL');
  const [sortBy, setSortBy] = useState('symbol');
  const [sortOrder, setSortOrder] = useState('asc');
  const [priceFlashMap, setPriceFlashMap] = useState({});
  const [summary, setSummary] = useState(null);
  const [watchlistIds, setWatchlistIds] = useState(new Set());

  const [selectedStockForChart, setSelectedStockForChart] = useState(null);
  const [selectedStockForTrade, setSelectedStockForTrade] = useState(null);

  const prevPricesRef = useRef({});

  const updatePricesFromData = (dataList) => {
    if (!dataList || !dataList.length) return;
    const newFlash = {};
    dataList.forEach(s => {
      const stockId = s.stock_id || s.id;
      const currentPrice = Number(s.current_price ?? s.price ?? 0);
      const old = prevPricesRef.current[stockId];
      if (old !== undefined) {
        if (currentPrice > old) newFlash[stockId] = 'flash-up';
        else if (currentPrice < old) newFlash[stockId] = 'flash-down';
      }
      prevPricesRef.current[stockId] = currentPrice;
    });

    if (Object.keys(newFlash).length > 0) {
      setPriceFlashMap(prev => ({ ...prev, ...newFlash }));
      setTimeout(() => {
        setPriceFlashMap(prev => {
          const cleared = { ...prev };
          Object.keys(newFlash).forEach(k => delete cleared[k]);
          return cleared;
        });
      }, 1000);
    }

    setStocks(prev => {
      const map = new Map(prev.map(item => [item.stock_id || item.id, item]));
      dataList.forEach(item => {
        const id = item.stock_id || item.id;
        const existing = map.get(id);
        map.set(id, existing ? { ...existing, ...item } : item);
      });
      return Array.from(map.values());
    });
  };

  const loadMarket = async () => {
    try {
      const [pricesRes, sumRes, wlRes] = await Promise.all([
        api.market.getPrices(),
        api.investor.getSummary().catch(() => null),
        api.investor.getWatchlist().catch(() => null)
      ]);

      if (pricesRes.ok && pricesRes.data) {
        updatePricesFromData(pricesRes.data);
      }
      if (sumRes?.ok) setSummary(sumRes.data);
      if (wlRes?.ok && Array.isArray(wlRes.data)) {
        setWatchlistIds(new Set(wlRes.data.map(item => item.stock_id)));
      }
    } catch (err) {
      console.error('Error polling market data', err);
    }
  };

  const handleToggleWatchlist = async (stockId) => {
    const isWatched = watchlistIds.has(stockId);
    try {
      if (isWatched) {
        await api.investor.removeFromWatchlist(stockId);
        setWatchlistIds(prev => {
          const next = new Set(prev);
          next.delete(stockId);
          return next;
        });
      } else {
        await api.investor.addToWatchlist(stockId);
        setWatchlistIds(prev => new Set(prev).add(stockId));
      }
    } catch (err) {
      console.error('Watchlist toggle error', err);
    }
  };

  useEffect(() => {
    loadMarket();

    let eventSource = null;
    let pollInterval = null;

    try {
      eventSource = new EventSource('/market/api/v1/market/stream');

      eventSource.addEventListener('snapshot', (e) => {
        try {
          const snapshot = JSON.parse(e.data);
          if (Array.isArray(snapshot)) {
            setStocks(snapshot);
            snapshot.forEach(s => {
              const id = s.stock_id || s.id;
              prevPricesRef.current[id] = Number(s.current_price ?? s.price ?? 0);
            });
          }
        } catch (err) {
          console.error('Error parsing SSE snapshot', err);
        }
      });

      eventSource.addEventListener('tick', (e) => {
        try {
          const deltas = JSON.parse(e.data);
          if (Array.isArray(deltas)) {
            updatePricesFromData(deltas);
          }
        } catch (err) {
          console.error('Error parsing SSE tick', err);
        }
      });

      eventSource.onerror = () => {
        if (!pollInterval) {
          pollInterval = setInterval(loadMarket, 3000);
        }
      };
    } catch {
      pollInterval = setInterval(loadMarket, 3000);
    }

    return () => {
      if (eventSource) eventSource.close();
      if (pollInterval) clearInterval(pollInterval);
    };
  }, []);

  // Unique sectors
  const sectors = ['ALL', ...Array.from(new Set(stocks.map(s => s.sector).filter(Boolean)))];

  // Filtering & Sorting
  const filteredStocks = stocks.filter(s => {
    const symbolStr = (s.symbol || '').toLowerCase();
    const nameStr = (s.company_name || '').toLowerCase();
    const query = search.toLowerCase();
    const matchesSearch = symbolStr.includes(query) || nameStr.includes(query);
    const matchesSector = selectedSector === 'ALL' || s.sector === selectedSector;
    return matchesSearch && matchesSector;
  }).sort((a, b) => {
    let cmp = 0;
    const aPrice = Number(a.current_price ?? a.price ?? 0);
    const bPrice = Number(b.current_price ?? b.price ?? 0);
    const aChange = Number(a.change_pct ?? a.day_change_pct ?? 0);
    const bChange = Number(b.change_pct ?? b.day_change_pct ?? 0);

    if (sortBy === 'symbol') cmp = (a.symbol || '').localeCompare(b.symbol || '');
    else if (sortBy === 'price') cmp = aPrice - bPrice;
    else if (sortBy === 'change') cmp = aChange - bChange;
    return sortOrder === 'asc' ? cmp : -cmp;
  });

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--navy)' }}>Market Directory</h2>
          <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
            Showing 100 NSE/BSE listed equities with live simulated price feeds
          </span>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={loadMarket}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="card" style={{ padding: '0.75rem 1rem', display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: '0.75rem', flex: 1, minWidth: '280px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={16} color="var(--muted)" style={{ position: 'absolute', left: '0.65rem', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Filter by symbol or company name..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{
                width: '100%',
                padding: '0.45rem 0.65rem 0.45rem 2.2rem',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.85rem',
                outline: 'none'
              }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Filter size={15} color="var(--muted)" />
            <select
              value={selectedSector}
              onChange={e => setSelectedSector(e.target.value)}
              style={{
                padding: '0.45rem 0.65rem',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.85rem',
                outline: 'none',
                background: 'var(--card)'
              }}
            >
              {sectors.map(sec => (
                <option key={sec} value={sec}>{sec}</option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
          Displaying <strong>{filteredStocks.length}</strong> of <strong>{stocks.length}</strong> equities
        </div>
      </div>

      {/* Stocks Table */}
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ cursor: 'pointer' }} onClick={() => handleSort('symbol')}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  Symbol & Company <ArrowUpDown size={12} />
                </div>
              </th>
              <th>Sector</th>
              <th className="numeric" style={{ cursor: 'pointer' }} onClick={() => handleSort('price')}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.3rem' }}>
                  Market Price <ArrowUpDown size={12} />
                </div>
              </th>
              <th className="numeric" style={{ cursor: 'pointer' }} onClick={() => handleSort('change')}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.3rem' }}>
                  24h Change <ArrowUpDown size={12} />
                </div>
              </th>
              <th className="numeric">Previous Close</th>
              <th style={{ textAlign: 'center' }}>Trade / Analytics</th>
            </tr>
          </thead>
          <tbody>
            {filteredStocks.map(s => {
              const stockId = s.stock_id || s.id;
              const flashClass = priceFlashMap[stockId] || '';
              const currentPrice = Number(s.current_price ?? s.price ?? 0);
              const changePct = Number(s.change_pct ?? s.day_change_pct ?? 0);
              const prevClose = Number(s.previous_close ?? 0);
              const isGain = changePct >= 0;

              return (
                <tr key={stockId}>
                  <td>
                    <strong style={{ color: 'var(--navy)' }}>{s.symbol}</strong>
                    <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{s.company_name}</div>
                  </td>
                  <td>
                    <span className="badge badge-neutral" style={{ fontSize: '0.7rem' }}>
                      {s.sector}
                    </span>
                  </td>
                  <td className={`numeric font-bold ${flashClass}`} style={{ fontSize: '0.95rem' }}>
                    {formatINR(currentPrice)}
                  </td>
                  <td className="numeric">
                    <span className={`badge ${isGain ? 'badge-gain' : 'badge-loss'}`}>
                      {formatPct(changePct)}
                    </span>
                  </td>
                  <td className="numeric" style={{ color: 'var(--muted)' }}>
                    {formatINR(prevClose)}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <div style={{ display: 'inline-flex', gap: '0.4rem' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ padding: '0.25rem 0.45rem' }}
                        onClick={() => handleToggleWatchlist(stockId)}
                        title={watchlistIds.has(stockId) ? "Remove from Watchlist" : "Add to Watchlist"}
                      >
                        <Star
                          size={13}
                          color={watchlistIds.has(stockId) ? "var(--amber)" : "var(--muted)"}
                          fill={watchlistIds.has(stockId) ? "var(--amber)" : "transparent"}
                        />
                      </button>
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ padding: '0.25rem 0.55rem' }}
                        onClick={() => setSelectedStockForChart({ ...s, current_price: currentPrice, price: currentPrice, change_pct: changePct })}
                        title="Interactive Chart"
                      >
                        <BarChart2 size={13} /> Chart
                      </button>
                      <button
                        className="btn btn-primary btn-sm"
                        style={{ padding: '0.25rem 0.65rem' }}
                        onClick={() => setSelectedStockForTrade({ ...s, current_price: currentPrice, price: currentPrice, change_pct: changePct })}
                      >
                        <ShoppingCart size={13} /> Trade
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
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
          availableCash={summary?.available_cash || 100000}
          onClose={() => setSelectedStockForTrade(null)}
          onOrderExecuted={loadMarket}
        />
      )}
    </div>
  );
}
