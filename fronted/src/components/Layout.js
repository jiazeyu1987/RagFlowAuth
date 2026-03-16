import React, { useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useRuntimeFeatureFlags } from '../hooks/useRuntimeFeatureFlags';
import PermissionGuard from './PermissionGuard';
import './Layout.css';

const roleLabel = (user) => {
  if (user?.is_super_admin || String(user?.username || '').toLowerCase() === 'superadmin') return '超级管理员';
  const role = String(user?.role || '').trim().toLowerCase();
  if (role === 'admin') return '管理员';
  if (role === 'reviewer') return '审核员';
  if (role === 'operator') return '操作员';
  if (role === 'user') return '普通用户';
  return user?.role || '';
};

const Layout = ({ children }) => {
  const { user, logout, canUpload, canReview, isSuperAdmin } = useAuth();
  const { flags } = useRuntimeFeatureFlags();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const permissionGroupLabel = useMemo(() => {
    const groups = (user?.permission_groups || [])
      .map((g) => (g && typeof g.group_name === 'string' ? g.group_name.trim() : ''))
      .filter(Boolean);
    const unique = Array.from(new Set(groups));
    if (unique.length > 0) return unique.join(' / ');
    return roleLabel(user);
  }, [user]);

  const canSee = (flagKey) => isSuperAdmin() || flags?.[flagKey] !== false;

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const isActive = (path) => {
    if (location.pathname === path) return true;
    if (path === '/tools' && location.pathname.startsWith('/tools/')) return true;
    return false;
  };

  const navigation = [
    { name: '智能对话', path: '/chat' },
    { name: '全文检索', path: '/agents' },
    { name: '知识库配置', path: '/kbs' },
    { name: '文档浏览', path: '/browser' },
    { name: '文档审核', path: '/documents', show: canReview },
    { name: '文档上传', path: '/upload', show: canUpload },
    { name: '修改密码', path: '/change-password' },
    { name: '实用工具', path: '/tools' },
    { name: '用户管理', path: '/users', allowedRoles: ['admin'] },
    { name: '组织管理', path: '/org-directory', allowedRoles: ['admin'] },
    { name: '权限分组', path: '/permission-groups', allowedRoles: ['admin'] },
    { name: '数据安全', path: '/data-security', allowedRoles: ['admin'] },
    {
      name: '日志审计',
      path: '/logs',
      allowedRoles: ['admin'],
      show: () => canSee('page_logs_visible'),
    },
    {
      name: '功能隐藏控制',
      path: '/super-admin/features',
      allowedRoles: ['admin'],
      show: () => isSuperAdmin(),
    },
  ];

  const pageTitleOverrides = {
    '/tools/patent-download': '专利下载分析',
    '/tools/paper-download': '论文下载分析',
    '/tools/paper-workspace': '论文工作台',
    '/tools/collection-workbench': '采集工作台',
    '/tools/nas-browser': 'NAS 网盘',
    '/tools/drug-admin': '药监导航',
    '/tools/nmpa': 'NMPA 专用工具',
    '/super-admin/features': '功能隐藏控制',
  };

  const currentTitle =
    pageTitleOverrides[location.pathname] ||
    navigation.find((item) => item.path === location.pathname)?.name ||
    '系统首页';

  const currentDate = new Date().toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className={`med-layout ${sidebarOpen ? 'is-expanded' : 'is-collapsed'}`}>
      <main className="med-main">
        <header className="med-header">
          <div className="med-header__left">
            <h1 className="med-header__title" data-testid="layout-header-title">
              {currentTitle}
            </h1>
            <p className="med-header__subtitle">{'\u7cbe\u795e\u5fc3\u7406\u9886\u57df\u6570\u636e\u5e93\u667a\u80fd\u5206\u6790\u7cfb\u7edf'}</p>
          </div>
          <div className="med-header__right">
            <span className="med-header__time">{currentDate}</span>
            <div data-testid="super-admin-credential-banner" className="med-super-admin-banner">
              {'\u6d4b\u8bd5\u8d85\u7ea7\u7ba1\u7406\u5458\u8d26\u53f7\uff1a'}SuperAdmin / SuperAdmin
            </div>
          </div>
        </header>

        <div className="med-content">{children}</div>
      </main>

      <aside className="med-sidebar" data-testid="layout-sidebar">
        <div className="med-sidebar__head">
          <div className="med-brand">
            <div className="med-sidebar__eyebrow">{sidebarOpen ? '\u4e3b\u63a7\u5236\u533a' : '\u63a7'}</div>
            <h2 className="med-brand__title">{sidebarOpen ? '\u7cbe\u795e\u5fc3\u7406\u6570\u636e\u5e93' : '\u7cbe\u5fc3\u5e93'}</h2>
            {sidebarOpen && <p className="med-brand__subtitle">{'\u4e34\u5e8a\u77e5\u8bc6\u4e0e\u667a\u80fd\u5206\u6790\u5e73\u53f0'}</p>}
          </div>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            data-testid="layout-sidebar-toggle"
            className="med-sidebar__toggle"
            aria-label="\u5207\u6362\u4fa7\u8fb9\u680f"
            type="button"
          >
            {sidebarOpen ? '\u6536' : '\u5c55'}
          </button>
        </div>

        {sidebarOpen && (
          <div className="med-sidebar__hint">
            {'\u4e34\u5e8a\u5e38\u7528\u5165\u53e3\u96c6\u4e2d\u5728\u6b64\u5904\uff0c\u53ef\u6309\u5de5\u4f5c\u6d41\u7a0b\u5feb\u901f\u5207\u6362\u3002'}
          </div>
        )}

        <nav className="med-nav">
          {navigation.map((item) => {
            if (item.show && !item.show()) return null;

            return (
              <PermissionGuard key={item.path} allowedRoles={item.allowedRoles} fallback={null}>
                <Link
                  to={item.path}
                  data-testid={`nav-${item.path.replace('/', '') || 'home'}`}
                  className={`med-nav__link ${isActive(item.path) ? 'is-active' : ''}`}
                >
                  <span className="med-nav__icon" aria-hidden />
                  {sidebarOpen && <span className="med-nav__label">{item.name}</span>}
                </Link>
              </PermissionGuard>
            );
          })}
        </nav>

        <div className="med-sidebar__footer">
          {sidebarOpen && (
            <div className="med-user-card">
              <div className="med-user-card__name" data-testid="layout-user-name">
                {user?.username}
              </div>
              <div className="med-user-card__role" data-testid="layout-user-role">
                {permissionGroupLabel}
              </div>
            </div>
          )}
          <button
            onClick={handleLogout}
            data-testid="layout-logout"
            className="med-logout-btn"
            type="button"
          >
            {sidebarOpen ? '\u9000\u51fa\u767b\u5f55' : '\u9000'}
          </button>
        </div>
      </aside>
    </div>
  );
};

export default Layout;
