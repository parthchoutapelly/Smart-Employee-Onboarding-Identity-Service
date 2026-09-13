import React, { useState, useEffect } from 'react';
import {
  UserPlus,
  Search,
  Users,
  Shield,
  CheckCircle2,
  AlertCircle,
  Copy,
  ExternalLink,
  RefreshCw,
  Clock,
  Briefcase,
  Calendar,
  FileCheck,
  AlertTriangle
} from 'lucide-react';
import { createEmployee, getOnboardingStatus, listOnboardingEmployees } from '../services/api';
import { ProgressBar } from '../components/ProgressBar';
import { StageCard } from '../components/StageCard';
import { StatusBadge } from '../components/StatusBadge';

const RECENT_EMPLOYEES_KEY = 'seo_recent_tracked_employees';

export function AdminPage() {
  const [activeTab, setActiveTab] = useState('search'); // 'search' | 'register' | 'directory'

  // Search State
  const [searchId, setSearchId] = useState('');
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [statusResult, setStatusResult] = useState(null);
  const [searchError, setSearchError] = useState('');
  const [recentList, setRecentList] = useState([]);

  // Pipeline Directory State
  const [pipelineEmployees, setPipelineEmployees] = useState([]);
  const [loadingPipeline, setLoadingPipeline] = useState(false);
  const [pipelineError, setPipelineError] = useState('');
  const [pipelineFilterDept, setPipelineFilterDept] = useState('All');
  const [pipelineSearch, setPipelineSearch] = useState('');

  // Registration Form State
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    department: 'Engineering',
    role: '',
    manager: '',
    joining_date: new Date().toISOString().split('T')[0],
    employment_type: 'Full-Time'
  });
  const [submittingReg, setSubmittingReg] = useState(false);
  const [regError, setRegError] = useState('');
  const [createdEmployee, setCreatedEmployee] = useState(null);
  const [copied, setCopied] = useState(false);

  // Load recent list from localStorage
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(RECENT_EMPLOYEES_KEY) || '[]');
      setRecentList(saved);
      // Auto-load the first one if available and no search done yet
      if (saved.length > 0 && !statusResult) {
        setSearchId(saved[0].employee_id);
        handleLookup(saved[0].employee_id);
      }
    } catch (e) {
      // ignore
    }
  }, []);

  const saveRecentEmployee = (emp) => {
    try {
      const existing = recentList.filter(e => e.employee_id !== emp.employee_id);
      const updated = [emp, ...existing].slice(0, 8);
      setRecentList(updated);
      localStorage.setItem(RECENT_EMPLOYEES_KEY, JSON.stringify(updated));
    } catch (e) {
      // ignore
    }
  };

  const handleLookup = async (idToSearch) => {
    const target = (idToSearch || searchId).trim();
    if (!target) {
      setSearchError('Please enter an Employee ID to search');
      return;
    }

    setLoadingStatus(true);
    setSearchError('');
    try {
      const res = await getOnboardingStatus(target);
      setStatusResult(res);
      saveRecentEmployee({
        employee_id: target,
        name: res.name || target,
        searched_at: new Date().toLocaleTimeString()
      });
    } catch (err) {
      console.error('Status lookup error:', err);
      setSearchError(err.message || `No employee found for ID "${target}"`);
      setStatusResult(null);
    } finally {
      setLoadingStatus(false);
    }
  };

  const fetchPipeline = async () => {
    setLoadingPipeline(true);
    setPipelineError('');
    try {
      const data = await listOnboardingEmployees();
      const list = Array.isArray(data) ? data : (data?.employees || []);
      setPipelineEmployees(list);
    } catch (err) {
      console.error('Failed to load onboarding pipeline:', err);
      setPipelineError(err.message || 'Failed to retrieve employee onboarding pipeline records');
    } finally {
      setLoadingPipeline(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'directory') {
      fetchPipeline();
    }
  }, [activeTab]);

  const handleInspectCandidate = (empId) => {
    setSearchId(empId);
    setActiveTab('search');
    handleLookup(empId);
  };

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setRegError('');
    setCreatedEmployee(null);

    // Client-side validations
    if (!formData.name.trim() || !formData.email.trim() || !formData.role.trim() || !formData.manager.trim()) {
      setRegError('All fields are required');
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email.trim())) {
      setRegError('Invalid email format');
      return;
    }

    setSubmittingReg(true);
    try {
      const res = await createEmployee({
        name: formData.name.trim(),
        email: formData.email.trim().toLowerCase(),
        department: formData.department.trim(),
        role: formData.role.trim(),
        manager: formData.manager.trim(),
        joining_date: formData.joining_date,
        employment_type: formData.employment_type.trim()
      });

      const newEmpRecord = {
        employee_id: res.employee_id,
        name: formData.name.trim(),
        email: formData.email.trim(),
        department: formData.department,
        role: formData.role
      };
      setCreatedEmployee(newEmpRecord);
      saveRecentEmployee(newEmpRecord);

      // Reset form fields
      setFormData({
        name: '',
        email: '',
        department: 'Engineering',
        role: '',
        manager: '',
        joining_date: new Date().toISOString().split('T')[0],
        employment_type: 'Full-Time'
      });
    } catch (err) {
      console.error('Registration failed:', err);
      setRegError(err.message || 'Failed to register employee record');
    } finally {
      setSubmittingReg(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div>
      {/* Admin Header */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: 'rgba(16, 185, 129, 0.15)',
            color: '#10b981',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Shield size={20} />
          </div>
          <h1 style={{ fontSize: '1.75rem', margin: 0 }}>HR Administration Dashboard</h1>
        </div>
        <p style={{ margin: 0 }}>
          Manage employee records, oversee automated identity provisioning, and monitor onboarding compliance.
        </p>
      </div>

      {/* Summary Metrics Cards */}
      <div className="grid-3" style={{ marginBottom: '2rem' }}>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>IDENTITY PROVISIONING</span>
            <Users size={16} color="#6366f1" />
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>Amazon Cognito</div>
          <p style={{ fontSize: '0.8rem', marginTop: '0.25rem', margin: 0 }}>
            Automated invitation emails & temporary password issuance
          </p>
        </div>

        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>WORKFLOW ORCHESTRATION</span>
            <Clock size={16} color="#3b82f6" />
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>4-Stage Engine</div>
          <p style={{ fontSize: '0.8rem', marginTop: '0.25rem', margin: 0 }}>
            Step Functions state machine with automated timeout tracking
          </p>
        </div>

        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>DOCUMENT VALIDATION</span>
            <FileCheck size={16} color="#10b981" />
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>S3 Event Triggers</div>
          <p style={{ fontSize: '0.8rem', marginTop: '0.25rem', margin: 0 }}>
            Direct presigned upload with automated Lambda inspection
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="tab-list">
        <button
          type="button"
          className={`tab-btn ${activeTab === 'search' ? 'active' : ''}`}
          onClick={() => setActiveTab('search')}
        >
          Search & Track Onboarding
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === 'register' ? 'active' : ''}`}
          onClick={() => setActiveTab('register')}
        >
          Register New Hire
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === 'directory' ? 'active' : ''}`}
          onClick={() => setActiveTab('directory')}
        >
          Pipeline Directory
        </button>
      </div>

      {/* TAB 1: Search & Track Status */}
      {activeTab === 'search' && (
        <div>
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ marginBottom: '0.5rem' }}>Onboarding Status Lookup</h3>
            <p style={{ fontSize: '0.85rem', marginBottom: '1rem' }}>
              Query real-time progress for any active candidate using their canonical Employee ID.
            </p>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleLookup();
              }}
              style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}
            >
              <div style={{ flex: 1, position: 'relative' }}>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Enter Employee UUID (e.g. 550e8400-e29b-41d4-a716-446655440000)"
                  value={searchId}
                  onChange={(e) => setSearchId(e.target.value)}
                  style={{ paddingLeft: '2.5rem' }}
                />
                <Search size={16} style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              </div>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={loadingStatus}
                style={{ padding: '0.625rem 1.25rem' }}
              >
                {loadingStatus ? (
                  <>
                    <span className="spinner" />
                    <span>Searching...</span>
                  </>
                ) : (
                  'Lookup Status'
                )}
              </button>
            </form>

            {/* Quick Pick: Recently Tracked */}
            {recentList.length > 0 && (
              <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, marginRight: '0.5rem' }}>
                  RECENT CANDIDATES:
                </span>
                <div style={{ display: 'inline-flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.25rem' }}>
                  {recentList.map((item) => (
                    <button
                      key={item.employee_id}
                      type="button"
                      onClick={() => {
                        setSearchId(item.employee_id);
                        handleLookup(item.employee_id);
                      }}
                      className="btn btn-secondary"
                      style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', fontFamily: 'monospace' }}
                    >
                      {item.name ? `${item.name} (${item.employee_id.slice(0, 8)}...)` : item.employee_id.slice(0, 12)}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {searchError && (
            <div className="alert alert-danger" style={{ marginBottom: '1.5rem' }}>
              <AlertCircle size={16} />
              <span>{searchError}</span>
            </div>
          )}

          {/* Status Results Display */}
          {statusResult && (
            <div className="card">
              <div className="card-header" style={{ alignItems: 'flex-start' }}>
                <div>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                    CANDIDATE ONBOARDING RECORD
                  </span>
                  <h3 style={{ margin: '0.25rem 0 0', fontFamily: 'monospace' }}>
                    {statusResult.employee_id}
                  </h3>
                </div>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => handleLookup(statusResult.employee_id)}
                  disabled={loadingStatus}
                  style={{ fontSize: '0.8rem', padding: '0.45rem 0.85rem' }}
                >
                  <RefreshCw size={14} className={loadingStatus ? 'spinner' : ''} />
                  <span>Refresh Status</span>
                </button>
              </div>

              {/* Overall Progress */}
              <ProgressBar stages={statusResult.onboarding_status} />

              {/* Stage Progression Cards */}
              <div style={{ marginTop: '1.75rem' }}>
                <h4 style={{ marginBottom: '0.75rem' }}>Workflow Progression Stages</h4>
                <div className="grid-4">
                  <StageCard
                    stepNumber="1"
                    stageKey="document_collection"
                    status={statusResult.onboarding_status?.document_collection}
                  />
                  <StageCard
                    stepNumber="2"
                    stageKey="it_provisioning"
                    status={statusResult.onboarding_status?.it_provisioning}
                  />
                  <StageCard
                    stepNumber="3"
                    stageKey="policy_signoff"
                    status={statusResult.onboarding_status?.policy_signoff}
                  />
                  <StageCard
                    stepNumber="4"
                    stageKey="manager_intro"
                    status={statusResult.onboarding_status?.manager_intro}
                  />
                </div>
              </div>

              {/* Document Status Inspection */}
              <div style={{ marginTop: '2rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '1.5rem' }}>
                <h4 style={{ marginBottom: '0.75rem' }}>Document Compliance Status</h4>
                <div className="grid-3">
                  <div className="card" style={{ background: 'var(--bg-surface-elevated)', padding: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>Government ID Proof</span>
                      <StatusBadge status={statusResult.onboarding_status?.documents?.id_proof} />
                    </div>
                  </div>

                  <div className="card" style={{ background: 'var(--bg-surface-elevated)', padding: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>Degree Certificate</span>
                      <StatusBadge status={statusResult.onboarding_status?.documents?.degree_certificate} />
                    </div>
                  </div>

                  <div className="card" style={{ background: 'var(--bg-surface-elevated)', padding: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>Signed Offer Letter</span>
                      <StatusBadge status={statusResult.onboarding_status?.documents?.offer_letter} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Register New Hire */}
      {activeTab === 'register' && (
        <div style={{ maxWidth: '720px' }}>
          {createdEmployee ? (
            <div className="card" style={{ borderColor: 'var(--status-complete-border)' }}>
              <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
                <div style={{
                  width: '56px',
                  height: '56px',
                  borderRadius: '50%',
                  background: 'rgba(16, 185, 129, 0.15)',
                  color: '#10b981',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '1rem'
                }}>
                  <CheckCircle2 size={32} />
                </div>
                <h2>Employee Profile Created!</h2>
                <p style={{ maxWidth: '500px', margin: '0 auto 1.5rem', fontSize: '0.9rem' }}>
                  The employee record has been persisted to DynamoDB and Cognito user provisioning has been triggered asynchronously by the backend Lambda.
                </p>

                {/* Generated Employee ID Banner */}
                <div style={{
                  background: 'var(--bg-surface-elevated)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-md)',
                  padding: '1rem',
                  maxWidth: '520px',
                  margin: '0 auto 1.5rem',
                  textAlign: 'left'
                }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                    ASSIGNED EMPLOYEE ID
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
                    <code style={{ fontSize: '0.95rem', color: 'var(--primary-500)', fontWeight: 700 }}>
                      {createdEmployee.employee_id}
                    </code>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => copyToClipboard(createdEmployee.employee_id)}
                      style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
                    >
                      <Copy size={13} />
                      <span>{copied ? 'Copied!' : 'Copy ID'}</span>
                    </button>
                  </div>
                </div>

                <div className="alert alert-info" style={{ textAlign: 'left', maxWidth: '520px', margin: '0 auto 1.5rem' }}>
                  <span>
                    <strong>Next Steps:</strong> The new hire will receive an automated welcome email containing their temporary password. They can now log in at the Employee Onboarding Portal.
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem' }}>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => {
                      setSearchId(createdEmployee.employee_id);
                      setActiveTab('search');
                      handleLookup(createdEmployee.employee_id);
                    }}
                  >
                    Track Onboarding Status
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setCreatedEmployee(null)}
                  >
                    Register Another Employee
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="card">
              <div style={{ marginBottom: '1.5rem' }}>
                <h3 style={{ margin: 0 }}>Register New Employee Profile</h3>
                <p style={{ fontSize: '0.85rem', margin: '0.25rem 0 0' }}>
                  Submits payload to <code>POST /employees</code> to instantiate canonical record and initiate Cognito provisioning.
                </p>
              </div>

              {regError && (
                <div className="alert alert-danger">
                  <AlertCircle size={16} />
                  <span>{regError}</span>
                </div>
              )}

              <form onSubmit={handleRegisterSubmit}>
                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label" htmlFor="reg-name">Full Legal Name *</label>
                    <input
                      id="reg-name"
                      name="name"
                      type="text"
                      className="form-input"
                      placeholder="e.g. Alex Mercer"
                      value={formData.name}
                      onChange={handleFormChange}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="reg-email">Corporate Email Address *</label>
                    <input
                      id="reg-email"
                      name="email"
                      type="email"
                      className="form-input"
                      placeholder="e.g. alex.mercer@company.com"
                      value={formData.email}
                      onChange={handleFormChange}
                      required
                    />
                  </div>
                </div>

                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label" htmlFor="reg-department">Department *</label>
                    <select
                      id="reg-department"
                      name="department"
                      className="form-select"
                      value={formData.department}
                      onChange={handleFormChange}
                      required
                    >
                      <option value="Engineering">Engineering</option>
                      <option value="Product">Product</option>
                      <option value="Design">Design</option>
                      <option value="Human Resources">Human Resources</option>
                      <option value="Sales & Marketing">Sales & Marketing</option>
                      <option value="Finance & Operations">Finance & Operations</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="reg-role">Designation / Role *</label>
                    <input
                      id="reg-role"
                      name="role"
                      type="text"
                      className="form-input"
                      placeholder="e.g. Senior Software Engineer"
                      value={formData.role}
                      onChange={handleFormChange}
                      required
                    />
                  </div>
                </div>

                <div className="grid-3">
                  <div className="form-group">
                    <label className="form-label" htmlFor="reg-manager">Reporting Manager *</label>
                    <input
                      id="reg-manager"
                      name="manager"
                      type="text"
                      className="form-input"
                      placeholder="e.g. Sarah Connor"
                      value={formData.manager}
                      onChange={handleFormChange}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="reg-date">Joining Date (ISO) *</label>
                    <input
                      id="reg-date"
                      name="joining_date"
                      type="date"
                      className="form-input"
                      value={formData.joining_date}
                      onChange={handleFormChange}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="reg-type">Employment Type *</label>
                    <select
                      id="reg-type"
                      name="employment_type"
                      className="form-select"
                      value={formData.employment_type}
                      onChange={handleFormChange}
                      required
                    >
                      <option value="Full-Time">Full-Time</option>
                      <option value="Part-Time">Part-Time</option>
                      <option value="Contractor">Contractor</option>
                      <option value="Intern">Intern</option>
                    </select>
                  </div>
                </div>

                <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={submittingReg}
                  >
                    {submittingReg ? (
                      <>
                        <span className="spinner" />
                        <span>Creating Profile...</span>
                      </>
                    ) : (
                      <>
                        <UserPlus size={16} />
                        <span>Create Employee & Provision Account</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Pipeline Directory */}
      {activeTab === 'directory' && (
        <div>
          {/* Header Controls */}
          <div className="card" style={{ marginBottom: '1.25rem' }}>
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '1rem'
            }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Users size={20} style={{ color: 'var(--primary-400)' }} />
                  Candidate Onboarding Directory
                </h3>
                <p style={{ margin: '0.35rem 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  Live multi-stage onboarding status across all registered employees.
                </p>
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.75rem' }}>
                {/* Search in Directory */}
                <div style={{ position: 'relative', minWidth: '220px' }}>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Search candidate or ID..."
                    value={pipelineSearch}
                    onChange={(e) => setPipelineSearch(e.target.value)}
                    style={{ paddingLeft: '2.25rem', fontSize: '0.825rem', padding: '0.5rem 0.75rem 0.5rem 2.25rem' }}
                  />
                  <Search size={14} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                </div>

                {/* Department Filter */}
                <select
                  className="form-input"
                  value={pipelineFilterDept}
                  onChange={(e) => setPipelineFilterDept(e.target.value)}
                  style={{ width: 'auto', fontSize: '0.825rem', padding: '0.5rem 0.75rem' }}
                >
                  <option value="All">All Departments</option>
                  <option value="Engineering">Engineering</option>
                  <option value="Product">Product</option>
                  <option value="Marketing">Marketing</option>
                  <option value="Sales">Sales</option>
                  <option value="Operations">Operations</option>
                  <option value="Human Resources">Human Resources</option>
                  <option value="Finance">Finance</option>
                </select>

                {/* Refresh Button */}
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={fetchPipeline}
                  disabled={loadingPipeline}
                  style={{ padding: '0.5rem 0.875rem', fontSize: '0.825rem' }}
                  title="Refresh pipeline from DynamoDB"
                >
                  <RefreshCw size={14} className={loadingPipeline ? 'spinner' : ''} />
                  <span>{loadingPipeline ? 'Refreshing...' : 'Refresh'}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Error State */}
          {pipelineError && (
            <div className="alert alert-danger" style={{ marginBottom: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertCircle size={18} />
                <span>{pipelineError}</span>
              </div>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={fetchPipeline}
                style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
              >
                Retry
              </button>
            </div>
          )}

          {/* Loading Skeleton */}
          {loadingPipeline && pipelineEmployees.length === 0 && (
            <div className="card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
              <span className="spinner" style={{ width: '2rem', height: '2rem', marginBottom: '1rem', color: 'var(--primary-400)' }} />
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
                Loading employee onboarding pipeline...
              </p>
            </div>
          )}

          {/* Empty State */}
          {!loadingPipeline && pipelineEmployees.length === 0 && !pipelineError && (
            <div className="card" style={{ textAlign: 'center', padding: '3rem 1.5rem', maxWidth: '520px', margin: '0 auto' }}>
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                background: 'rgba(99, 102, 241, 0.15)',
                color: 'var(--primary-400)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '1rem'
              }}>
                <Users size={24} />
              </div>
              <h3>No Onboarding Records Found</h3>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', margin: '0.5rem 0 1.5rem' }}>
                There are currently no employee records in the system. Register a new hire to launch their multi-stage onboarding pipeline.
              </p>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setActiveTab('register')}
              >
                <UserPlus size={16} />
                <span>Register New Hire</span>
              </button>
            </div>
          )}

          {/* Records Table */}
          {pipelineEmployees.length > 0 && (() => {
            const filtered = pipelineEmployees.filter(emp => {
              const matchesDept = pipelineFilterDept === 'All' || emp.department === pipelineFilterDept;
              const q = pipelineSearch.trim().toLowerCase();
              const matchesQuery = !q ||
                (emp.name || '').toLowerCase().includes(q) ||
                (emp.email || '').toLowerCase().includes(q) ||
                (emp.employee_id || '').toLowerCase().includes(q) ||
                (emp.role || '').toLowerCase().includes(q);
              return matchesDept && matchesQuery;
            });

            if (filtered.length === 0) {
              return (
                <div className="card" style={{ textAlign: 'center', padding: '2.5rem 1rem' }}>
                  <Search size={28} style={{ color: 'var(--text-muted)', marginBottom: '0.75rem' }} />
                  <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                    No candidates match the filter criteria.
                  </p>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => {
                      setPipelineFilterDept('All');
                      setPipelineSearch('');
                    }}
                    style={{ marginTop: '0.75rem', fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
                  >
                    Clear Filters
                  </button>
                </div>
              );
            }

            return (
              <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    textAlign: 'left',
                    fontSize: '0.85rem'
                  }}>
                    <thead>
                      <tr style={{
                        background: 'var(--bg-surface-elevated)',
                        borderBottom: '1px solid var(--border-subtle)',
                        color: 'var(--text-secondary)',
                        fontSize: '0.75rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>
                        <th style={{ padding: '0.85rem 1rem' }}>Candidate</th>
                        <th style={{ padding: '0.85rem 1rem' }}>Department & Role</th>
                        <th style={{ padding: '0.85rem 1rem' }}>Doc Collection</th>
                        <th style={{ padding: '0.85rem 1rem' }}>IT Provisioning</th>
                        <th style={{ padding: '0.85rem 1rem' }}>Policy Sign-Off</th>
                        <th style={{ padding: '0.85rem 1rem' }}>Manager Intro</th>
                        <th style={{ padding: '0.85rem 1rem', textAlign: 'right' }}>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((emp) => {
                        const status = emp.onboarding_status || {};
                        return (
                          <tr
                            key={emp.employee_id}
                            style={{
                              borderBottom: '1px solid var(--border-subtle)',
                              transition: 'background 0.15s ease'
                            }}
                            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'; }}
                            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                          >
                            {/* Candidate info */}
                            <td style={{ padding: '0.85rem 1rem' }}>
                              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.15rem' }}>
                                {emp.name || 'Unnamed Employee'}
                              </div>
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                {emp.email || '—'}
                              </div>
                              <div style={{
                                marginTop: '0.25rem',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                fontFamily: 'monospace',
                                fontSize: '0.7rem',
                                color: 'var(--primary-400)',
                                background: 'rgba(99, 102, 241, 0.08)',
                                padding: '0.1rem 0.35rem',
                                borderRadius: '4px'
                              }}>
                                <span>{emp.employee_id}</span>
                              </div>
                            </td>

                            {/* Department / Role */}
                            <td style={{ padding: '0.85rem 1rem' }}>
                              <div style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                                {emp.department || '—'}
                              </div>
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
                                {emp.role || '—'}
                              </div>
                            </td>

                            {/* Stages */}
                            <td style={{ padding: '0.85rem 1rem' }}>
                              <StatusBadge status={status.document_collection || 'pending'} />
                            </td>
                            <td style={{ padding: '0.85rem 1rem' }}>
                              <StatusBadge status={status.it_provisioning || 'pending'} />
                            </td>
                            <td style={{ padding: '0.85rem 1rem' }}>
                              <StatusBadge status={status.policy_signoff || 'pending'} />
                            </td>
                            <td style={{ padding: '0.85rem 1rem' }}>
                              <StatusBadge status={status.manager_intro || 'pending'} />
                            </td>

                            {/* Action */}
                            <td style={{ padding: '0.85rem 1rem', textAlign: 'right' }}>
                              <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={() => handleInspectCandidate(emp.employee_id)}
                                style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                                title="Inspect full onboarding workflow"
                              >
                                <ExternalLink size={12} />
                                <span>Track</span>
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Footer Count */}
                <div style={{
                  padding: '0.75rem 1rem',
                  borderTop: '1px solid var(--border-subtle)',
                  background: 'var(--bg-surface-elevated)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '0.775rem',
                  color: 'var(--text-secondary)'
                }}>
                  <span>Showing <strong>{filtered.length}</strong> of <strong>{pipelineEmployees.length}</strong> candidates</span>
                  <span>Auto-synchronized with DynamoDB</span>
                </div>
              </div>
            );
          })()}
        </div>
      )}

    </div>
  );
}
