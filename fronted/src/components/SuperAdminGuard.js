import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const SuperAdminGuard = ({ children, fallbackPath = '/unauthorized' }) => {
  const { loading, user, isSuperAdmin } = useAuth();

  if (loading) {
    return <div>加载中...</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (!isSuperAdmin()) {
    return <Navigate to={fallbackPath} replace />;
  }
  return children;
};

export default SuperAdminGuard;
