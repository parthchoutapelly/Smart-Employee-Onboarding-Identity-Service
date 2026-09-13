import React from 'react';
import { FileCheck, Laptop, ShieldCheck, UserCheck } from 'lucide-react';
import { StatusBadge } from './StatusBadge';

const STAGE_CONFIG = {
  document_collection: {
    title: 'Document Collection',
    description: 'Verify identity, qualifications, and employment documents',
    icon: FileCheck,
    color: '#6366f1'
  },
  it_provisioning: {
    title: 'IT Provisioning',
    description: 'Account access, laptop allocation, and developer setup',
    icon: Laptop,
    color: '#3b82f6'
  },
  policy_signoff: {
    title: 'Policy Sign-off',
    description: 'Acknowledge corporate handbook, security policies & NDA',
    icon: ShieldCheck,
    color: '#10b981'
  },
  manager_intro: {
    title: 'Manager Introduction',
    description: 'Initial sync with your reporting manager and team kickoff',
    icon: UserCheck,
    color: '#8b5cf6'
  }
};

export function StageCard({ stageKey, status = 'pending', stepNumber }) {
  const config = STAGE_CONFIG[stageKey] || {
    title: stageKey,
    description: '',
    icon: FileCheck,
    color: '#6366f1'
  };

  const IconComponent = config.icon;

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="card-header" style={{ marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            backgroundColor: `${config.color}20`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: config.color
          }}>
            <IconComponent size={20} />
          </div>
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              STAGE {stepNumber}
            </span>
            <h4 style={{ margin: 0, fontSize: '0.95rem' }}>{config.title}</h4>
          </div>
        </div>
      </div>
      
      <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', flex: 1, marginBottom: '1rem' }}>
        {config.description}
      </p>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.75rem' }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Workflow State</span>
        <StatusBadge status={status} />
      </div>
    </div>
  );
}
