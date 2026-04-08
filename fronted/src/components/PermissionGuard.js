import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const PermissionGuard = ({
  children,
  allowedRoles,
  permission,
  permissions,
  anyPermissions,
  fallback,
}) => {
  const { user, loading, isAuthorized } = useAuth();

  if (loading) {
    return <div>加载中...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!isAuthorized({ allowedRoles, permission, permissions, anyPermissions })) {
    return fallback !== undefined ? fallback : <Navigate to="/unauthorized" replace />;
  }

  return children;
};

export default PermissionGuard;
