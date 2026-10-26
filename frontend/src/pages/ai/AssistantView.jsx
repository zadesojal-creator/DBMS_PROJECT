import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Terminal,
  CheckCircle2,
  AlertTriangle,
  Send,
  History,
  Clock,
  RefreshCw,
  Copy,
  Check,
  Code,
  Play,
  RotateCcw,
  BookOpen,
  ShieldCheck,
  ExternalLink
} from 'lucide-react';
import { api } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import SqlResultViewer from '../../components/SqlResultViewer';

export default function AssistantView() {
  const { user } = useAuth();
  const [activeMode, setActiveMode] = useState('ai'); // 'ai' | 'manual'

  // AI Assistant state
  const [prompt, setPrompt] = useState('');
  const [aiSubmitting, setAiSubmitting] = useState(false);
  const [aiResponse, setAiResponse] = useState(null);
  const [aiError, setAiError] = useState(null);
  const [copiedSql, setCopiedSql] = useState(false);

  // Manual SQL state
  const [manualSql, setManualSql] = useState('');
  const [manualSubmitting, setManualSubmitting] = useState(false);
  const [manualResponse, setManualResponse] = useState(null);
  const [manualError, setManualError] = useState(null);
  const [schemaInfo, setSchemaInfo] = useState(null);

  // History state
  const [showHistory, setShowHistory] = useState(false);
  const [historyItems, setHistoryItems] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Load allowed views & schema specifications for Manual SQL mode
  useEffect(() => {
    api.ai.getSchema()
      .then(res => {
        if (res.ok && res.data) {
          setSchemaInfo(res.data);
          // Set initial default query for manual SQL if empty
          if (!manualSql && res.data.allowed_views?.length > 0) {
            setManualSql(res.data.allowed_views[0].sample || `SELECT * FROM ${res.data.allowed_views[0].view} LIMIT 10;`);
          }
        }
      })
      .catch(console.error);
  }, []);

  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await api.ai.getHistory();
      if (res.ok) {
        setHistoryItems(res.data || []);
      }
    } catch {
      // Non-blocking history fetch
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (showHistory) {
      fetchHistory();
    }
  }, [showHistory]);

  const samplePrompts = {
    INVESTOR: [
      "What are my open stock holdings and their current values?",
      "Show my latest executed transactions with brokerage fees",
      "Which technology sector stocks have gained the most today?",
      "What is my overall portfolio return percentage?"
    ],
    BROKER: [
      "Show all active clients assigned to me with their balances",
      "What is the total commission I have earned across all trades?",
      "List transactions executed by my assigned clients today",
      "Which clients have the largest unrealised portfolio gains?"
    ],
    ADMIN: [
      "Show accounts with failed login attempts or lockouts",
      "Show recent failed login security events with timestamps",
      "Show total platform trading volume and collected fees",
      "List listed securities grouped by sector with average prices"
    ]
  };

  const currentSamples = samplePrompts[user?.role] || samplePrompts.INVESTOR;

  // Handle AI question submission
  const handleAiSubmit = async (queryText) => {
    const q = queryText || prompt;
    if (!q.trim()) return;
    setAiSubmitting(true);
    setAiError(null);
    setAiResponse(null);

    try {
      const res = await api.ai.query(q);
      if (res.ok) {
        setAiResponse(res.data);
      } else {
        setAiError(res.error?.message || 'AI Assistant query failed');
      }
    } catch (err) {
      setAiError(err.message || 'AI Assistant service unavailable');
    } finally {
      setAiSubmitting(false);
    }
  };

  // Handle Manual SQL execution
  const handleManualSqlSubmit = async () => {
    if (!manualSql.trim()) return;
    setManualSubmitting(true);
    setManualError(null);
    setManualResponse(null);

    try {
      const res = await api.ai.executeSql(manualSql.trim(), 'Manual SQL Execution');
      if (res.ok) {
        setManualResponse(res.data);
      } else {
        setManualError(res.error?.message || 'Query execution rejected');
      }
    } catch (err) {
      setManualError(err.message || 'Query execution failed');
    } finally {
      setManualSubmitting(false);
    }
  };

  // Copy SQL to clipboard
  const handleCopySql = (sqlText) => {
    if (!sqlText) return;
    navigator.clipboard.writeText(sqlText);
    setCopiedSql(true);
    setTimeout(() => setCopiedSql(false), 2000);
  };

  // Transfer generated SQL to Manual SQL mode
  const handleOpenInManualSql = (sqlText) => {
    if (!sqlText) return;
    setManualSql(sqlText);
    setActiveMode('manual');
    setManualResponse(null);
    setManualError(null);
  };

  // Handle Tab key in SQL textarea
  const handleKeyDown = (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = e.target.selectionStart;
      const end = e.target.selectionEnd;
      const newVal = manualSql.substring(0, start) + '  ' + manualSql.substring(end);
      setManualSql(newVal);
      setTimeout(() => {
        e.target.selectionStart = e.target.selectionEnd = start + 2;
      }, 0);
    } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleManualSqlSubmit();
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Banner & Mode Switcher */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
            <Sparkles size={22} color="var(--teal)" />
            <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--navy)' }}>
              AI SQL Assistant & Query Console
            </h2>
          </div>
          <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
            Natural language database exploration and custom read-only SQL execution secured by sqlglot AST allowlists and role tenancy scoping
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          {/* Mode Pill Toggle */}
          <div style={{ display: 'inline-flex', background: '#E2E8F0', padding: '0.2rem', borderRadius: 'var(--radius-md)' }}>
            <button
              type="button"
              className={`btn btn-sm ${activeMode === 'ai' ? 'btn-primary' : ''}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                border: 'none',
                background: activeMode === 'ai' ? 'var(--primary)' : 'transparent',
                color: activeMode === 'ai' ? '#FFFFFF' : 'var(--navy)',
                fontSize: '0.8rem',
                fontWeight: 600,
                padding: '0.35rem 0.75rem'
              }}
              onClick={() => setActiveMode('ai')}
            >
              <Sparkles size={14} /> AI Assistant
            </button>
            <button
              type="button"
              className={`btn btn-sm ${activeMode === 'manual' ? 'btn-primary' : ''}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                border: 'none',
                background: activeMode === 'manual' ? 'var(--primary)' : 'transparent',
                color: activeMode === 'manual' ? '#FFFFFF' : 'var(--navy)',
                fontSize: '0.8rem',
                fontWeight: 600,
                padding: '0.35rem 0.75rem'
              }}
              onClick={() => setActiveMode('manual')}
            >
              <Code size={14} /> Manual SQL
            </button>
          </div>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setShowHistory(!showHistory)}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem' }}
          >
            <History size={14} />
            {showHistory ? 'Hide History' : 'Query History'}
          </button>
        </div>
      </div>

      {/* Query History Drawer */}
      {showHistory && (
        <div className="card" style={{ padding: '1rem', borderLeft: '4px solid var(--navy)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Clock size={16} color="var(--navy)" />
              <strong style={{ fontSize: '0.9rem', color: 'var(--navy)' }}>Recent Audit Query Records</strong>
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={fetchHistory}
              disabled={loadingHistory}
              style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
            >
              <RefreshCw size={12} className={loadingHistory ? 'spin' : ''} /> Refresh
            </button>
          </div>

          {loadingHistory ? (
            <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--muted)', fontSize: '0.85rem' }}>
              Loading audit logs...
            </div>
          ) : historyItems.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--muted)', fontSize: '0.85rem' }}>
              No past query records found for your account.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '240px', overflowY: 'auto' }}>
              {historyItems.map((item) => (
                <div
                  key={item.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0.5rem 0.75rem',
                    background: '#F8FAFC',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.8rem'
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem', maxWidth: '70%' }}>
                    <span style={{ fontWeight: 600, color: 'var(--navy)' }}>{item.prompt}</span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>
                      {item.created_at} &bull; {item.duration_ms}ms &bull; {item.row_count} rows &bull; Provider: <code>{item.provider || 'System'}</code>
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className={`badge ${item.validation_status === 'VALID' ? 'badge-gain' : 'badge-loss'}`} style={{ fontSize: '0.65rem' }}>
                      {item.validation_status}
                    </span>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
                      onClick={() => {
                        if (item.generated_sql) {
                          setManualSql(item.generated_sql);
                          setActiveMode('manual');
                        } else {
                          setPrompt(item.prompt);
                          setActiveMode('ai');
                        }
                      }}
                      title="Load into Editor"
                    >
                      Load
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODE 1: AI ASSISTANT                                                      */}
      {/* ========================================================================= */}
      {activeMode === 'ai' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Natural Language Input Card */}
          <div className="card" style={{ padding: '1.25rem' }}>
            <form onSubmit={(e) => { e.preventDefault(); handleAiSubmit(); }}>
              <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem' }}>
                <input
                  type="text"
                  placeholder={`Ask a question in plain English about your ${user?.role === 'INVESTOR' ? 'portfolio, market or trades' : user?.role === 'BROKER' ? 'clients and commissions' : 'system metrics'}...`}
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  style={{
                    flex: 1,
                    padding: '0.65rem 0.85rem',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.9rem',
                    outline: 'none'
                  }}
                />
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={aiSubmitting || !prompt.trim()}
                  style={{ padding: '0.65rem 1.25rem' }}
                >
                  {aiSubmitting ? 'Analyzing...' : (
                    <>
                      <Send size={15} /> Ask AI
                    </>
                  )}
                </button>
              </div>
            </form>

            {/* Quick prompts */}
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.5rem' }}>
                Preset Prompts
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {currentSamples.map((sample, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}
                    onClick={() => {
                      setPrompt(sample);
                      handleAiSubmit(sample);
                    }}
                  >
                    {sample}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* AI Error */}
          {aiError && (
            <div className="card" style={{ background: 'var(--loss-bg)', border: '1px solid #FCA5A5' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--loss)', fontWeight: 600 }}>
                <AlertTriangle size={18} />
                <span>AI Query Error</span>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--loss)', marginTop: '0.35rem' }}>
                {aiError}
              </p>
            </div>
          )}

          {/* AI Output View */}
          {aiResponse && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Grounded Direct Answer & Analysis Card */}
              <div className="card" style={{ borderLeft: '4px solid var(--teal)', padding: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Sparkles size={16} color="var(--teal)" />
                    <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--teal)', fontWeight: 700, letterSpacing: '0.04em' }}>
                      Assistant Direct Answer
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                    {aiResponse.key_metrics?.map((m, idx) => (
                      <span key={idx} className="badge badge-neutral" style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}>
                        {m.label}: <strong style={{ color: 'var(--navy)' }}>{m.value}</strong>
                      </span>
                    ))}
                    <span className="badge badge-gain" style={{ fontSize: '0.75rem' }}>
                      {aiResponse.duration_ms || 0}ms
                    </span>
                  </div>
                </div>

                {/* Direct Executive Answer */}
                <p style={{ fontSize: '1.05rem', color: 'var(--navy)', lineHeight: 1.5, fontWeight: 600, margin: '0.35rem 0 0.75rem 0' }}>
                  {aiResponse.summary || 'Query executed successfully with verified database rows.'}
                </p>

                {/* Business Logic & Query Explanation */}
                {aiResponse.explanation && (
                  <div style={{
                    marginTop: '0.5rem',
                    padding: '0.65rem 0.85rem',
                    background: '#F0FDFA',
                    border: '1px solid #CCFBF1',
                    borderRadius: 'var(--radius-sm)',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.5rem'
                  }}>
                    <BookOpen size={15} color="#0D9488" style={{ marginTop: '0.15rem', flexShrink: 0 }} />
                    <div style={{ fontSize: '0.825rem', color: '#115E59', lineHeight: 1.5 }}>
                      <strong>Query & Business Explanation:</strong> {aiResponse.explanation}
                    </div>
                  </div>
                )}
              </div>

              {/* Generated SQL Code Box with Actions */}
              <div className="card" style={{ background: '#0F172A', color: '#E2E8F0', padding: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: '#94A3B8' }}>
                    <Terminal size={15} />
                    <span>Generated Parameterized SQL (MySQL Dialect)</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="badge badge-gain" style={{ fontSize: '0.7rem' }}>
                      <CheckCircle2 size={12} /> AST VALIDATED
                    </span>
                    <span style={{ fontSize: '0.7rem', color: '#94A3B8' }}>
                      Model: <strong>{aiResponse.provider_used || 'Failover Chain'}</strong>
                    </span>

                    {/* Copy SQL Button */}
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', background: 'rgba(255,255,255,0.1)', color: '#FFFFFF', border: 'none' }}
                      onClick={() => handleCopySql(aiResponse.generated_sql)}
                      title="Copy SQL to Clipboard"
                    >
                      {copiedSql ? <Check size={13} color="var(--gain)" /> : <Copy size={13} />}
                      {copiedSql ? 'Copied' : 'Copy SQL'}
                    </button>

                    {/* Open in Manual SQL Button */}
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                      onClick={() => handleOpenInManualSql(aiResponse.generated_sql)}
                      title="Open query in Manual SQL console"
                    >
                      <ExternalLink size={13} /> Open in Manual SQL
                    </button>
                  </div>
                </div>

                <pre style={{
                  margin: 0,
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                  color: '#38BDF8',
                  overflowX: 'auto',
                  padding: '0.75rem',
                  background: '#020617',
                  borderRadius: 'var(--radius-sm)'
                }}>
                  {aiResponse.generated_sql}
                </pre>
              </div>

              {/* Results Table & Chart.js Visualizer */}
              <SqlResultViewer
                columns={aiResponse.columns || []}
                rows={aiResponse.results || aiResponse.rows || []}
                durationMs={aiResponse.duration_ms || 0}
                rowCount={aiResponse.row_count || (aiResponse.results || aiResponse.rows || []).length}
              />
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODE 2: MANUAL SQL CONSOLE                                                */}
      {/* ========================================================================= */}
      {activeMode === 'manual' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* SQL Editor Card */}
          <div className="card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Terminal size={18} color="var(--navy)" />
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--navy)' }}>
                  Interactive SQL Editor
                </h3>
                <span className="badge badge-secondary" style={{ fontSize: '0.75rem' }}>
                  Role: {user?.role}
                </span>
                <span className="badge badge-gain" style={{ fontSize: '0.75rem' }}>
                  <ShieldCheck size={12} /> READ-ONLY ENFORCED
                </span>
              </div>

              <div style={{ display: 'flex', gap: '0.4rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '0.8rem' }}
                  onClick={() => setManualSql('')}
                  title="Clear editor"
                >
                  <RotateCcw size={13} /> Clear
                </button>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  style={{ fontSize: '0.8rem', padding: '0.35rem 0.85rem' }}
                  onClick={handleManualSqlSubmit}
                  disabled={manualSubmitting || !manualSql.trim()}
                  title="Execute Query (Ctrl + Enter)"
                >
                  {manualSubmitting ? 'Executing...' : (
                    <>
                      <Play size={13} fill="#FFFFFF" /> Run Query
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Allowed Views Reference Pills */}
            {schemaInfo?.allowed_views && (
              <div style={{ marginBottom: '0.75rem' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--muted)', marginBottom: '0.35rem' }}>
                  Authorized Views for {user?.role} (click to insert sample query):
                </div>
                <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                  {schemaInfo.allowed_views.map(v => (
                    <button
                      key={v.view}
                      type="button"
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: '0.75rem', padding: '0.2rem 0.55rem', fontFamily: 'monospace' }}
                      onClick={() => setManualSql(v.sample || `SELECT * FROM ${v.view} LIMIT 10;`)}
                      title={v.description}
                    >
                      {v.view}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Code Textarea Editor */}
            <div style={{ position: 'relative' }}>
              <textarea
                value={manualSql}
                onChange={e => setManualSql(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Write your read-only SELECT query here... (e.g. SELECT * FROM v_market_latest ORDER BY day_change_pct DESC LIMIT 10;)"
                rows={7}
                style={{
                  width: '100%',
                  boxSizing: 'border-box',
                  padding: '0.85rem',
                  fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                  fontSize: '0.875rem',
                  background: '#0F172A',
                  color: '#38BDF8',
                  border: '1px solid #334155',
                  borderRadius: 'var(--radius-md)',
                  outline: 'none',
                  lineHeight: '1.5',
                  resize: 'vertical'
                }}
              />
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '0.75rem',
                color: 'var(--muted)',
                marginTop: '0.35rem'
              }}>
                <span>Shortcut: Press <code>Ctrl + Enter</code> to run query</span>
                <span>Enforced limit: Max 500 rows &bull; Timeout: 5000ms</span>
              </div>
            </div>
          </div>

          {/* Manual SQL Validation / Execution Error */}
          {manualError && (
            <div className="card" style={{ background: 'var(--loss-bg)', border: '1px solid #FCA5A5' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--loss)', fontWeight: 600 }}>
                <AlertTriangle size={18} />
                <span>Query Security or Syntax Error</span>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--loss)', marginTop: '0.35rem', fontFamily: 'monospace' }}>
                {manualError}
              </p>
              <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.5rem' }}>
                Only SELECT queries on authorized views are permitted. Mutations (INSERT, UPDATE, DELETE), DDL (DROP, ALTER), stacked queries, and unauthorized tables are rejected on the backend.
              </div>
            </div>
          )}

          {/* Manual SQL Result View */}
          {manualResponse && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Executive Summary Card */}
              <div className="card" style={{ borderLeft: '4px solid var(--primary)', padding: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Code size={16} color="var(--primary)" />
                    <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--primary)', fontWeight: 700, letterSpacing: '0.04em' }}>
                      Query Execution Summary
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                    {manualResponse.key_metrics?.map((m, idx) => (
                      <span key={idx} className="badge badge-neutral" style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}>
                        {m.label}: <strong style={{ color: 'var(--navy)' }}>{m.value}</strong>
                      </span>
                    ))}
                    <span className="badge badge-gain" style={{ fontSize: '0.75rem' }}>
                      {manualResponse.duration_ms || 0}ms
                    </span>
                  </div>
                </div>

                <p style={{ fontSize: '1.05rem', color: 'var(--navy)', lineHeight: 1.5, fontWeight: 600, margin: '0.35rem 0 0.75rem 0' }}>
                  {manualResponse.summary || 'Query executed successfully with verified database rows.'}
                </p>

                {manualResponse.explanation && (
                  <div style={{
                    marginTop: '0.5rem',
                    padding: '0.65rem 0.85rem',
                    background: '#EFF6FF',
                    border: '1px solid #DBEAFE',
                    borderRadius: 'var(--radius-sm)',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.5rem'
                  }}>
                    <BookOpen size={15} color="#2563EB" style={{ marginTop: '0.15rem', flexShrink: 0 }} />
                    <div style={{ fontSize: '0.825rem', color: '#1E40AF', lineHeight: 1.5 }}>
                      <strong>Execution & Security Context:</strong> {manualResponse.explanation}
                    </div>
                  </div>
                )}
              </div>

              <SqlResultViewer
                columns={manualResponse.columns || []}
                rows={manualResponse.rows || manualResponse.results || []}
                durationMs={manualResponse.duration_ms || 0}
                rowCount={manualResponse.row_count || (manualResponse.rows || manualResponse.results || []).length}
              />
            </div>
          )}
        </div>
      )}

      {/* Security Architecture Reference */}
      <div className="card" style={{ background: '#F8FAFC' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
          <ShieldCheck size={16} color="var(--teal)" />
          <strong style={{ fontSize: '0.85rem', color: 'var(--navy)' }}>Unified 5-Layer Shared Security & Tenancy Guarantee</strong>
        </div>
        <p style={{ fontSize: '0.8rem', color: 'var(--muted)', lineHeight: 1.5 }}>
          Both <strong>AI Assistant</strong> and <strong>Manual SQL</strong> execute queries through the identical safe backend pipeline:<br />
          1. <strong>AST Syntax & Allowlist Parsing:</strong> Parses SQL via <code>sqlglot</code> to enforce read-only SELECT statements, single statements, and approved functions.<br />
          2. <strong>Role View Allowlist:</strong> Validates that referenced views are strictly authorized for your current role (<code>INVESTOR</code>, <code>BROKER</code>, or <code>ADMIN</code>).<br />
          3. <strong>Mathematical Row-Level Tenancy Scoping:</strong> Automatically wraps private tenant views into subqueries <code>(SELECT * FROM view WHERE user_id = :auth_user_id)</code>, strictly preventing cross-investor or cross-broker data leakage.<br />
          4. <strong>Least-Privilege Execution:</strong> Executed under dedicated MySQL user <code>stocktrade_ai_ro</code> with <code>READ ONLY</code> transaction and 5-second timeout.<br />
          5. <strong>Tamper-Resistant Audit Trail:</strong> Every query attempt (both permitted and rejected) is permanently logged in <code>AI_Query_History</code>.
        </p>
      </div>
    </div>
  );
}
