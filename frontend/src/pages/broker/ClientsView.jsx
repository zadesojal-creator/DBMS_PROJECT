import React, { useState, useEffect } from 'react';
import { UserPlus, UserCheck, ShieldAlert, RefreshCw, Eye, XOctagon } from 'lucide-react';
import { api } from '../../api/client';
import { formatINR, formatDateTime } from '../../utils/formatters';
import OnboardClientModal from '../../components/OnboardClientModal';

export default function ClientsView() {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showOnboardModal, setShowOnboardModal] = useState(false);
  const [selectedClientProfile, setSelectedClientProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadClients = async () => {
    try {
      const res = await api.broker.getClients();
      if (res.ok) {
        setClients(res.data || []);
      }
    } catch (err) {
      console.error('Failed to load broker clients', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClients();
  }, []);

  const handleViewProfile = async (investorId) => {
    setProfileLoading(true);
    setError(null);
    try {
      const res = await api.broker.getClientProfile(investorId);
      if (res.ok) {
        setSelectedClientProfile(res.data);
      } else {
        setError(res.error?.message || 'Could not load client profile');
      }
    } catch (err) {
      setError(err.message || 'Tenant isolation: Access denied');
    } finally {
      setProfileLoading(false);
    }
  };

  const handleEndAssignment = async (investorId, username) => {
    if (!window.confirm(`Are you sure you want to end broker assignment for ${username}?`)) return;
    try {
      const res = await api.broker.endAssignment(investorId);
      if (res.ok) {
        loadClients();
        if (selectedClientProfile?.investor_id === investorId) {
          setSelectedClientProfile(null);
        }
      }
    } catch (err) {
      alert(`Error ending assignment: ${err.message}`);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--navy)' }}>
            Managed Investor Clients
          </h2>
          <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
            Onboard, monitor portfolios, and earn platform-funded commissions
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn btn-secondary btn-sm" onClick={loadClients}>
            <RefreshCw size={14} /> Refresh
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => setShowOnboardModal(true)}>
            <UserPlus size={15} /> Onboard New Investor
          </button>
        </div>
      </div>

      {error && (
        <div style={{ background: 'var(--loss-bg)', color: 'var(--loss)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <ShieldAlert size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Clients Table */}
      <div className="card" style={{ padding: '0' }}>
        <div className="table-container" style={{ border: 'none' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Investor Name</th>
                <th>Username</th>
                <th>Email & Phone</th>
                <th className="numeric">Virtual Balance</th>
                <th>Assigned Date</th>
                <th>Status</th>
                <th style={{ textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {clients.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--muted)' }}>
                    No clients assigned yet. Click "Onboard New Investor" to register a client.
                  </td>
                </tr>
              ) : (
                clients.map(c => (
                  <tr key={c.investor_id}>
                    <td>
                      <strong style={{ color: 'var(--navy)' }}>{c.full_name}</strong>
                    </td>
                    <td>{c.username}</td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
                      <div>{c.email}</div>
                      {c.phone && <div>{c.phone}</div>}
                    </td>
                    <td className="numeric font-bold">{formatINR(c.virtual_balance)}</td>
                    <td style={{ fontSize: '0.8rem' }}>{formatDateTime(c.assigned_at)}</td>
                    <td>
                      <span className="badge badge-gain">ACTIVE</span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <div style={{ display: 'inline-flex', gap: '0.4rem' }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{ padding: '0.2rem 0.5rem' }}
                          onClick={() => handleViewProfile(c.investor_id)}
                          title="View Portfolio & History"
                        >
                          <Eye size={13} /> View
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          style={{ padding: '0.2rem 0.5rem' }}
                          onClick={() => handleEndAssignment(c.investor_id, c.username)}
                          title="End Client Relationship"
                        >
                          <XOctagon size={13} /> Release
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Client Profile Drawer / Modal */}
      {selectedClientProfile && (
        <div className="modal-overlay" onClick={() => setSelectedClientProfile(null)}>
          <div className="modal-content" style={{ maxWidth: '680px' }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1.25rem', borderBottom: '1px solid var(--border)' }}>
              <div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--navy)' }}>
                  Client Portfolio: {selectedClientProfile.client?.full_name}
                </h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
                  Virtual Balance: {formatINR(selectedClientProfile.balance || 0)}
                </span>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedClientProfile(null)}>
                Close
              </button>
            </div>

            <div style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div>
                <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--navy)', marginBottom: '0.5rem' }}>
                  Open Positions
                </h4>
                {selectedClientProfile.holdings?.length === 0 ? (
                  <div style={{ fontSize: '0.825rem', color: 'var(--muted)', background: '#F8FAFC', padding: '0.75rem', borderRadius: 'var(--radius-sm)' }}>
                    No active stock holdings.
                  </div>
                ) : (
                  <div className="table-container">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Symbol</th>
                          <th className="numeric">Quantity</th>
                          <th className="numeric">Avg Cost</th>
                          <th className="numeric">Current Price</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedClientProfile.holdings?.map(h => (
                          <tr key={h.symbol}>
                            <td><strong>{h.symbol}</strong></td>
                            <td className="numeric">{h.quantity}</td>
                            <td className="numeric">{formatINR(h.avg_cost)}</td>
                            <td className="numeric font-bold">{formatINR(h.current_price)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <div>
                <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--navy)', marginBottom: '0.5rem' }}>
                  Commission Earned from this Client
                </h4>
                <div className="card" style={{ background: '#F8FAFC', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>Total Broker Commission:</span>
                  <span className="num font-bold" style={{ fontSize: '1.2rem', color: 'var(--gain)' }}>
                    {formatINR(selectedClientProfile.total_commissions || 0)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Onboard Modal */}
      {showOnboardModal && (
        <OnboardClientModal
          onClose={() => setShowOnboardModal(false)}
          onClientOnboarded={loadClients}
        />
      )}
    </div>
  );
}
