import React from 'react';
import {
  LayoutDashboard,
  TrendingUp,
  Briefcase,
  History,
  Users,
  PieChart,
  Building2,
  Sliders,
  ShieldAlert,
  Sparkles,
  Star
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Sidebar({ currentTab, onSelectTab }) {
  const { user } = useAuth();
  const role = user?.role;

  const investorNav = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'market', label: 'Market Directory', icon: TrendingUp },
    { id: 'watchlist', label: 'Watchlist & Alerts', icon: Star },
    { id: 'portfolio', label: 'Portfolio & Holdings', icon: Briefcase },
    { id: 'transactions', label: 'Transactions & Ledger', icon: History },
    { id: 'ai', label: 'AI SQL Assistant', icon: Sparkles },
  ];

  const brokerNav = [
    { id: 'clients', label: 'Client Management', icon: Users },
    { id: 'analytics', label: 'Commission Analytics', icon: PieChart },
    { id: 'market', label: 'Market Directory', icon: TrendingUp },
    { id: 'ai', label: 'AI SQL Assistant', icon: Sparkles },
  ];

  const adminNav = [
    { id: 'overview', label: 'Platform Overview', icon: LayoutDashboard },
    { id: 'companies', label: 'Listed Companies', icon: Building2 },
    { id: 'users', label: 'User Accounts', icon: Users },
    { id: 'simulator', label: 'Simulator Controls', icon: Sliders },
    { id: 'audit', label: 'Security Audit Logs', icon: ShieldAlert },
    { id: 'ai', label: 'AI SQL Assistant', icon: Sparkles },
  ];

  let items = investorNav;
  if (role === 'BROKER') items = brokerNav;
  if (role === 'ADMIN') items = adminNav;

  return (
    <aside style={{
      width: '230px',
      background: 'var(--navy)',
      color: '#E2E8F0',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      padding: '1.25rem 0.75rem',
      userSelect: 'none'
    }}>
      <div style={{ padding: '0 0.5rem 1rem 0.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', marginBottom: '1rem' }}>
        <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'rgba(255,255,255,0.5)', letterSpacing: '0.08em', fontWeight: 600 }}>
          {role} CONSOLE
        </div>
        <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#FFFFFF', marginTop: '0.2rem' }}>
          Workspace
        </div>
      </div>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', flex: 1 }}>
        {items.map(item => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem',
                padding: '0.6rem 0.75rem',
                borderRadius: 'var(--radius-md)',
                border: 'none',
                background: isActive ? 'var(--teal)' : 'transparent',
                color: isActive ? '#FFFFFF' : '#CBD5E1',
                fontSize: '0.85rem',
                fontWeight: isActive ? 600 : 500,
                textAlign: 'left',
                cursor: 'pointer',
                transition: 'background 0.15s ease'
              }}
              onMouseEnter={e => {
                if (!isActive) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
              }}
              onMouseLeave={e => {
                if (!isActive) e.currentTarget.style.background = 'transparent';
              }}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div style={{ padding: '0.75rem 0.5rem 0', borderTop: '1px solid rgba(255,255,255,0.1)', fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)' }}>
        StockTrade v2.0 · DBMS Lab
      </div>
    </aside>
  );
}
