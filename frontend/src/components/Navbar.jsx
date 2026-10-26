import React, { useState, useEffect } from 'react';
import { Search, LogOut, TrendingUp, User, Command } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import SimulatedBadge from './SimulatedBadge';
import BullLogo from './BullLogo';

export default function Navbar({ onSearchSelect, stocks = [] }) {
  const { user, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);

  // Keyboard shortcut Ctrl+K to focus search
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        const input = document.getElementById('navbar-stock-search');
        if (input) input.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSearchChange = (q) => {
    setSearchQuery(q);
    if (!q.trim()) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }
    const filtered = stocks.filter(s => 
      s.symbol.toLowerCase().includes(q.toLowerCase()) || 
      s.company_name.toLowerCase().includes(q.toLowerCase())
    ).slice(0, 8);
    setSearchResults(filtered);
    setShowDropdown(true);
  };

  return (
    <header style={{
      height: '60px',
      background: 'var(--card)',
      borderBottom: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 1.5rem',
      position: 'sticky',
      top: 0,
      zIndex: 100
    }}>
      {/* Brand & Badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontWeight: 800, fontSize: '1.15rem', color: 'var(--navy)', letterSpacing: '-0.02em' }}>
          <BullLogo size={28} glow={false} />
          <span>STOCKTRADE</span>
        </div>
        <SimulatedBadge />
      </div>

      {/* Global Stock Search (Ctrl+K) */}
      <div style={{ position: 'relative', width: '320px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          background: 'var(--bg)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border)',
          padding: '0.35rem 0.65rem'
        }}>
          <Search size={16} color="var(--muted)" style={{ marginRight: '0.4rem' }} />
          <input
            id="navbar-stock-search"
            type="text"
            placeholder="Search stock or symbol... (Ctrl+K)"
            value={searchQuery}
            onChange={e => handleSearchChange(e.target.value)}
            onFocus={() => searchQuery && setShowDropdown(true)}
            style={{
              border: 'none',
              background: 'transparent',
              outline: 'none',
              fontSize: '0.825rem',
              width: '100%',
              color: 'var(--text-main)'
            }}
          />
        </div>

        {/* Search Results Dropdown */}
        {showDropdown && searchResults.length > 0 && (
          <div style={{
            position: 'absolute',
            top: '110%',
            left: 0,
            right: 0,
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-md)',
            zIndex: 110,
            maxHeight: '260px',
            overflowY: 'auto'
          }}>
            {searchResults.map(stock => (
              <div
                key={stock.id || stock.stock_id}
                onClick={() => {
                  setShowDropdown(false);
                  setSearchQuery('');
                  if (onSearchSelect) onSearchSelect(stock);
                }}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '0.5rem 0.75rem',
                  cursor: 'pointer',
                  borderBottom: '1px solid var(--border)',
                  fontSize: '0.825rem'
                }}
                onMouseEnter={e => e.currentTarget.style.backgroundColor = '#F8FAFC'}
                onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                <div>
                  <strong style={{ color: 'var(--navy)' }}>{stock.symbol}</strong>
                  <span style={{ color: 'var(--muted)', marginLeft: '0.5rem', fontSize: '0.75rem' }}>{stock.company_name}</span>
                </div>
                <span className="num" style={{ fontWeight: 600 }}>₹{Number(stock.current_price ?? stock.price ?? 0).toFixed(2)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* User Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
          <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: '#E2E8F0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <User size={18} color="var(--navy)" />
          </div>
          <div>
            <div style={{ fontWeight: 600, color: 'var(--navy)', lineHeight: 1.2 }}>{user?.full_name || user?.username}</div>
            <span className="badge badge-neutral" style={{ fontSize: '0.65rem', padding: '0.1rem 0.4rem' }}>
              {user?.role}
            </span>
          </div>
        </div>

        <button
          className="btn btn-secondary btn-sm"
          onClick={logout}
          title="Sign out"
          style={{ padding: '0.4rem 0.6rem' }}
        >
          <LogOut size={16} />
          <span>Exit</span>
        </button>
      </div>
    </header>
  );
}
