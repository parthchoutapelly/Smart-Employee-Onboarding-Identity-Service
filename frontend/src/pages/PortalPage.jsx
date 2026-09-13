import React, { useState, useEffect, useCallback } from 'react';
import {
  User,
  Building,
  Briefcase,
  Hash,
  RefreshCw,
  Lock,
  Mail,
  AlertCircle,
  CheckCircle2,
  FileText
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { getOnboardingStatus } from '../services/api';
import { ProgressBar } from '../components/ProgressBar';
import { StageCard } from '../components/StageCard';
import { DocumentCard } from '../components/DocumentCard';

export function PortalPage() {
  const {
    user,
    employeeId,
    name,
    email,
    role,
    department,
    loading: authLoading,
    requireNewPassword,
    login,
    confirmPassword,
    setDemoEmployeeId,
    isCognitoConfigured
  } = useAuth();

  // Sign-in state
  const [signInEmail, setSignInEmail] = useState('');
  const [signInPassword, setSignInPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [submittingAuth, setSubmittingAuth] = useState(false);
  const [authError, setAuthError] = useState('');

  // Portal Onboarding Data state
  const [statusData, setStatusData] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [statusError, setStatusError] = useState('');

  // Fetch status callback
  const fetchStatus = useCallback(async (targetEmpId) => {
    const idToUse = targetEmpId || employeeId;
    if (!idToUse) return;

    setLoadingStatus(true);
    setStatusError('');
    try {
      const data = await getOnboardingStatus(idToUse);
      setStatusData(data);
    } catch (err) {
      console.error('Failed to load status:', err);
      setStatusError(err.message || 'Unable to retrieve onboarding status');
    } finally {
      setLoadingStatus(false);
    }
  }, [employeeId]);

  useEffect(() => {
    if (employeeId) {
      fetchStatus(employeeId);
    }
  }, [employeeId, fetchStatus]);

  const handleSignIn = async (e) => {
    e.preventDefault();
    setAuthError('');
    if (!signInEmail || !signInPassword) {
      setAuthError('Please enter both email and password');
      return;
    }

    setSubmittingAuth(true);
    try {
      await login(signInEmail, signInPassword);
    } catch (err) {
      console.error('Login error:', err);
      setAuthError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setSubmittingAuth(false);
    }
  };

  const handleNewPasswordSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');
    if (!newPassword || newPassword.length < 8) {
      setAuthError('Password must be at least 8 characters long');
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setAuthError('Passwords do not match');
      return;
    }

    setSubmittingAuth(true);
    try {
      await confirmPassword(newPassword);
    } catch (err) {
      console.error('Password reset error:', err);
      setAuthError(err.message || 'Failed to set permanent password');
    } finally {
      setSubmittingAuth(false);
    }
  };

  if (authLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem 1rem' }}>
        <span className="spinner" style={{ width: '2rem', height: '2rem', color: 'var(--primary-500)' }} />
        <p style={{ marginTop: '1rem' }}>Verifying Cognito session...</p>
      </div>
    );
  }

  // --- Render Authentication Screen if unauthenticated ---
  if (!user) {
    return (
      <div style={{ maxWidth: '440px', margin: '2rem auto' }}>
        <div className="card">
          <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
            <div style={{
              width: '44px',
              height: '44px',
              borderRadius: '50%',
              background: 'rgba(99, 102, 241, 0.15)',
              color: 'var(--primary-500)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '0.75rem'
            }}>
              <Lock size={22} />
            </div>
            <h2>Employee Portal Sign In</h2>
            <p style={{ fontSize: '0.85rem' }}>
              Sign in with your Cognito employee credentials provided in your onboarding email.
            </p>
          </div>

          {authError && (
            <div className="alert alert-danger">
              <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
              <span>{authError}</span>
            </div>
          )}

          {!requireNewPassword ? (
            <form onSubmit={handleSignIn}>
              <div className="form-group">
                <label className="form-label" htmlFor="login-email">Corporate Email</label>
                <div style={{ position: 'relative' }}>
                  <input
                    id="login-email"
                    type="email"
                    className="form-input"
                    placeholder="newhire@company.com"
                    value={signInEmail}
                    onChange={(e) => setSignInEmail(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="login-password">Password or Temporary Password</label>
                <input
                  id="login-password"
                  type="password"
                  className="form-input"
                  placeholder="••••••••••••"
                  value={signInPassword}
                  onChange={(e) => setSignInPassword(e.target.value)}
                  required
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '0.5rem' }}
                disabled={submittingAuth}
              >
                {submittingAuth ? (
                  <>
                    <span className="spinner" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  'Sign In'
                )}
              </button>

              {!isCognitoConfigured && (
                <div style={{ marginTop: '1.25rem', padding: '0.75rem', borderRadius: '8px', background: 'var(--bg-surface-elevated)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  💡 <strong>Local Demo Mode Active:</strong> Cognito env variables are not configured. Enter any email to log in with a mock profile.
                </div>
              )}
            </form>
          ) : (
            <form onSubmit={handleNewPasswordSubmit}>
              <div className="alert alert-info">
                <span>First time login: Please set a new permanent password for your corporate account.</span>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="new-password">New Permanent Password</label>
                <input
                  id="new-password"
                  type="password"
                  className="form-input"
                  placeholder="Minimum 8 characters"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="confirm-password">Confirm New Password</label>
                <input
                  id="confirm-password"
                  type="password"
                  className="form-input"
                  placeholder="Re-type permanent password"
                  value={confirmNewPassword}
                  onChange={(e) => setConfirmNewPassword(e.target.value)}
                  required
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '0.5rem' }}
                disabled={submittingAuth}
              >
                {submittingAuth ? (
                  <>
                    <span className="spinner" />
                    <span>Setting password...</span>
                  </>
                ) : (
                  'Set New Password & Sign In'
                )}
              </button>
            </form>
          )}
        </div>
      </div>
    );
  }

  // --- Authenticated Dashboard ---
  const onboardingStatus = statusData?.onboarding_status || {
    document_collection: 'pending',
    it_provisioning: 'pending',
    policy_signoff: 'pending',
    manager_intro: 'pending',
    documents: {
      id_proof: 'pending',
      degree_certificate: 'pending',
      offer_letter: 'pending'
    }
  };

  const documents = onboardingStatus.documents || {
    id_proof: 'pending',
    degree_certificate: 'pending',
    offer_letter: 'pending'
  };

  return (
    <div>
      {/* Identity & Header Section */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1.5rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
            <div style={{
              width: '56px',
              height: '56px',
              borderRadius: '16px',
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: '1.5rem',
              fontWeight: 700,
              boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)'
            }}>
              {name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 style={{ fontSize: '1.4rem', margin: 0 }}>Welcome, {name}</h2>
              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '1rem',
                marginTop: '0.35rem',
                fontSize: '0.85rem',
                color: 'var(--text-secondary)'
              }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Mail size={14} color="#6366f1" />
                  {email}
                </span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Briefcase size={14} color="#3b82f6" />
                  {role}
                </span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Building size={14} color="#10b981" />
                  {department}
                </span>
              </div>
            </div>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            background: 'var(--bg-surface-elevated)',
            padding: '0.75rem 1.25rem',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-default)'
          }}>
            <div>
              <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                EMPLOYEE IDENTITY ID
              </div>
              <div style={{
                fontSize: '0.9rem',
                fontFamily: 'monospace',
                fontWeight: 700,
                color: 'var(--text-primary)'
              }}>
                {employeeId || 'ID Not Assigned'}
              </div>
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => fetchStatus()}
              disabled={loadingStatus || !employeeId}
              title="Refresh onboarding status"
              style={{ padding: '0.45rem' }}
            >
              <RefreshCw size={15} className={loadingStatus ? 'spinner' : ''} />
            </button>
          </div>
        </div>

        {/* Demo fallback Employee ID changer for testing */}
        {!isCognitoConfigured && (
          <div style={{
            marginTop: '1rem',
            paddingTop: '0.75rem',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            fontSize: '0.8rem',
            color: 'var(--text-muted)'
          }}>
            <span>⚙️ Demo mode: Change tracked Employee ID:</span>
            <input
              type="text"
              defaultValue={employeeId}
              onBlur={(e) => {
                if (e.target.value) {
                  setDemoEmployeeId(e.target.value.trim());
                  fetchStatus(e.target.value.trim());
                }
              }}
              style={{
                background: 'var(--bg-main)',
                border: '1px solid var(--border-default)',
                color: 'white',
                padding: '0.25rem 0.5rem',
                borderRadius: '4px',
                fontSize: '0.8rem'
              }}
            />
          </div>
        )}

        {/* Overall Progress Bar */}
        <ProgressBar stages={onboardingStatus} />
      </div>

      {statusError && (
        <div className="alert alert-danger" style={{ marginBottom: '1.5rem' }}>
          <AlertCircle size={16} />
          <span>{statusError}</span>
        </div>
      )}

      {/* 4 Workflow Stage Cards */}
      <div style={{ marginBottom: '2.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h3>Workflow Progression Stages</h3>
          <span style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>
            Orchestrated by AWS Step Functions
          </span>
        </div>
        <div className="grid-4">
          <StageCard
            stepNumber="1"
            stageKey="document_collection"
            status={onboardingStatus.document_collection}
          />
          <StageCard
            stepNumber="2"
            stageKey="it_provisioning"
            status={onboardingStatus.it_provisioning}
          />
          <StageCard
            stepNumber="3"
            stageKey="policy_signoff"
            status={onboardingStatus.policy_signoff}
          />
          <StageCard
            stepNumber="4"
            stageKey="manager_intro"
            status={onboardingStatus.manager_intro}
          />
        </div>
      </div>

      {/* Document Section */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div>
            <h3>Required Compliance Documents</h3>
            <p style={{ fontSize: '0.85rem', margin: 0 }}>
              Upload valid PDF, JPG, or PNG files. Each file is verified automatically upon upload to Amazon S3.
            </p>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => fetchStatus()}
            disabled={loadingStatus}
            style={{ fontSize: '0.8rem', padding: '0.45rem 0.85rem' }}
          >
            <RefreshCw size={14} className={loadingStatus ? 'spinner' : ''} />
            <span>Refresh Verification Status</span>
          </button>
        </div>

        <div className="grid-3">
          <DocumentCard
            employeeId={employeeId}
            documentType="id_proof"
            status={documents.id_proof}
            onUploadComplete={() => fetchStatus()}
          />
          <DocumentCard
            employeeId={employeeId}
            documentType="degree_certificate"
            status={documents.degree_certificate}
            onUploadComplete={() => fetchStatus()}
          />
          <DocumentCard
            employeeId={employeeId}
            documentType="offer_letter"
            status={documents.offer_letter}
            onUploadComplete={() => fetchStatus()}
          />
        </div>
      </div>
    </div>
  );
}
