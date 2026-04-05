import { useState, useEffect, useCallback, createContext, useContext, useRef } from 'react';
import authApi from '../api/auth/authApi';
import { STORAGE_KEYS } from '../constants/storageKeys';
import { meApi } from '../features/me/api';
import tokenStore from '../shared/auth/tokenStore';

const AuthContext = createContext(null);

const APP_VERSION = '7';

const createDefaultPermissions = () => ({
  can_upload: false,
  can_review: false,
  can_download: false,
  can_copy: false,
  can_delete: false,
  can_manage_kb_directory: false,
  can_view_kb_config: false,
  can_view_tools: false,
  accessible_tools: []
});

const mapLoginErrorMessage = (message) => {
  const code = String(message || '').trim();
  if (code === 'invalid_username_or_password') {
    return '用户名或密码错误';
  }
  if (code === 'credentials_locked') {
    return '账号已被临时锁定，请稍后再试或联系管理员';
  }
  if (code === 'account_inactive' || code === 'account_disabled') {
    return '该账号已被禁用，请联系管理员';
  }
  if (code === 'missing_refresh_token' || code.startsWith('invalid_refresh_token')) {
    return '登录状态已失效，请重新登录';
  }
  return code || '登录失败';
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
  const [accessibleKbs, setAccessibleKbs] = useState([]);
  const [permissions, setPermissions] = useState(createDefaultPermissions);
  const idleRedirectingRef = useRef(false);
  const currentUserId = user?.user_id;
  const currentIdleTimeoutMinutes = user?.idle_timeout_minutes;

  const invalidateAuth = useCallback(() => {
    tokenStore.clearAuth();
    setUser(null);
    setAccessibleKbs([]);
    setPermissions(createDefaultPermissions());
  }, []);

  const applyAuthenticatedUser = useCallback((nextUser) => {
    tokenStore.setUser(nextUser);
    setUser(nextUser);
    setPermissions(nextUser?.permissions ? nextUser.permissions : createDefaultPermissions());
  }, []);

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
      } catch (error) {
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
    if (typeof window === 'undefined') return;

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

  useEffect(() => {
    const fetchAccessibleKbs = async () => {
      if (user) {
        try {
          const data = await meApi.listMyKnowledgeBases();
          setAccessibleKbs(data.kb_ids || []);
        } catch (fetchError) {
          console.error('Failed to fetch accessible KBs:', fetchError);
          setAccessibleKbs([]);
        }
      } else {
        setAccessibleKbs([]);
      }
    };

    fetchAccessibleKbs();
  }, [user]);

  const login = async (username, password) => {
    try {
      setError(null);
      const data = await authApi.login(username, password);
      tokenStore.setAuth(data.access_token, data.refresh_token, data.user);
      console.log('[Login] Logged in user:', data.user);
      applyAuthenticatedUser(data.user);
      return { success: true };
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

  const hasRole = (roles) => {
    if (!user) return false;
    if (Array.isArray(roles)) {
      return roles.includes(user.role);
    }
    return user.role === roles;
  };

  const isAdmin = () => user?.role === 'admin';
  const isSubAdmin = () => user?.role === 'sub_admin';
  const isReviewer = () => user?.role === 'admin' || !!permissions.can_review;
  const isOperator = () => user?.role === 'admin' || !!permissions.can_upload || !!permissions.can_review;
  const canManageKnowledgeTree = () => user?.role === 'admin' || !!permissions.can_manage_kb_directory;

  const can = useCallback((resource, action, target = null) => {
    if (!user) return false;

    const ops = permissions || {};

    if (resource === 'users') {
      return user.role === 'admin' || user.role === 'sub_admin';
    }

    if (resource === 'kb_documents') {
      if (action === 'view') return accessibleKbs.length > 0;
      if (action === 'upload') return user.role === 'admin' || !!ops.can_upload;
      if (action === 'review' || action === 'approve' || action === 'reject') return user.role === 'admin' || !!ops.can_review;
      if (action === 'delete') return user.role === 'admin' || !!ops.can_delete;
      if (action === 'download') return user.role === 'admin' || !!ops.can_download;
      if (action === 'copy') return user.role === 'admin' || !!ops.can_copy;
      return false;
    }

    if (resource === 'ragflow_documents') {
      if (action === 'view' || action === 'preview') return accessibleKbs.length > 0;
      if (action === 'download') return user.role === 'admin' || !!ops.can_download;
      if (action === 'copy') return user.role === 'admin' || !!ops.can_copy;
      if (action === 'delete') return user.role === 'admin' || !!ops.can_delete;
      return false;
    }

    if (resource === 'kb_directory') {
      if (action === 'manage') return user.role === 'admin' || !!ops.can_manage_kb_directory;
      return false;
    }

    if (resource === 'kbs_config') {
      if (action === 'view') return user.role === 'admin' || ops.can_view_kb_config !== false;
      return false;
    }

    if (resource === 'tools') {
      if (action !== 'view') return false;
      if (user.role === 'admin') return true;
      if (ops.can_view_tools === false) return false;
      const allowedTools = Array.isArray(ops.accessible_tools)
        ? ops.accessible_tools
            .map((item) => String(item || '').trim())
            .filter((item) => !!item)
        : [];
      if (!target) return true;
      if (allowedTools.length === 0) return true;
      return allowedTools.includes(String(target));
    }

    return false;
  }, [user, permissions, accessibleKbs]);

  const canAccessKb = useCallback((kbId) => {
    if (!user) return false;
    return accessibleKbs.includes(kbId);
  }, [user, accessibleKbs]);

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
    managedKbRootNodeId: user?.managed_kb_root_node_id || null,
    managedKbRootPath: user?.managed_kb_root_path || null,
    canUpload: () => user?.role === 'admin' || !!permissions.can_upload,
    canReview: () => user?.role === 'admin' || !!permissions.can_review,
    canDownload: () => user?.role === 'admin' || !!permissions.can_download,
    canCopy: () => user?.role === 'admin' || !!permissions.can_copy,
    canDelete: () => user?.role === 'admin' || !!permissions.can_delete,
    canManageKbDirectory: () => user?.role === 'admin' || !!permissions.can_manage_kb_directory,
    canViewKbConfig: () => user?.role === 'admin' || permissions.can_view_kb_config !== false,
    canViewTools: () => user?.role === 'admin' || permissions.can_view_tools !== false,
    canAccessTool: (toolId) => can('tools', 'view', toolId),
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
