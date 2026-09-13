import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  loginUser,
  completeNewPassword,
  logoutUser,
  getCurrentUserProfile,
  isCognitoConfigured
} from './cognito';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [requireNewPassword, setRequireNewPassword] = useState(false);
  const [pendingEmail, setPendingEmail] = useState('');

  const loadSession = useCallback(async () => {
    try {
      setLoading(true);
      const profile = await getCurrentUserProfile();
      if (profile) {
        setUser(profile);
      } else {
        setUser(null);
      }
    } catch (err) {
      console.error('Failed to load session:', err);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  const login = async (email, password) => {
    try {
      const result = await loginUser(email, password);

      if (result.nextStep?.signInStep === 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED') {
        setRequireNewPassword(true);
        setPendingEmail(email);
        return { requireNewPassword: true };
      }

      setRequireNewPassword(false);
      setPendingEmail('');
      await loadSession();
      return { success: true };
    } catch (err) {
      throw err;
    }
  };

  const confirmPassword = async (newPassword) => {
    try {
      await completeNewPassword(newPassword);
      setRequireNewPassword(false);
      setPendingEmail('');
      await loadSession();
      return { success: true };
    } catch (err) {
      throw err;
    }
  };

  const logout = async () => {
    try {
      await logoutUser();
      setUser(null);
      setRequireNewPassword(false);
      setPendingEmail('');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  // Helper getters for custom attributes
  const employeeId = user?.attributes?.['custom:employee_id'] || user?.attributes?.employee_id || '';
  const role = user?.attributes?.['custom:role'] || user?.attributes?.role || 'Employee';
  const department = user?.attributes?.['custom:department'] || user?.attributes?.department || 'General';
  const name = user?.attributes?.name || user?.username || 'Employee';
  const email = user?.attributes?.email || user?.username || '';

  // Manual demo override for local testing when needed
  const setDemoEmployeeId = (newId) => {
    if (user) {
      const updated = {
        ...user,
        attributes: {
          ...user.attributes,
          'custom:employee_id': newId
        }
      };
      setUser(updated);
      localStorage.setItem('mock_auth_user', JSON.stringify(updated));
    }
  };

  const value = {
    user,
    employeeId,
    role,
    department,
    name,
    email,
    loading,
    requireNewPassword,
    pendingEmail,
    isCognitoConfigured,
    login,
    confirmPassword,
    logout,
    refreshSession: loadSession,
    setDemoEmployeeId
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
