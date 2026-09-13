import { getAuthToken } from '../auth/cognito';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

/**
 * Core HTTP client with Cognito token injection and error handling
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  try {
    const token = await getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  } catch (err) {
    console.debug('No auth token attached:', err);
  }

  const response = await fetch(url, {
    ...options,
    headers
  });

  let data;
  try {
    data = await response.json();
  } catch (e) {
    data = { message: response.statusText };
  }

  if (!response.ok) {
    const errorMessage = data?.error || data?.message || `HTTP ${response.status}: Request failed`;
    const error = new Error(errorMessage);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

// In-memory demo store for mock/fallback mode
const MOCK_STORAGE_KEY = 'seo_mock_profiles';
function getMockProfiles() {
  try {
    return JSON.parse(localStorage.getItem(MOCK_STORAGE_KEY) || '{}');
  } catch {
    return {};
  }
}
function saveMockProfiles(profiles) {
  localStorage.setItem(MOCK_STORAGE_KEY, JSON.stringify(profiles));
}

/**
 * Register a new employee
 * POST /employees
 */
export async function createEmployee(payload) {
  if (API_BASE_URL) {
    return await request('/employees', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  // Local fallback mock
  console.info('[Mock API] createEmployee called with:', payload);
  const employeeId = 'emp-' + Math.random().toString(36).substring(2, 10);
  const profiles = getMockProfiles();
  profiles[employeeId] = {
    ...payload,
    employee_id: employeeId,
    created_at: new Date().toISOString(),
    onboarding_status: {
      document_collection: 'pending',
      it_provisioning: 'pending',
      policy_signoff: 'pending',
      manager_intro: 'pending',
      documents: {
        id_proof: 'pending',
        degree_certificate: 'pending',
        offer_letter: 'pending'
      }
    }
  };
  saveMockProfiles(profiles);

  // simulate network latency
  await new Promise(r => setTimeout(r, 400));
  return {
    employee_id: employeeId,
    status: 'created'
  };
}

/**
 * Retrieve an employee's onboarding progress
 * GET /onboarding/{employee_id}/status
 */
export async function getOnboardingStatus(employeeId) {
  if (!employeeId) {
    throw new Error('Employee ID is required');
  }

  if (API_BASE_URL) {
    return await request(`/onboarding/${encodeURIComponent(employeeId)}/status`, {
      method: 'GET'
    });
  }

  // Local fallback mock
  await new Promise(r => setTimeout(r, 300));
  const profiles = getMockProfiles();
  if (profiles[employeeId]) {
    return {
      employee_id: employeeId,
      onboarding_status: profiles[employeeId].onboarding_status
    };
  }

  // Default seed data for any unrecognized mock ID
  return {
    employee_id: employeeId,
    onboarding_status: {
      document_collection: 'in_progress',
      it_provisioning: 'pending',
      policy_signoff: 'pending',
      manager_intro: 'pending',
      documents: {
        id_proof: 'verified',
        degree_certificate: 'pending',
        offer_letter: 'pending'
      }
    }
  };
}

/**
 * Request presigned upload URL
 * POST /documents/upload-url
 */
export async function getUploadUrl({ employee_id, document_type, file_extension }) {
  if (API_BASE_URL) {
    return await request('/documents/upload-url', {
      method: 'POST',
      body: JSON.stringify({
        employee_id,
        document_type,
        file_extension
      })
    });
  }

  // Local fallback mock
  await new Promise(r => setTimeout(r, 250));
  return {
    upload_url: `https://mock-s3-presigned-url/${employee_id}/${document_type}.${file_extension}`,
    s3_key: `documents/${employee_id}/${document_type}.${file_extension}`
  };
}

/**
 * Upload binary file directly to S3 via presigned PUT URL.
 * contentType must match exactly what the backend baked into the presigned URL signature.
 */
export async function uploadFileToS3(uploadUrl, file, onProgress, contentType) {
  if (!API_BASE_URL || uploadUrl.includes('mock-s3')) {
    // Local fallback mock simulation
    for (let p = 20; p <= 100; p += 20) {
      if (onProgress) onProgress(p);
      await new Promise(r => setTimeout(r, 120));
    }
    return true;
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', uploadUrl, true);
    // Use the caller-supplied contentType (derived from the normalized extension) so it
    // exactly matches the ContentType parameter the backend baked into the presigned signature.
    xhr.setRequestHeader('Content-Type', contentType || 'application/octet-stream');

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(true);
      } else {
        reject(new Error(`S3 upload failed with HTTP status ${xhr.status}`));
      }
    };

    xhr.onerror = () => {
      reject(new Error('Network error during direct S3 file upload'));
    };

    xhr.send(file);
  });
}

/**
 * Retrieve all employee onboarding pipeline statuses
 * GET /onboarding/pipeline
 */
export async function listOnboardingEmployees() {
  if (API_BASE_URL) {
    return await request('/onboarding/pipeline', {
      method: 'GET'
    });
  }

  // Local fallback mock
  await new Promise(r => setTimeout(r, 300));
  const profiles = getMockProfiles();
  return Object.values(profiles).map(p => ({
    employee_id: p.employee_id,
    name: p.name,
    email: p.email,
    department: p.department,
    role: p.role,
    manager: p.manager,
    joining_date: p.joining_date,
    employment_type: p.employment_type,
    created_at: p.created_at,
    onboarding_status: p.onboarding_status
  }));
}
