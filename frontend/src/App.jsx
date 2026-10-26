import React, { useState, useEffect } from 'react';
import { useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import Login from './pages/Login';
import { api } from './api/client';

// Investor Pages
import DashboardView from './pages/investor/DashboardView';
import MarketView from './pages/investor/MarketView';
import PortfolioView from './pages/investor/PortfolioView';
import TransactionsView from './pages/investor/TransactionsView';
import WatchlistView from './pages/investor/WatchlistView';

// Broker Pages
import ClientsView from './pages/broker/ClientsView';
import AnalyticsView from './pages/broker/AnalyticsView';

// Admin Pages
import OverviewView from './pages/admin/OverviewView';
import CompaniesView from './pages/admin/CompaniesView';
import UsersView from './pages/admin/UsersView';
import SimulatorView from './pages/admin/SimulatorView';
import AuditLogsView from './pages/admin/AuditLogsView';

// AI Assistant
import AssistantView from './pages/ai/AssistantView';

// Modals
import StockChartModal from './components/StockChartModal';
import TradeTicketModal from './components/TradeTicketModal';

export default function App() {
  const { user, loading } = useAuth();
  const [currentTab, setCurrentTab] = useState('');
  const [stocks, setStocks] = useState([]);
  const [selectedStockForChart, setSelectedStockForChart] = useState(null);
  const [selectedStockForTrade, setSelectedStockForTrade] = useState(null);

  // Set default tab on login based on role
  useEffect(() => {
    if (user?.role === 'ADMIN') setCurrentTab('overview');
    else if (user?.role === 'BROKER') setCurrentTab('clients');
    else if (user?.role === 'INVESTOR') setCurrentTab('dashboard');
  }, [user?.role]);

  // Load stock directory for global search
  useEffect(() => {
    if (user) {
      api.market.getPrices()
        .then(res => {
          if (res.ok && res.data) setStocks(res.data);
        })
        .catch(console.error);
    }
  }, [user]);

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg)',
        color: 'var(--muted)',
        fontSize: '1rem',
        fontWeight: 500
      }}>
        Initializing StockTrade Platform...
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  const renderContent = () => {
    switch (currentTab) {
      // Investor tabs
      case 'dashboard':
        return <DashboardView />;
      case 'market':
        return <MarketView initialStocks={stocks} />;
      case 'watchlist':
        return <WatchlistView allStocks={stocks} />;
      case 'portfolio':
        return <PortfolioView />;
      case 'transactions':
        return <TransactionsView />;

      // Broker tabs
      case 'clients':
        return <ClientsView />;
      case 'analytics':
        return <AnalyticsView />;

      // Admin tabs
      case 'overview':
        return <OverviewView />;
      case 'companies':
        return <CompaniesView />;
      case 'users':
        return <UsersView />;
      case 'simulator':
        return <SimulatorView />;
      case 'audit':
        return <AuditLogsView />;

      // AI Assistant (common to all roles)
      case 'ai':
        return <AssistantView />;

      default:
        return user.role === 'ADMIN' ? <OverviewView /> : user.role === 'BROKER' ? <ClientsView /> : <DashboardView />;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Navbar
        stocks={stocks}
        onSearchSelect={(stock) => setSelectedStockForChart(stock)}
      />

      <div style={{ display: 'flex', flex: 1, minHeight: 'calc(100vh - 60px)' }}>
        <Sidebar currentTab={currentTab} onSelectTab={setCurrentTab} />

        <main style={{
          flex: 1,
          padding: '1.75rem',
          maxWidth: '1360px',
          width: '100%',
          margin: '0 auto',
          overflowY: 'auto'
        }}>
          {renderContent()}
        </main>
      </div>

      {/* Global Modals triggered from Search */}
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
          availableCash={100000}
          onClose={() => setSelectedStockForTrade(null)}
          onOrderExecuted={() => {
            // refresh data if on dashboard or market
          }}
        />
      )}
    </div>
  );
}
