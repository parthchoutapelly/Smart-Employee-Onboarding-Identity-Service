import React from 'react';

export function ProgressBar({ stages = {} }) {
  const stageKeys = ['document_collection', 'it_provisioning', 'policy_signoff', 'manager_intro'];
  const total = stageKeys.length;
  const completed = stageKeys.filter(key => stages[key] === 'complete').length;
  const percent = Math.round((completed / total) * 100);

  return (
    <div style={{ margin: '1.5rem 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
        <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>
          Overall Onboarding Progress
        </span>
        <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
          {completed} of {total} stages completed ({percent}%)
        </span>
      </div>
      <div className="progress-container">
        <div className="progress-fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
