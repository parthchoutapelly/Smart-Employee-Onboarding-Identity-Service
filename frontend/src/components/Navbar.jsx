import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Users, LogOut, Shield } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

export function Navbar() {
  const location = useLocation();
  const { user, name, role, logout } = useAuth();

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="brand-link">
          <div className="brand-badge">
            <Users size={18} />
          </div>
          <span>Smart Employee Onboarding & Identity Service</span>
        </Link>

        <nav className="nav-links">
          <Link
            to="/"
            className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
          >
            Home
          </Link>
          <Link
            to="/portal"
            className={`nav-link ${location.pathname === '/portal' ? 'active' : ''}`}
          >
            Employee Portal
          </Link>
          <Link
            to="/admin"
            className={`nav-link ${location.pathname === '/admin' ? 'active' : ''}`}
          >
            HR Admin
          </Link>

          {user ? (
            <div className="auth-controls" style={{ marginLeft: '0.5rem' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontSize: '0.825rem',
                background: 'var(--bg-surface-elevated)',
                padding: '0.35rem 0.75rem',
                borderRadius: 'var(--radius-full)',
                border: '1px solid var(--border-default)'
              }}>
                <Shield size={13} color="#6366f1" />
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{name}</span>
                <span style={{ color: 'var(--text-muted)' }}>({role})</span>
              </div>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={logout}
                title="Sign out"
                style={{ padding: '0.35rem 0.65rem', fontSize: '0.8rem' }}
              >
                <LogOut size={14} />
                <span>Sign Out</span>
              </button>
            </div>
          ) : (
            <Link to="/portal" className="btn btn-primary" style={{ padding: '0.4rem 0.85rem', fontSize: '0.825rem' }}>
              Sign In
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
