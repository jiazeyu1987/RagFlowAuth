import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useRuntimeFeatureFlags } from '../hooks/useRuntimeFeatureFlags';

const FeatureVisibilityGuard = ({ children, flagKey, fallbackPath = '/unauthorized' }) => {
  const { isSuperAdmin } = useAuth();
  const { loading, flags } = useRuntimeFeatureFlags();

  if (loading) {
    return <div>加载中...</div>;
  }

  const visible = flags?.[flagKey] !== false;
  if (!visible && !isSuperAdmin()) {
    return <Navigate to={fallbackPath} replace />;
  }

  return children;
};

export default FeatureVisibilityGuard;
