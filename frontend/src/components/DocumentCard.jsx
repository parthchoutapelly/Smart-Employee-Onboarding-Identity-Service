import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, Check, AlertTriangle, AlertCircle } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { getUploadUrl, uploadFileToS3 } from '../services/api';

const DOC_METADATA = {
  id_proof: {
    title: 'Government ID Proof',
    subtitle: 'Passport, Driving License, or National ID',
    allowedTypes: ['pdf', 'jpg', 'jpeg', 'png']
  },
  degree_certificate: {
    title: 'Degree Certificate',
    subtitle: 'Highest qualification degree or official transcript',
    allowedTypes: ['pdf', 'jpg', 'jpeg', 'png']
  },
  offer_letter: {
    title: 'Signed Offer Letter',
    subtitle: 'Countersigned offer letter agreement copy',
    allowedTypes: ['pdf', 'jpg', 'jpeg', 'png']
  }
};

export function DocumentCard({ employeeId, documentType, status = 'pending', onUploadComplete }) {
  const meta = DOC_METADATA[documentType] || {
    title: documentType,
    subtitle: 'Document upload',
    allowedTypes: ['pdf', 'jpg', 'jpeg', 'png']
  };

  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const handleFileChange = (e) => {
    setErrorMessage('');
    setSuccessMessage('');
    const file = e.target.files?.[0];
    if (!file) return;

    // Check extension
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !meta.allowedTypes.includes(ext)) {
      setErrorMessage(`Invalid format. Allowed: ${meta.allowedTypes.join(', ').toUpperCase()}`);
      setSelectedFile(null);
      return;
    }

    // Check max size (10 MB)
    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage('File exceeds maximum allowed size of 10 MB');
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setErrorMessage('Please choose a file to upload');
      return;
    }
    if (!employeeId) {
      setErrorMessage('Missing employee identity context');
      return;
    }

    setUploading(true);
    setProgress(10);
    setErrorMessage('');
    setSuccessMessage('');

    try {
      const rawExt = selectedFile.name.split('.').pop()?.toLowerCase();
      const normalizedExt = rawExt === 'jpeg' ? 'jpg' : rawExt;

      // Content-Type must exactly match what the backend baked into the presigned URL signature
      const contentTypeMap = {
        pdf: 'application/pdf',
        jpg: 'image/jpeg',
        png: 'image/png',
      };
      const contentType = contentTypeMap[normalizedExt] || 'application/octet-stream';

      // Step 1: Request presigned S3 PUT URL
      const { upload_url } = await getUploadUrl({
        employee_id: employeeId,
        document_type: documentType,
        file_extension: normalizedExt
      });

      // Step 2: PUT file directly to S3 using the exact Content-Type from the presigned signature
      await uploadFileToS3(upload_url, selectedFile, (p) => setProgress(p), contentType);

      setSuccessMessage('Uploaded successfully. S3 verification in progress...');
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';

      // Trigger status refresh
      if (onUploadComplete) {
        onUploadComplete();
      }
    } catch (err) {
      console.error('Upload failed:', err);
      setErrorMessage(err.message || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const isVerified = status === 'verified';
  const isRejected = status === 'rejected';

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '38px',
            height: '38px',
            borderRadius: '8px',
            backgroundColor: isVerified ? 'rgba(16, 185, 129, 0.15)' : 'rgba(99, 102, 241, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: isVerified ? '#10b981' : '#6366f1'
          }}>
            <FileText size={20} />
          </div>
          <div>
            <h4 style={{ margin: 0 }}>{meta.title}</h4>
            <p style={{ margin: 0, fontSize: '0.775rem', color: 'var(--text-muted)' }}>
              {meta.subtitle}
            </p>
          </div>
        </div>
        <StatusBadge status={status} />
      </div>

      {isRejected && (
        <div className="alert alert-danger" style={{ padding: '0.5rem 0.75rem', marginBottom: '0.75rem' }}>
          <AlertCircle size={15} style={{ flexShrink: 0, marginTop: '2px' }} />
          <span style={{ fontSize: '0.8rem' }}>
            Document was rejected during validation. Please upload a clear PDF or JPG.
          </span>
        </div>
      )}

      {successMessage && (
        <div className="alert alert-success" style={{ padding: '0.5rem 0.75rem', marginBottom: '0.75rem' }}>
          <Check size={15} style={{ flexShrink: 0, marginTop: '2px' }} />
          <span style={{ fontSize: '0.8rem' }}>{successMessage}</span>
        </div>
      )}

      {errorMessage && (
        <div className="alert alert-danger" style={{ padding: '0.5rem 0.75rem', marginBottom: '0.75rem' }}>
          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: '2px' }} />
          <span style={{ fontSize: '0.8rem' }}>{errorMessage}</span>
        </div>
      )}

      <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={handleFileChange}
          disabled={uploading}
          style={{ display: 'none' }}
          id={`file-input-${documentType}`}
        />

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <label
            htmlFor={`file-input-${documentType}`}
            className="btn btn-secondary"
            style={{
              flex: 1,
              padding: '0.5rem 0.75rem',
              fontSize: '0.8rem',
              cursor: uploading ? 'not-allowed' : 'pointer',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}
          >
            {selectedFile ? selectedFile.name : (isVerified ? 'Replace File...' : 'Choose File...')}
          </label>

          <button
            type="button"
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            style={{ padding: '0.5rem 0.85rem', fontSize: '0.8rem' }}
          >
            {uploading ? (
              <>
                <span className="spinner" />
                <span>{progress}%</span>
              </>
            ) : (
              <>
                <UploadCloud size={14} />
                <span>Upload</span>
              </>
            )}
          </button>
        </div>

        {uploading && (
          <div className="progress-container" style={{ height: '4px', marginTop: '0.5rem' }}>
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.4rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          <span>Formats: PDF, JPG, PNG</span>
          <span>Max: 10 MB</span>
        </div>
      </div>
    </div>
  );
}
