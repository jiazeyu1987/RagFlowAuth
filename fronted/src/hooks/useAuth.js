import { useState, useEffect, useCallback, createContext, useContext, useRef } from 'react';
import { STORAGE_KEYS } from '../constants/storageKeys';
import authApi from '../features/auth/api';
import tokenStore from '../shared/auth/tokenStore';
import {
  DEFAULT_AUTH_CAPABILITIES,
  DEFAULT_AUTH_PERMISSIONS,
  canWithCapabilities,
  hasAnyRole,
  isAuthorized as evaluateAuthorization,
  isPermissionKeyAllowed,
  normalizeAuthenticatedUser,
} from '../shared/auth/capabilities';

const AuthContext = createContext(null);

const APP_VERSION = '7';

const mapLoginErrorMessage = (message) => {
  const code = String(message || '').trim();
  if (code === 'invalid_username_or_password') {
    return '\u7528\u6237\u540d\u6216\u5bc6\u7801\u9519\u8bef';
  }
  if (code === 'credentials_locked') {
    return '\u8d26\u53f7\u5df2\u88ab\u4e34\u65f6\u9501\u5b9a\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5\u6216\u8054\u7cfb\u7ba1\u7406\u5458';
  }
  if (code === 'account_inactive' || code === 'account_disabled') {
    return '\u8be5\u8d26\u53f7\u5df2\u88ab\u7981\u7528\uff0c\u8bf7\u8054\u7cfb\u7ba1\u7406\u5458';
  }
  if (code === 'missing_refresh_token' || code.startsWith('invalid_refresh_token')) {
    return '\u767b\u5f55\u72b6\u6001\u5df2\u5931\u6548\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55';
  }
  if (code.startsWith('auth_user_invalid_')) {
    return '\u767b\u5f55\u8fd4\u56de\u7684\u6743\u9650\u6570\u636e\u5f02\u5e38\uff0c\u8bf7\u8054\u7cfb\u7ba1\u7406\u5458';
  }
  return code || '\u767b\u5f55\u5931\u8d25';
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [permissions, setPermissions] = useState(DEFAULT_AUTH_PERMISSIONS);
  const [capabilities, setCapabilities] = useState(DEFAULT_AUTH_CAPABILITIES);
  const idleRedirectingRef = useRef(false);
  const currentUserId = user?.user_id;
  const currentIdleTimeoutMinutes = user?.idle_timeout_minutes;
  const accessibleKbs = Array.isArray(user?.accessible_kb_ids) ? user.accessible_kb_ids : [];

  const syncAuthenticatedUserState = useCallback((normalizedUser) => {
    setUser(normalizedUser);
    setPermissions(normalizedUser.permissions);
    setCapabilities(normalizedUser.capabilities);
  }, []);

  const invalidateAuth = useCallback(() => {
    tokenStore.clearAuth();
    setUser(null);
    setPermissions(DEFAULT_AUTH_PERMISSIONS);
    setCapabilities(DEFAULT_AUTH_CAPABILITIES);
  }, []);

  const applyAuthenticatedUser = useCallback((nextUser) => {
    const normalizedUser = normalizeAuthenticatedUser(nextUser);
    tokenStore.setUser(normalizedUser);
    syncAuthenticatedUserState(normalizedUser);
    return normalizedUser;
  }, [syncAuthenticatedUserState]);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        localStorage.removeItem('lastUserRole');
        localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);

        const lastVersion = localStorage.getItem(STORAGE_KEYS.APP_VERSION);
        if (lastVersion !== APP_VERSION) {
          console.log(`[App Version Update] ${lastVersion} -> ${APP_VERSION}, clearing all caches`);
          localStorage.setItem(STORAGE_KEYS.APP_VERSION, APP_VERSION);
          tokenStore.clearAuth();

          if ('caches' in window) {
            try {
              const names = await caches.keys();
              await Promise.all(names.map((name) => caches.delete(name)));
            } catch (cacheError) {
              console.warn('Failed to clear Cache Storage:', cacheError);
            }
          }
        }

        const accessToken = tokenStore.getAccessToken();
        const refreshToken = tokenStore.getRefreshToken();
        const storedUser = accessToken ? tokenStore.getUser() : null;

        if (accessToken) {
          try {
            const currentUser = await authApi.getCurrentUser();
            applyAuthenticatedUser(currentUser);
          } catch (currentUserError) {
            if (!refreshToken) {
              invalidateAuth();
            } else {
              try {
                await authApi.refreshAccessToken();
                const currentUser = await authApi.getCurrentUser();
                applyAuthenticatedUser(currentUser);
              } catch (refreshError) {
                invalidateAuth();
              }
            }
          }
        } else if (refreshToken || storedUser) {
          invalidateAuth();
        }
      } catch (authError) {
        invalidateAuth();
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [applyAuthenticatedUser, invalidateAuth]);

  useEffect(() => {
    if (!currentUserId) {
      idleRedirectingRef.current = false;
      return;
    }
    if (typeof window === 'undefined') return undefined;

    const rawMinutes = Number(currentIdleTimeoutMinutes);
    const idleMinutes = Number.isFinite(rawMinutes) && rawMinutes > 0 ? rawMinutes : 120;
    const idleMs = Math.max(1000, Math.floor(idleMinutes * 60 * 1000));
    let lastActivityAt = Date.now();

    const markActivity = () => {
      lastActivityAt = Date.now();
    };

    const events = ['pointerdown', 'keydown', 'mousemove', 'touchstart', 'scroll', 'wheel'];
    for (const name of events) {
      window.addEventListener(name, markActivity, { passive: true });
    }

    const timer = window.setInterval(() => {
      if (Date.now() - lastActivityAt < idleMs) return;
      if (idleRedirectingRef.current) return;
      idleRedirectingRef.current = true;
      invalidateAuth();
      if (String(window.location?.pathname || '') !== '/login') {
        window.location.assign('/login');
      }
    }, 1000);

    return () => {
      window.clearInterval(timer);
      for (const name of events) {
        window.removeEventListener(name, markActivity);
      }
    };
  }, [currentUserId, currentIdleTimeoutMinutes, invalidateAuth]);

  const login = async (username, password) => {
    try {
      setError(null);
      const data = await authApi.login(username, password);
      const normalizedUser = normalizeAuthenticatedUser(data.user);
      tokenStore.setAuth(data.access_token, data.refresh_token, normalizedUser);
      console.log('[Login] Logged in user:', normalizedUser);
      syncAuthenticatedUserState(normalizedUser);
      return { success: true, user: normalizedUser };
    } catch (loginError) {
      const message = mapLoginErrorMessage(loginError?.message);
      setError(message);
      return { success: false, error: message };
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
      setError(null);
    } catch (logoutError) {
      setError(logoutError.message);
    } finally {
      invalidateAuth();
    }
  };

  const hasRole = useCallback((roles) => hasAnyRole(user, roles), [user]);
  const isAdmin = useCallback(() => user?.role === 'admin', [user]);
  const isSubAdmin = useCallback(() => user?.role === 'sub_admin', [user]);
  const can = useCallback((resource, action, target = null) => {
    if (!user) return false;
    return canWithCapabilities(capabilities, resource, action, target);
  }, [user, capabilities]);
  const canByPermissionKey = useCallback((key, target = null) => {
    if (!user) return false;
    return isPermissionKeyAllowed(capabilities, key, target);
  }, [user, capabilities]);
  const isReviewer = useCallback(() => canByPermissionKey('canReview'), [canByPermissionKey]);
  const isOperator = useCallback(
    () => canByPermissionKey('canUpload') || canByPermissionKey('canReview'),
    [canByPermissionKey]
  );
  const canManageKnowledgeTree = useCallback(
    () => canByPermissionKey('canManageKbDirectory'),
    [canByPermissionKey]
  );
  const canAccessKb = useCallback((kbId) => can('kb_documents', 'view', kbId), [can]);
  const isAuthorized = useCallback((options = {}) => evaluateAuthorization({
    user,
    capabilities,
    allowedRoles: options.allowedRoles,
    permission: options.permission,
    permissions: options.permissions,
    anyPermissions: options.anyPermissions,
    permissionKey: options.permissionKey,
    permissionKeys: options.permissionKeys,
    anyPermissionKeys: options.anyPermissionKeys,
  }), [user, capabilities]);

  const value = {
    user,
    loading,
    error,
    login,
    logout,
    hasRole,
    isAdmin,
    isSubAdmin,
    isReviewer,
    isOperator,
    canManageKnowledgeTree,
    can,
    accessibleKbs,
    canAccessKb,
    permissions,
    capabilities,
    isAuthorized,
    managedKbRootNodeId: user?.managed_kb_root_node_id || null,
    managedKbRootPath: user?.managed_kb_root_path || null,
    canUpload: () => canByPermissionKey('canUpload'),
    canReview: () => canByPermissionKey('canReview'),
    canDownload: () => canByPermissionKey('canDownload'),
    canCopy: () => canByPermissionKey('canCopy'),
    canDelete: () => canByPermissionKey('canDelete'),
    canManageKbDirectory: () => canByPermissionKey('canManageKbDirectory'),
    canViewKbConfig: () => canByPermissionKey('canViewKbConfig'),
    canViewTools: () => canByPermissionKey('canViewTools'),
    canAccessTool: (toolId) => canByPermissionKey('canViewTools', toolId),
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
