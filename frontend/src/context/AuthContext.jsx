import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, setCsrfToken } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Check existing session
    api.auth.session()
      .then(res => {
        if (res.ok && res.data) {
          if (res.data.csrf_token) {
            setCsrfToken(res.data.csrf_token);
          }
          if (res.data.authenticated) {
            setUser(res.data.user);
          } else {
            setUser(null);
          }
        } else {
          setUser(null);
        }
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const login = async (identifier, password) => {
    setError(null);
    try {
      const res = await api.auth.login(identifier, password);
      if (res.ok) {
        if (res.data?.csrf_token) {
          setCsrfToken(res.data.csrf_token);
        }
        setUser(res.data);
        return res.data;
      }
    } catch (err) {
      setError(err.message || 'Login failed');
      throw err;
    }
  };

  const logout = async () => {
    try {
      await api.auth.logout();
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, error, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
