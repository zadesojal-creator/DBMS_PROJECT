import React, { useState, useEffect } from 'react';
import { Users, Unlock, ToggleLeft, ToggleRight, RefreshCw, ShieldAlert } from 'lucide-react';
import { api } from '../../api/client';
import { formatDateTime } from '../../utils/formatters';

export default function UsersView() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadUsers = async () => {
    try {
      const res = await api.admin.getUsers();
      if (res.ok) {
        setUsers(res.data || []);
      }
    } catch (err) {
      console.error('Failed to load users', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleToggleStatus = async (userId, currentStatus) => {
    const newStatus = currentStatus === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    try {
      const res = await api.admin.toggleUserStatus(userId, newStatus);
      if (res.ok) {
        loadUsers();
      }
    } catch (err) {
      alert(`Status toggle failed: ${err.message}`);
    }
  };

  const handleResetLockout = async (userId, username) => {
    try {
      const res = await api.admin.resetLockout(userId);
      if (res.ok) {
        alert(`Lockout reset successfully for ${username}`);
        loadUsers();
      }
    } catch (err) {
      alert(`Reset failed: ${err.message}`);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--navy)' }}>
            User Account Management & Access Control
          </h2>
          <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
            RBAC roles, authentication lockout controls, and status deactivation
          </span>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={loadUsers}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div className="card" style={{ padding: '0' }}>
        <div className="table-container" style={{ border: 'none' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Full Name & Email</th>
                <th>Username</th>
                <th>Role</th>
                <th>Status</th>
                <th className="numeric">Failed Logins</th>
                <th>Last Login</th>
                <th style={{ textAlign: 'center' }}>Security Controls</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => {
                const isLocked = u.failed_login_attempts >= 5 || Boolean(u.locked_until);
                const isActive = u.status === 'ACTIVE';

                return (
                  <tr key={u.id}>
                    <td style={{ fontSize: '0.8rem', color: 'var(--muted)', fontFamily: 'monospace' }}>
                      #{u.id}
                    </td>
                    <td>
                      <strong style={{ color: 'var(--navy)' }}>{u.full_name}</strong>
                      <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{u.email}</div>
                    </td>
                    <td>{u.username}</td>
                    <td>
                      <span className={`badge ${u.role === 'ADMIN' ? 'badge-neutral' : u.role === 'BROKER' ? 'badge-simulated' : 'badge-gain'}`}>
                        {u.role}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${isActive ? 'badge-gain' : 'badge-loss'}`}>
                        {u.status}
                      </span>
                    </td>
                    <td className="numeric">
                      {isLocked ? (
                        <span className="badge badge-loss" title="Account locked for 15 minutes">
                          LOCKED ({u.failed_login_attempts})
                        </span>
                      ) : (
                        <span>{u.failed_login_attempts || 0}</span>
                      )}
                    </td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
                      {formatDateTime(u.last_login_at)}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <div style={{ display: 'inline-flex', gap: '0.4rem' }}>
                        {isLocked && (
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '0.2rem 0.5rem', color: 'var(--amber)' }}
                            onClick={() => handleResetLockout(u.id, u.username)}
                            title="Reset Lockout"
                          >
                            <Unlock size={13} /> Reset
                          </button>
                        )}
                        <button
                          className={`btn ${isActive ? 'btn-danger' : 'btn-primary'} btn-sm`}
                          style={{ padding: '0.2rem 0.6rem' }}
                          onClick={() => handleToggleStatus(u.id, u.status)}
                          title={isActive ? 'Deactivate user' : 'Activate user'}
                        >
                          {isActive ? 'Deactivate' : 'Activate'}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
