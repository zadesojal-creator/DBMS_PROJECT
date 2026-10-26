import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  Shield,
  Lock,
  User,
  Eye,
  EyeOff,
  AlertCircle,
  ChevronDown,
  ArrowRight,
  CheckCircle2
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import BullLogo from '../components/BullLogo';

export default function Login() {
  const { login } = useAuth();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [showDemoAccounts, setShowDemoAccounts] = useState(false);
  const [focusedField, setFocusedField] = useState(null);

  // Live real simulated stock prices from backend API
  const defaultInitialStocks = [
    { symbol: 'TCS', company_name: 'Tata Consultancy Services', current_price: 4155.30, day_change: -34.15, day_change_pct: -0.82 },
    { symbol: 'RELIANCE', company_name: 'Reliance Industries', current_price: 2982.55, day_change: 17.45, day_change_pct: 0.59 },
    { symbol: 'HDFCBANK', company_name: 'HDFC Bank', current_price: 1665.00, day_change: -2.12, day_change_pct: -0.13 },
    { symbol: 'INFY', company_name: 'Infosys', current_price: 1833.55, day_change: -47.25, day_change_pct: -2.51 },
    { symbol: 'ICICIBANK', company_name: 'ICICI Bank', current_price: 1223.75, day_change: -10.85, day_change_pct: -0.88 },
    { symbol: 'SBIN', company_name: 'State Bank of India', current_price: 788.35, day_change: -17.80, day_change_pct: -2.21 },
    { symbol: 'BHARTIARTL', company_name: 'Bharti Airtel', current_price: 1680.40, day_change: 12.30, day_change_pct: 0.74 },
    { symbol: 'ITC', company_name: 'ITC Ltd', current_price: 492.15, day_change: 3.85, day_change_pct: 0.79 },
  ];

  const [marketStocks, setMarketStocks] = useState(defaultInitialStocks);

  // Institutional sandbox accounts for quick evaluation
  const demoAccounts = [
    { label: 'System Administrator', id: 'admin', pw: 'Admin@StockTrade2026', badge: 'ADMIN', desc: 'Platform oversight & risk controls' },
    { label: 'Institutional Broker Desk 1', id: 'broker_arun', pw: 'Broker@StockTrade2026', badge: 'BROKER', desc: 'Apex Securities — Client onboarding' },
    { label: 'Institutional Broker Desk 2', id: 'broker_priya', pw: 'Broker@StockTrade2026', badge: 'BROKER', desc: 'BlueChip Capital — Asset allocation' },
    { label: 'Retail Trader Account', id: 'investor_rahul', pw: 'Investor@StockTrade2026', badge: 'INVESTOR', desc: 'Active paper equities execution' },
    { label: 'Wealth Management Client', id: 'investor_sneha', pw: 'Investor@StockTrade2026', badge: 'INVESTOR', desc: 'Broker-managed equity portfolio' },
    { label: 'Direct Market Participant', id: 'investor_rohit', pw: 'Investor@StockTrade2026', badge: 'INVESTOR', desc: 'Self-directed paper equities' },
  ];

  // Fetch real authoritative live prices from backend market simulator
  useEffect(() => {
    let isMounted = true;
    const fetchLivePrices = async () => {
      try {
        const res = await fetch('/market/api/v1/market/prices');
        if (res.ok) {
          const json = await res.json();
          if (json.ok && Array.isArray(json.data) && isMounted) {
            const prioritySymbols = ['TCS', 'RELIANCE', 'HDFCBANK', 'INFY', 'ICICIBANK', 'SBIN', 'BHARTIARTL', 'ITC'];
            const mapped = [];
            for (const sym of prioritySymbols) {
              const found = json.data.find(s => s.symbol === sym);
              if (found) mapped.push(found);
            }
            if (mapped.length > 0) {
              setMarketStocks(mapped);
            }
          }
        }
      } catch (err) {
        console.warn('Real market prices fetch on login gateway:', err);
      }
    };

    fetchLivePrices();
    const interval = setInterval(fetchLivePrices, 3000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!identifier.trim() || !password) return;
    setError(null);
    setSubmitting(true);
    try {
      await login(identifier.trim(), password);
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setSubmitting(false);
    }
  };

  const selectDemoAccount = (acc) => {
    setIdentifier(acc.id);
    setPassword(acc.pw);
    setError(null);
    setShowDemoAccounts(false);
  };

  // Extract live TCS stock for graph tooltip
  const tcsStock = marketStocks.find(s => s.symbol === 'TCS') || defaultInitialStocks[0];
  const tcsPriceFormatted = Number(tcsStock.current_price || 4155.30).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
  const isTcsPositive = (tcsStock.day_change_pct || 0) >= 0;

  return (
    <div style={{
      minHeight: '100vh',
      width: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'radial-gradient(ellipse at 20% 30%, #0E2A2F 0%, #09151C 45%, #060E13 100%)',
      padding: '2rem 1.25rem',
      boxSizing: 'border-box',
      position: 'relative',
      overflowY: 'auto'
    }}>
      {/* Keyframe & Component Styles */}
      <style>{`
        /* Infinite moving marquee ticker animation */
        @keyframes continuousTicker {
          0% {
            transform: translate3d(0, 0, 0);
          }
          100% {
            transform: translate3d(-50%, 0, 0);
          }
        }
        .moving-ticker-rail {
          display: flex;
          align-items: center;
          gap: 2rem;
          width: max-content;
          animation: continuousTicker 26s linear infinite;
          will-change: transform;
        }
        .moving-ticker-rail:hover {
          animation-play-state: paused;
        }

        /* Pure opacity breathe for the stationary graph coordinate marker (ZERO movement/translation) */
        @keyframes stationaryAuraBreathe {
          0%, 100% { opacity: 0.2; }
          50% { opacity: 0.55; }
        }
        .stationary-marker-halo {
          animation: stationaryAuraBreathe 2.4s ease-in-out infinite;
        }

        /* Status pill pulsating green dot */
        @keyframes pulseBeacon {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.3); opacity: 0.7; }
        }
        .beacon-pulse {
          animation: pulseBeacon 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }

        .tactile-input {
          transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .tactile-btn {
          transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .tactile-btn:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 14px rgba(0, 168, 132, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
        }
        .tactile-btn:active:not(:disabled) {
          transform: translateY(0px);
        }
        .demo-chip {
          transition: all 0.15s ease;
        }
        .demo-chip:hover {
          background: #F1F5F9 !important;
          border-color: #0D9488 !important;
        }
        @media (max-width: 940px) {
          .terminal-split-card {
            grid-template-columns: 1fr !important;
            max-width: 460px !important;
          }
          .brand-dominant-pane {
            padding: 2rem 1.75rem !important;
            border-right: none !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
          }
          .auth-workspace-pane {
            padding: 2rem 1.75rem !important;
          }
        }
      `}</style>

      {/* Ambient background depth lights */}
      <div style={{
        position: 'absolute',
        top: '10%',
        left: '12%',
        width: '500px',
        height: '500px',
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(20, 184, 166, 0.14) 0%, transparent 65%)',
        filter: 'blur(70px)',
        pointerEvents: 'none'
      }} />

      <div style={{
        position: 'absolute',
        bottom: '10%',
        right: '15%',
        width: '450px',
        height: '450px',
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(0, 168, 132, 0.12) 0%, transparent 60%)',
        filter: 'blur(60px)',
        pointerEvents: 'none'
      }} />

      {/* The Master Split-Card Container (60/40 Asymmetrical Brand-Dominant Split) */}
      <div className="terminal-split-card" style={{
        position: 'relative',
        zIndex: 10,
        width: '100%',
        maxWidth: '1040px',
        display: 'grid',
        gridTemplateColumns: '1.25fr 1fr',
        background: 'rgba(9, 21, 28, 0.88)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(255, 255, 255, 0.09)',
        borderRadius: '20px',
        boxShadow: '0 30px 80px -15px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(255, 255, 255, 0.06)',
        overflow: 'hidden',
        boxSizing: 'border-box'
      }}>
        {/* ========================================================================= */}
        {/* LEFT PANE: BRAND DOMINANT TERMINAL EXPERIENCE (60%)                       */}
        {/* ========================================================================= */}
        <div className="brand-dominant-pane" style={{
          padding: '2.75rem 2.5rem',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          borderRight: '1px solid rgba(255, 255, 255, 0.08)',
          position: 'relative',
          overflow: 'hidden',
          background: 'linear-gradient(180deg, rgba(14, 42, 47, 0.4) 0%, rgba(9, 21, 28, 0.75) 100%)',
          boxSizing: 'border-box'
        }}>
          {/* Subtle frosted glass backdrop grid */}
          <div style={{
            position: 'absolute',
            inset: 0,
            backgroundImage: 'radial-gradient(rgba(20, 184, 166, 0.12) 1px, transparent 1px)',
            backgroundSize: '24px 24px',
            opacity: 0.5,
            pointerEvents: 'none'
          }} />

          {/* Top Brand & Status Pill */}
          <div style={{ position: 'relative', zIndex: 2 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                <BullLogo size={32} />
                <span style={{
                  fontSize: '1.1rem',
                  fontWeight: 800,
                  color: '#FFFFFF',
                  letterSpacing: '-0.03em'
                }}>
                  STOCKTRADE
                </span>
              </div>

              {/* Glowing Status Pill */}
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.45rem',
                padding: '0.25rem 0.7rem',
                borderRadius: '9999px',
                background: 'rgba(20, 184, 166, 0.08)',
                border: '1px solid rgba(20, 184, 166, 0.22)',
                backdropFilter: 'blur(8px)',
                fontSize: '0.725rem',
                fontWeight: 600,
                color: '#2DD4BF',
                letterSpacing: '0.02em'
              }}>
                <span className="beacon-pulse" style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: '#14B8A6',
                  boxShadow: '0 0 8px #14B8A6'
                }} />
                Matching Engine Active
              </div>
            </div>

            {/* Headline with subtle gradient text effect */}
            <div style={{ marginTop: '2.5rem' }}>
              <h1 style={{
                fontSize: '2.2rem',
                fontWeight: 800,
                letterSpacing: '-0.035em',
                lineHeight: 1.15,
                background: 'linear-gradient(180deg, #FFFFFF 25%, #CBD5E1 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                marginBottom: '0.75rem'
              }}>
                Simulated Market Terminal
              </h1>
              <p style={{
                fontSize: '0.9rem',
                color: '#94A3B8',
                lineHeight: 1.6,
                fontWeight: 400,
                maxWidth: '430px'
              }}>
                Institutional-grade paper trading simulation powered by deterministic order execution, ACID settlement, and real-time market depth.
              </p>
            </div>
          </div>

          {/* Abstract Ultra-Smooth Line Chart (Rock-Solid Coordinates, Fixed Apex Marker) */}
          <div style={{ position: 'relative', zIndex: 1, margin: '2rem 0 1.5rem 0' }}>
            <svg
              viewBox="0 0 460 110"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              style={{ width: '100%', height: 'auto', overflow: 'visible' }}
            >
              <defs>
                <linearGradient id="chartStrokeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#0D9488" stopOpacity="0.3" />
                  <stop offset="40%" stopColor="#14B8A6" stopOpacity="0.85" />
                  <stop offset="85%" stopColor="#2DD4BF" stopOpacity="1" />
                  <stop offset="100%" stopColor="#00A884" stopOpacity="0.9" />
                </linearGradient>

                <linearGradient id="chartFillGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#14B8A6" stopOpacity="0.16" />
                  <stop offset="100%" stopColor="#14B8A6" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Subtle background horizontal guidelines */}
              <line x1="0" y1="25" x2="460" y2="25" stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" />
              <line x1="0" y1="65" x2="460" y2="65" stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" />

              {/* Area fill under curve */}
              <path
                d="M 0,82 C 45,80 80,92 120,68 C 160,42 195,78 235,48 C 275,18 310,54 350,28 C 390,4 425,30 456,15 L 456,110 L 0,110 Z"
                fill="url(#chartFillGrad)"
              />

              {/* The Smooth Heartbeat Line ending precisely at apex (456, 15) */}
              <path
                d="M 0,82 C 45,80 80,92 120,68 C 160,42 195,78 235,48 C 275,18 310,54 350,28 C 390,4 425,30 456,15"
                stroke="url(#chartStrokeGrad)"
                strokeWidth="2.5"
                strokeLinecap="round"
              />

              {/* Stationary Apex Anchor Marker (FIXED: Zero transform scaling, anchored firmly at cx=456 cy=15) */}
              <circle
                cx="456"
                cy="15"
                r="7.5"
                fill="#14B8A6"
                className="stationary-marker-halo"
              />
              <circle
                cx="456"
                cy="15"
                r="3.5"
                fill="#2DD4BF"
              />

              {/* Real-time Tooltip anchored above the stationary apex marker */}
              <g transform="translate(365, 0)">
                <rect
                  width="92"
                  height="22"
                  rx="5"
                  fill="rgba(9, 21, 28, 0.95)"
                  stroke="rgba(45, 212, 191, 0.4)"
                  strokeWidth="1"
                />
                <text
                  x="46"
                  y="15"
                  fill={isTcsPositive ? '#34D399' : '#F87171'}
                  fontSize="10"
                  fontWeight="700"
                  textAnchor="middle"
                  letterSpacing="0.02em"
                >
                  TCS ₹{tcsPriceFormatted} {isTcsPositive ? '▲' : '▼'}
                </text>
              </g>
            </svg>
          </div>

          {/* Bottom Moving Marquee Panel (Real authoritative prices from backend simulation) */}
          <div style={{ position: 'relative', zIndex: 2 }}>
            <div style={{
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.07)',
              borderRadius: '9999px',
              backdropFilter: 'blur(12px)',
              padding: '0.45rem 0',
              overflow: 'hidden',
              position: 'relative',
              width: '100%',
              maskImage: 'linear-gradient(to right, transparent, black 5%, black 95%, transparent)',
              WebkitMaskImage: 'linear-gradient(to right, transparent, black 5%, black 95%, transparent)'
            }}>
              {/* Duplicated list inside moving rail for seamless, infinite looping marquee */}
              <div className="moving-ticker-rail">
                {[...marketStocks, ...marketStocks].map((stock, idx) => {
                  const isPos = (stock.day_change_pct || 0) >= 0;
                  const priceStr = Number(stock.current_price || 0).toLocaleString('en-IN', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                  });
                  const changeStr = `${isPos ? '+' : ''}${(stock.day_change_pct || 0).toFixed(2)}%`;

                  return (
                    <div
                      key={`${stock.symbol}-${idx}`}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.45rem',
                        fontSize: '0.75rem',
                        whiteSpace: 'nowrap',
                        userSelect: 'none'
                      }}
                    >
                      <span style={{ fontWeight: 700, color: '#FFFFFF', letterSpacing: '0.02em' }}>
                        {stock.symbol}
                      </span>
                      <span style={{ color: '#94A3B8', fontVariantNumeric: 'tabular-nums' }}>
                        ₹{priceStr}
                      </span>
                      <span style={{
                        color: isPos ? '#34D399' : '#F87171',
                        fontWeight: 600,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.15rem',
                        background: isPos ? 'rgba(52, 211, 153, 0.12)' : 'rgba(248, 113, 113, 0.12)',
                        padding: '0.1rem 0.35rem',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        fontVariantNumeric: 'tabular-nums'
                      }}>
                        {isPos ? '▲' : '▼'} {changeStr}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.725rem',
              color: '#64748B',
              marginTop: '0.85rem',
              paddingLeft: '0.25rem'
            }}>
              <span>Enterprise-grade security</span>
              <span>•</span>
              <span>Real-time execution</span>
              <span>•</span>
              <span>50 ticks/sec</span>
            </div>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* RIGHT PANE: CRISP WHITE FLOATING AUTH WORKSPACE (40%)                     */}
        {/* ========================================================================= */}
        <div className="auth-workspace-pane" style={{
          background: '#FFFFFF',
          padding: '2.75rem 2.5rem',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          boxSizing: 'border-box',
          position: 'relative'
        }}>
          {/* Header */}
          <div style={{ marginBottom: '1.75rem' }}>
            <h2 style={{
              fontSize: '1.5rem',
              fontWeight: 700,
              color: '#0F172A',
              letterSpacing: '-0.025em',
              lineHeight: 1.2
            }}>
              Sign in to your terminal
            </h2>
            <p style={{
              fontSize: '0.875rem',
              color: '#64748B',
              marginTop: '0.35rem',
              lineHeight: 1.5
            }}>
              Welcome back. Enter your credentials to access the simulated exchange.
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            {/* Field 1: Email or Username */}
            <div style={{ marginBottom: '1.15rem' }}>
              <label style={{
                display: 'block',
                fontSize: '0.8125rem',
                fontWeight: 500,
                color: '#475569',
                marginBottom: '0.4rem',
                letterSpacing: '0.01em'
              }}>
                Email or username
              </label>

              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                <div style={{
                  position: 'absolute',
                  left: '0.85rem',
                  color: focusedField === 'user' ? '#0D9488' : '#94A3B8',
                  display: 'flex',
                  transition: 'color 0.15s ease'
                }}>
                  <User size={16} strokeWidth={1.6} />
                </div>

                <input
                  type="text"
                  required
                  placeholder="Enter your username or email"
                  value={identifier}
                  onChange={e => setIdentifier(e.target.value)}
                  onFocus={() => setFocusedField('user')}
                  onBlur={() => setFocusedField(null)}
                  className="tactile-input"
                  style={{
                    width: '100%',
                    padding: '0.725rem 0.85rem 0.725rem 2.45rem',
                    background: focusedField === 'user' ? '#FFFFFF' : '#F8FAFC',
                    border: focusedField === 'user' ? '1px solid #0D9488' : '1px solid #E2E8F0',
                    borderRadius: '8px',
                    boxShadow: focusedField === 'user'
                      ? '0 0 0 3px rgba(13, 148, 136, 0.15), inset 0 1px 2px rgba(0, 0, 0, 0.02)'
                      : 'inset 0 1px 2px rgba(0, 0, 0, 0.04)',
                    fontSize: '0.875rem',
                    color: '#0F172A',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
            </div>

            {/* Field 2: Password with Show/Hide toggle */}
            <div style={{ marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <label style={{
                  fontSize: '0.8125rem',
                  fontWeight: 500,
                  color: '#475569',
                  letterSpacing: '0.01em'
                }}>
                  Password
                </label>
              </div>

              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                <div style={{
                  position: 'absolute',
                  left: '0.85rem',
                  color: focusedField === 'pw' ? '#0D9488' : '#94A3B8',
                  display: 'flex',
                  transition: 'color 0.15s ease'
                }}>
                  <Lock size={16} strokeWidth={1.6} />
                </div>

                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  placeholder="••••••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  onFocus={() => setFocusedField('pw')}
                  onBlur={() => setFocusedField(null)}
                  className="tactile-input"
                  style={{
                    width: '100%',
                    padding: '0.725rem 2.45rem 0.725rem 2.45rem',
                    background: focusedField === 'pw' ? '#FFFFFF' : '#F8FAFC',
                    border: focusedField === 'pw' ? '1px solid #0D9488' : '1px solid #E2E8F0',
                    borderRadius: '8px',
                    boxShadow: focusedField === 'pw'
                      ? '0 0 0 3px rgba(13, 148, 136, 0.15), inset 0 1px 2px rgba(0, 0, 0, 0.02)'
                      : 'inset 0 1px 2px rgba(0, 0, 0, 0.04)',
                    fontSize: '0.875rem',
                    color: '#0F172A',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />

                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '0.75rem',
                    background: 'transparent',
                    border: 'none',
                    color: '#94A3B8',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    padding: '0.2rem'
                  }}
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={16} strokeWidth={1.6} /> : <Eye size={16} strokeWidth={1.6} />}
                </button>
              </div>
            </div>

            {/* Error Notification */}
            {error && (
              <div style={{
                background: '#FEF2F2',
                border: '1px solid #FEE2E2',
                color: '#B91C1C',
                padding: '0.6rem 0.8rem',
                borderRadius: '8px',
                fontSize: '0.8125rem',
                marginBottom: '1.15rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.45rem'
              }}>
                <AlertCircle size={15} strokeWidth={1.75} />
                <span>{error}</span>
              </div>
            )}

            {/* Tactile Primary Button with Inner Highlight */}
            <button
              type="submit"
              disabled={submitting}
              className="tactile-btn"
              style={{
                width: '100%',
                padding: '0.75rem',
                fontSize: '0.9rem',
                fontWeight: 600,
                color: '#FFFFFF',
                background: 'linear-gradient(180deg, #00A884 0%, #008F6F 100%)',
                border: '1px solid #007D61',
                borderRadius: '8px',
                boxShadow: '0 1px 2px rgba(0, 0, 0, 0.08), 0 4px 12px rgba(0, 168, 132, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.22)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                cursor: submitting ? 'not-allowed' : 'pointer'
              }}
            >
              {submitting ? (
                <>
                  <span style={{
                    display: 'inline-block',
                    width: '13px',
                    height: '13px',
                    border: '2px solid #FFFFFF',
                    borderTopColor: 'transparent',
                    borderRadius: '50%',
                    animation: 'spin 0.6s linear infinite'
                  }} />
                  <span>Connecting to terminal...</span>
                </>
              ) : (
                <>
                  <span>Launch Workspace</span>
                  <ArrowRight size={16} strokeWidth={1.75} />
                </>
              )}
            </button>
          </form>

          {/* Minimalist Demo Account Trigger (Clean & Unobtrusive) */}
          <div style={{ marginTop: '1.25rem', textAlign: 'center' }}>
            <button
              type="button"
              onClick={() => setShowDemoAccounts(!showDemoAccounts)}
              style={{
                background: 'none',
                border: 'none',
                color: '#0D9488',
                fontSize: '0.8125rem',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.25rem 0.5rem',
                borderRadius: '4px',
                transition: 'background 0.15s ease'
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#F0FDFA'}
              onMouseLeave={e => e.currentTarget.style.background = 'none'}
            >
              <span>Login as a Demo Account</span>
              <ChevronDown
                size={14}
                strokeWidth={1.75}
                style={{
                  transform: showDemoAccounts ? 'rotate(180deg)' : 'none',
                  transition: 'transform 0.2s cubic-bezier(0.16, 1, 0.3, 1)'
                }}
              />
            </button>
          </div>

          {/* Expandable Demo Role Sheet */}
          {showDemoAccounts && (
            <div style={{
              marginTop: '0.75rem',
              padding: '0.75rem',
              background: '#F8FAFC',
              border: '1px solid #E2E8F0',
              borderRadius: '8px',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.4rem',
              animation: 'fadeIn 0.2s ease-out'
            }}>
              <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.2rem' }}>
                Select a simulated profile to auto-fill
              </div>
              {demoAccounts.map(acc => (
                <div
                  key={acc.id}
                  onClick={() => selectDemoAccount(acc)}
                  className="demo-chip"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.45rem 0.6rem',
                    background: '#FFFFFF',
                    border: '1px solid #E2E8F0',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '0.775rem'
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontWeight: 600, color: '#0F172A' }}>{acc.label}</span>
                    <span style={{ fontSize: '0.675rem', color: '#64748B' }}>{acc.desc}</span>
                  </div>
                  <span style={{
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    padding: '0.15rem 0.4rem',
                    borderRadius: '4px',
                    background: '#E2E8F0',
                    color: '#475569'
                  }}>
                    {acc.badge}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Institutional Trust Footnote */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.4rem',
            fontSize: '0.725rem',
            color: '#94A3B8',
            marginTop: '1.75rem',
            paddingTop: '1.25rem',
            borderTop: '1px solid #F1F5F9'
          }}>
            <Shield size={14} strokeWidth={1.5} color="#0D9488" />
            <span>Enterprise-grade security • Real-time execution</span>
          </div>
        </div>
      </div>
    </div>
  );
}
