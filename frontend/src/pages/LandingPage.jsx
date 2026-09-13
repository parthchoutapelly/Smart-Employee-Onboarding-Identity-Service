import React from 'react';
import { Link } from 'react-router-dom';
import { UserCheck, ShieldCheck, ArrowRight, FileCheck, Cpu, Key } from 'lucide-react';

export function LandingPage() {
  return (
    <div>
      <section className="hero">
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.35rem 0.85rem',
          borderRadius: 'var(--radius-full)',
          background: 'rgba(99, 102, 241, 0.1)',
          border: '1px solid rgba(99, 102, 241, 0.3)',
          color: '#a5b4fc',
          fontSize: '0.8rem',
          fontWeight: 600,
          marginBottom: '1.25rem'
        }}>
          <Key size={14} />
          AWS Cloud-Native Identity & Onboarding Suite
        </div>
        <h1 className="hero-title">
          Smart Employee Onboarding & Identity Service
        </h1>
        <p className="hero-subtitle">
          Automated identity lifecycle management, secure document collection, and seamless multi-stage employee onboarding powered by AWS Serverless.
        </p>
      </section>

      <section className="grid-2" style={{ maxWidth: '960px', margin: '0 auto 3rem' }}>
        {/* Employee Portal Card */}
        <div className="card" style={{
          display: 'flex',
          flexDirection: 'column',
          border: '1px solid var(--border-default)',
          background: 'linear-gradient(180deg, var(--bg-surface) 0%, var(--bg-subtle) 100%)',
          transition: 'transform 0.2s ease, border-color 0.2s ease'
        }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            background: 'rgba(99, 102, 241, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--primary-500)',
            marginBottom: '1.25rem'
          }}>
            <UserCheck size={26} />
          </div>
          <h2 style={{ fontSize: '1.35rem', marginBottom: '0.5rem' }}>Employee Onboarding Portal</h2>
          <p style={{ fontSize: '0.9rem', marginBottom: '1.5rem', flex: 1 }}>
            Are you a new hire joining the company? Sign in with your corporate Cognito credentials, track your onboarding roadmap, and upload required compliance credentials to S3.
          </p>
          <div style={{
            background: 'var(--bg-surface-elevated)',
            borderRadius: 'var(--radius-md)',
            padding: '0.75rem 1rem',
            marginBottom: '1.5rem',
            fontSize: '0.8rem',
            color: 'var(--text-secondary)'
          }}>
            <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '0.25rem' }}>Features:</strong>
            • 4-Stage Onboarding Pipeline Progress<br/>
            • Direct Presigned S3 Document Uploads<br/>
            • Real-time Verification & Stage Badges
          </div>
          <Link to="/portal" className="btn btn-primary" style={{ width: '100%' }}>
            <span>Access Employee Portal</span>
            <ArrowRight size={16} />
          </Link>
        </div>

        {/* HR Admin Card */}
        <div className="card" style={{
          display: 'flex',
          flexDirection: 'column',
          border: '1px solid var(--border-default)',
          background: 'linear-gradient(180deg, var(--bg-surface) 0%, var(--bg-subtle) 100%)',
          transition: 'transform 0.2s ease, border-color 0.2s ease'
        }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            background: 'rgba(16, 185, 129, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#10b981',
            marginBottom: '1.25rem'
          }}>
            <ShieldCheck size={26} />
          </div>
          <h2 style={{ fontSize: '1.35rem', marginBottom: '0.5rem' }}>HR Administration Dashboard</h2>
          <p style={{ fontSize: '0.9rem', marginBottom: '1.5rem', flex: 1 }}>
            HR operations command center. Register and initiate new employee profiles, trigger asynchronous Cognito identity provisioning, and monitor live candidate pipelines.
          </p>
          <div style={{
            background: 'var(--bg-surface-elevated)',
            borderRadius: 'var(--radius-md)',
            padding: '0.75rem 1rem',
            marginBottom: '1.5rem',
            fontSize: '0.8rem',
            color: 'var(--text-secondary)'
          }}>
            <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '0.25rem' }}>Features:</strong>
            • New Hire Profile & Identity Registration<br/>
            • Real-time Status Lookup by Employee ID<br/>
            • Compliance & Stage Verification Auditing
          </div>
          <Link to="/admin" className="btn btn-secondary" style={{ width: '100%' }}>
            <span>Access HR Dashboard</span>
            <ArrowRight size={16} />
          </Link>
        </div>
      </section>

      {/* System Highlights */}
      <section style={{
        borderTop: '1px solid var(--border-subtle)',
        paddingTop: '2.5rem',
        maxWidth: '960px',
        margin: '0 auto'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h3 style={{ fontSize: '1.15rem', color: 'var(--text-secondary)' }}>
            Enterprise Cloud Architecture
          </h3>
        </div>
        <div className="grid-3">
          <div className="card" style={{ padding: '1.25rem' }}>
            <Key size={22} color="#6366f1" style={{ marginBottom: '0.75rem' }} />
            <h4 style={{ marginBottom: '0.35rem' }}>Amazon Cognito Identity</h4>
            <p style={{ fontSize: '0.825rem' }}>
              Built-in identity management with custom attributes (employee ID, role, department) and password policies.
            </p>
          </div>
          <div className="card" style={{ padding: '1.25rem' }}>
            <Cpu size={22} color="#3b82f6" style={{ marginBottom: '0.75rem' }} />
            <h4 style={{ marginBottom: '0.35rem' }}>Step Functions Engine</h4>
            <p style={{ fontSize: '0.825rem' }}>
              Orchestrated 4-stage onboarding workflow with stage timeouts and reminder email dispatch.
            </p>
          </div>
          <div className="card" style={{ padding: '1.25rem' }}>
            <FileCheck size={22} color="#10b981" style={{ marginBottom: '0.75rem' }} />
            <h4 style={{ marginBottom: '0.35rem' }}>S3 Event Validation</h4>
            <p style={{ fontSize: '0.825rem' }}>
              Secure presigned document uploads with automated Lambda file inspection, rejection logging, and SNS notifications.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
