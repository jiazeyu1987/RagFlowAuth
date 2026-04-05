import { useState, useEffect, useCallback, createContext, useContext, useRef } from 'react';
import authClient from '../api/authClient';
import { STORAGE_KEYS } from '../constants/storageKeys';
import { meApi } from '../features/me/api';
import tokenStore from '../shared/auth/tokenStore';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// 应用版本号。权限或文案更新后递增，用于强制清理旧缓存。
const APP_VERSION = '7';

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

export const AuthProvider = ({ children }) => {
  // 使用当前登录用户信息，等待 checkAuth 完成后再落定。
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [accessibleKbs, setAccessibleKbs] = useState([]);
  const [permissions, setPermissions] = useState({
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
  const idleRedirectingRef = useRef(false);
  const currentUserId = user?.user_id;
  const currentIdleTimeoutMinutes = user?.idle_timeout_minutes;

  const invalidateAuth = useCallback(() => {
    authClient.clearAuth();
    setUser(null);
    setAccessibleKbs([]);
    setPermissions({
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
  }, []);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        // 迁移或清理旧 key，避免跨账号角色缓存相互污染。
        localStorage.removeItem('lastUserRole');
        localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);

        // 检查应用版本。
        const lastVersion = localStorage.getItem(STORAGE_KEYS.APP_VERSION);
        if (lastVersion !== APP_VERSION) {
          console.log(`[App Version Update] ${lastVersion} -> ${APP_VERSION}, clearing all caches`);
          localStorage.setItem(STORAGE_KEYS.APP_VERSION, APP_VERSION);

          // 清除所有认证相关的 localStorage 数据。
          tokenStore.clearAuth();

          // 清除 Cache Storage。
          if ('caches' in window) {
            try {
              const names = await caches.keys();
              await Promise.all(names.map((name) => caches.delete(name)));
            } catch (e) {
              console.warn('Failed to clear Cache Storage:', e);
            }
          }
        }

        // 检查是否已有可用令牌。
        if (authClient.accessToken) {
          try {
            const currentUser = await authClient.getCurrentUser();
            // 更新当前用户信息。
            authClient.setAuth(authClient.accessToken, authClient.refreshToken, currentUser);
            setUser(currentUser);
            // 更新权限组操作权限。
            if (currentUser.permissions) {
              setPermissions(currentUser.permissions);
            }
          } catch (err) {
            // 令牌可能已过期，尝试刷新。
            if (authClient.refreshToken) {
              try {
                await authClient.refreshAccessToken();
                const currentUser = await authClient.getCurrentUser();
                setUser(currentUser);
                // 更新权限组操作权限。
                if (currentUser.permissions) {
                  setPermissions(currentUser.permissions);
                }
              } catch (refreshErr) {
                invalidateAuth();
              }
            } else {
              invalidateAuth();
            }
          }
        } else {
          if (authClient.user) {
            invalidateAuth();
          }
        }
      } catch (err) {
        invalidateAuth();
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [invalidateAuth]);

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

  // 加载用户可访问的知识库列表。
  useEffect(() => {
    const fetchAccessibleKbs = async () => {
      if (user) {
        try {
          const data = await meApi.listMyKnowledgeBases();
          setAccessibleKbs(data.kb_ids || []);
        } catch (err) {
          console.error('Failed to fetch accessible KBs:', err);
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
      const data = await authClient.login(username, password);
      // 新后端的 login 已在内部调用 /me 并写入 user。
      console.log('[Login] Logged in user:', data.user);
      setUser(data.user);
      // 更新权限组操作权限。
      if (data.user.permissions) {
        setPermissions(data.user.permissions);
      }
      return { success: true };
    } catch (err) {
      const message = mapLoginErrorMessage(err?.message);
      setError(message);
      return { success: false, error: message };
    }
  };

  const logout = async () => {
    try {
      await authClient.logout();
      setUser(null);
      setError(null);
    } catch (err) {
      setError(err.message);
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

  /**
   * 前端 UI 权限检查。
   * 后端以权限组 resolver 为准，这里只用于 UI 显示控制。
   */
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
      // 说明：查看/预览不等于下载。
      // 目标：没有下载权限的用户也可以查看预览，但不能直接下载。
      // 后端仍会在下载接口做最终权限校验。
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

  /**
   * 检查用户是否有某个知识库的访问权限。
   * @param {string} kbId - 知识库 ID
   * @returns {boolean} 是否有权限
   */
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
