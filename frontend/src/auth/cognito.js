import { Amplify } from 'aws-amplify';
import {
  signIn,
  signOut,
  getCurrentUser,
  fetchUserAttributes,
  confirmSignIn,
  fetchAuthSession
} from 'aws-amplify/auth';

const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID;
const userPoolClientId = import.meta.env.VITE_COGNITO_CLIENT_ID;
const region = import.meta.env.VITE_AWS_REGION || 'us-east-1';

export const isCognitoConfigured = Boolean(userPoolId && userPoolClientId);

if (isCognitoConfigured) {
  try {
    Amplify.configure({
      Auth: {
        Cognito: {
          userPoolId,
          userPoolClientId
        }
      }
    });
  } catch (err) {
    console.error('Failed to configure Amplify Auth:', err);
  }
} else {
  console.warn('Cognito environment variables not set. Running in local fallback mode.');
}

/**
 * Sign in with email and password
 */
export async function loginUser(email, password) {
  if (isCognitoConfigured) {
    const result = await signIn({
      username: email.trim().toLowerCase(),
      password
    });
    return result;
  }

  // Local fallback mock mode for frontend development preview
  if (password === 'fail') {
    throw new Error('Incorrect username or password');
  }
  const mockUser = {
    userId: 'mock-sub-12345',
    username: email,
    attributes: {
      email,
      name: email.split('@')[0],
      'custom:employee_id': 'demo-emp-' + email.slice(0, 5),
      'custom:role': email.includes('admin') ? 'HR Admin' : 'Software Engineer',
      'custom:department': email.includes('admin') ? 'Human Resources' : 'Engineering'
    }
  };
  localStorage.setItem('mock_auth_user', JSON.stringify(mockUser));
  return {
    isSignedIn: true,
    nextStep: { signInStep: 'DONE' }
  };
}

/**
 * Handle new password requirement (first login temporary password flow)
 */
export async function completeNewPassword(newPassword) {
  if (isCognitoConfigured) {
    const result = await confirmSignIn({
      challengeResponse: newPassword
    });
    return result;
  }

  // Mock flow
  return {
    isSignedIn: true,
    nextStep: { signInStep: 'DONE' }
  };
}

/**
 * Sign out
 */
export async function logoutUser() {
  if (isCognitoConfigured) {
    await signOut();
    return;
  }
  localStorage.removeItem('mock_auth_user');
}

/**
 * Get current authenticated user profile & custom attributes
 */
export async function getCurrentUserProfile() {
  if (isCognitoConfigured) {
    try {
      const user = await getCurrentUser();
      const attributes = await fetchUserAttributes();
      return {
        userId: user.userId,
        username: user.username,
        attributes
      };
    } catch (err) {
      return null;
    }
  }

  // Local fallback mock
  const raw = localStorage.getItem('mock_auth_user');
  if (raw) {
    try {
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }
  return null;
}

/**
 * Get access or ID token for API Authorization header
 */
export async function getAuthToken() {
  if (isCognitoConfigured) {
    try {
      const session = await fetchAuthSession();
      return session.tokens?.idToken?.toString() || session.tokens?.accessToken?.toString() || null;
    } catch (err) {
      return null;
    }
  }

  return 'mock-bearer-token';
}
