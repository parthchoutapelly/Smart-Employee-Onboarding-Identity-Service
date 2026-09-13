import React from 'react';
import { CheckCircle2, Clock, AlertCircle, XCircle } from 'lucide-react';

export function StatusBadge({ status = 'pending' }) {
  const normalized = (status || 'pending').toLowerCase();

  const getIcon = () => {
    switch (normalized) {
      case 'complete':
      case 'verified':
        return <CheckCircle2 size={13} />;
      case 'in_progress':
        return <Clock size={13} />;
      case 'failed':
      case 'rejected':
        return <XCircle size={13} />;
      case 'pending':
      default:
        return <AlertCircle size={13} />;
    }
  };

  const getLabel = () => {
    switch (normalized) {
      case 'in_progress':
        return 'In Progress';
      case 'verified':
        return 'Verified';
      case 'rejected':
        return 'Rejected';
      case 'complete':
        return 'Complete';
      case 'failed':
        return 'Failed';
      case 'pending':
      default:
        return 'Pending';
    }
  };

  return (
    <span className={`badge badge-${normalized}`}>
      {getIcon()}
      {getLabel()}
    </span>
  );
}
