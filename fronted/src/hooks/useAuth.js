import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import authClient from '../api/authClient';
import { STORAGE_KEYS } from '../constants/storageKeys';
import tokenStore from '../shared/auth/tokenStore';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// 应用版本号，每次更新权限相关代码时递增
const APP_VERSION = '6';  // 强制清除所有缓存

export const AuthProvider = ({ children }) => {
  // 使用新的令牌名称
  const [user, setUser] = useState(null);  // 初始为null，等待checkAuth完成
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [accessibleKbs, setAccessibleKbs] = useState([]);  // 用户可访问的知识库列表
  const [permissions, setPermissions] = useState({  // 权限组操作权限
    can_upload: false,
    can_review: false,
    can_download: false,
    can_delete: false
  });

  const invalidateAuth = useCallback(() => {
    authClient.clearAuth();
    setUser(null);
    setAccessibleKbs([]);
    setPermissions({
      can_upload: false,
      can_review: false,
      can_download: false,
      can_delete: false
    });
  }, []);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        // 迁移/清理旧 key，避免跨账号角色缓存干扰
        localStorage.removeItem('lastUserRole');
        localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);  // 清除旧令牌

        // 检查应用版本
        const lastVersion = localStorage.getItem(STORAGE_KEYS.APP_VERSION);
        if (lastVersion !== APP_VERSION) {
          console.log(`[App Version Update] ${lastVersion} -> ${APP_VERSION}, clearing all caches`);
          localStorage.setItem(STORAGE_KEYS.APP_VERSION, APP_VERSION);

          // 清除所有认证相关的localStorage数据
          tokenStore.clearAuth();

          // 清除Cache Storage
          if ('caches' in window) {
            try {
              const names = await caches.keys();
              await Promise.all(names.map((name) => caches.delete(name)));
            } catch (e) {
              console.warn('Failed to clear Cache Storage:', e);
            }
          }
        }

        // 检查是否有新的访问令牌
        if (authClient.accessToken) {
          try {
            const currentUser = await authClient.getCurrentUser();
            // 更新用户信息
            authClient.setAuth(authClient.accessToken, authClient.refreshToken, currentUser);
            setUser(currentUser);
            // 更新权限组操作权限
            if (currentUser.permissions) {
              setPermissions(currentUser.permissions);
            }
          } catch (err) {
            // 令牌可能已过期，尝试刷新
            if (authClient.refreshToken) {
              try {
                await authClient.refreshAccessToken();
                const currentUser = await authClient.getCurrentUser();
                setUser(currentUser);
                // 更新权限组操作权限
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

  // 加载用户的知识库权限
  useEffect(() => {
    const fetchAccessibleKbs = async () => {
      if (user) {
        try {
          const data = await authClient.getMyKnowledgeBases();
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
      // 新后端的 login 方法已经在内部调用了 /me 并设置 user
      console.log('[Login] Logged in user:', data.user);
      setUser(data.user);
      // 更新权限组操作权限
      if (data.user.permissions) {
        setPermissions(data.user.permissions);
      }
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
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
  const isReviewer = () => user?.role === 'admin' || permissions.can_review;
  const isOperator = () => user?.role === 'admin' || permissions.can_upload || permissions.can_review;

  /**
   * 前端 UI 权限检查（同步）
   * 后端以权限组/resolver 为准；这里只用于 UI 显示控制。
   */
  const can = useCallback((resource, action) => {
    if (!user) return false;
    if (user.role === 'admin') return true;

    const ops = permissions || {};

    if (resource === 'users') {
      return false;
    }

    if (resource === 'kb_documents') {
      if (action === 'view') return accessibleKbs.length > 0;
      if (action === 'upload') return !!ops.can_upload;
      if (action === 'review' || action === 'approve' || action === 'reject') return !!ops.can_review;
      if (action === 'delete') return !!ops.can_delete;
      if (action === 'download') return !!ops.can_download;
      return false;
    }

    if (resource === 'ragflow_documents') {
      // 说明：查看/预览不等于下载。
      // 目标：无下载权限的用户也可以“查看/预览”，但不能“下载”。
      // 后端仍会做最终权限校验（下载接口需要 can_download）。
      if (action === 'view' || action === 'preview') return accessibleKbs.length > 0;
      if (action === 'download') return !!ops.can_download;
      if (action === 'delete') return !!ops.can_delete;
      return false;
    }

    return false;
  }, [user, permissions, accessibleKbs]);

  /**
   * 检查用户是否有某个知识库的访问权限
   * @param {string} kbId - 知识库ID
   * @returns {boolean} 是否有权限
   */
  const canAccessKb = useCallback((kbId) => {
    if (!user) return false;
    if (user.role === 'admin') return true;  // 管理员自动拥有所有权限
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
    isReviewer,
    isOperator,
    can,
    accessibleKbs,      // 用户可访问的知识库列表
    canAccessKb,        // 知识库权限检查方法
    permissions,        // 权限组操作权限
    canUpload: () => user?.role === 'admin' || permissions.can_upload,
    canReview: () => user?.role === 'admin' || permissions.can_review,
    canDownload: () => user?.role === 'admin' || permissions.can_download,
    canDelete: () => user?.role === 'admin' || permissions.can_delete,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
