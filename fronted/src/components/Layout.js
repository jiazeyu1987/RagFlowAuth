import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import PermissionGuard from './PermissionGuard';

const MOBILE_BREAKPOINT = 768;

const Layout = ({ children }) => {
  const {
    user,
    logout,
    canUpload,
    canReview,
    canViewKbConfig,
    canViewTools,
  } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window === 'undefined') return true;
    return window.innerWidth > MOBILE_BREAKPOINT;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => {
      const mobile = window.innerWidth <= MOBILE_BREAKPOINT;
      setIsMobile(mobile);
      setSidebarOpen((prev) => {
        if (mobile) return false;
        return prev === false ? true : prev;
      });
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const permissionGroupLabel = (() => {
    const groups = (user?.permission_groups || [])
      .map((group) => (group && typeof group.group_name === 'string' ? group.group_name.trim() : ''))
      .filter(Boolean);
    const unique = Array.from(new Set(groups));
    if (unique.length > 0) return unique.join(' / ');
    return user?.role || '';
  })();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const isActive = (path) => {
    if (location.pathname === path) return true;
    if (path === '/tools' && location.pathname.startsWith('/tools/')) return true;
    return false;
  };

  const handleNavigate = () => {
    if (isMobile) setSidebarOpen(false);
  };

  const navigation = [
    { name: '智能对话', path: '/chat', icon: '💬' },
    { name: '全库搜索', path: '/agents', icon: '🔎' },
    { name: '知识配置', path: '/kbs', icon: '📚', show: canViewKbConfig },
    { name: '文档浏览', path: '/browser', icon: '📄' },
    { name: '文档审核', path: '/documents', icon: '✅', show: canReview },
    { name: '文档上传', path: '/upload', icon: '📤', show: canUpload },
    { name: '修改密码', path: '/change-password', icon: '🔐' },
    { name: '实用工具', path: '/tools', icon: '🧰', show: canViewTools },
    { name: '用户管理', path: '/users', icon: '👤', allowedRoles: ['admin'] },
    { name: '组织管理', path: '/org-directory', icon: '🏢', allowedRoles: ['admin'] },
    { name: '权限分组', path: '/permission-groups', icon: '🛡️', allowedRoles: ['admin'] },
    { name: '数据安全', path: '/data-security', icon: '🔒', allowedRoles: ['admin'] },
    { name: '日志审计', path: '/logs', icon: '🧾', allowedRoles: ['admin'] },
  ];

  const pageTitleOverrides = {
    '/tools/patent-download': '专利下载',
    '/tools/paper-download': '论文下载',
    '/tools/nas-browser': 'NAS云盘',
    '/tools/drug-admin': '药监导航',
    '/tools/nmpa': 'NMPA',
    '/tools/package-drawing': '包装图纸',
  };

  const currentTitle = pageTitleOverrides[location.pathname]
    || navigation.find((item) => item.path === location.pathname)?.name
    || '首页';

  const sidebarWidth = isMobile ? 'min(78vw, 280px)' : (sidebarOpen ? '250px' : '60px');
  const headerPadding = isMobile ? '14px 16px' : '16px 24px';
  const contentPadding = isMobile ? '16px' : '24px';

  return (
    <div style={{ display: 'flex', height: '100vh', position: 'relative', overflow: 'hidden' }}>
      {isMobile && sidebarOpen ? (
        <button
          type="button"
          aria-label="close sidebar overlay"
          onClick={() => setSidebarOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            border: 'none',
            backgroundColor: 'rgba(15, 23, 42, 0.42)',
            zIndex: 20,
            padding: 0,
          }}
        />
      ) : null}

      <aside
        style={{
          width: sidebarWidth,
          minWidth: sidebarWidth,
          backgroundColor: '#1f2937',
          color: 'white',
          transition: 'transform 0.3s ease, width 0.3s ease',
          display: 'flex',
          flexDirection: 'column',
          position: isMobile ? 'fixed' : 'relative',
          top: 0,
          left: 0,
          bottom: 0,
          zIndex: isMobile ? 30 : 1,
          transform: isMobile ? (sidebarOpen ? 'translateX(0)' : 'translateX(-100%)') : 'none',
          boxShadow: isMobile && sidebarOpen ? '0 20px 50px rgba(0, 0, 0, 0.28)' : 'none',
        }}
        data-testid="layout-sidebar"
      >
        <div
          style={{
            padding: isMobile ? '16px' : '20px',
            borderBottom: '1px solid #374151',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <h2 style={{ margin: 0, fontSize: sidebarOpen ? (isMobile ? '1.2rem' : '1.5rem') : '0.9rem' }}>
            {sidebarOpen ? '知识库系统' : 'KB'}
          </h2>
          <button
            type="button"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            data-testid="layout-sidebar-toggle"
            style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', fontSize: '1.2rem' }}
            aria-label="toggle sidebar"
          >
            {sidebarOpen ? '<' : '>'}
          </button>
        </div>

        <nav style={{ flex: 1, padding: '10px 0', overflowY: 'auto' }}>
          {navigation.map((item) => {
            if (item.show !== undefined && !item.show()) return null;

            return (
              <PermissionGuard key={item.path} allowedRoles={item.allowedRoles} fallback={null}>
                <Link
                  to={item.path}
                  data-testid={`nav-${item.path.replace('/', '') || 'home'}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: sidebarOpen ? 'flex-start' : 'center',
                    gap: sidebarOpen ? '10px' : '0px',
                    padding: sidebarOpen ? '12px 20px' : '12px 0px',
                    color: isActive(item.path) ? '#60a5fa' : '#d1d5db',
                    textDecoration: 'none',
                    backgroundColor: isActive(item.path) ? '#374151' : 'transparent',
                    transition: 'background-color 0.2s',
                    whiteSpace: sidebarOpen ? 'normal' : 'nowrap',
                    overflow: 'hidden',
                  }}
                  onClick={handleNavigate}
                  onMouseEnter={(e) => {
                    if (!isActive(item.path)) e.currentTarget.style.backgroundColor = '#374151';
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive(item.path)) e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  <span
                    aria-hidden
                    style={{
                      width: '24px',
                      textAlign: 'center',
                      fontSize: sidebarOpen ? '1.05rem' : '1.15rem',
                      lineHeight: 1,
                      flexShrink: 0,
                    }}
                    title={item.name}
                  >
                    {item.icon || '-'}
                  </span>
                  {sidebarOpen ? <span style={{ flex: 1 }}>{item.name}</span> : null}
                </Link>
              </PermissionGuard>
            );
          })}
        </nav>

        <div style={{ padding: isMobile ? '16px' : '20px', borderTop: '1px solid #374151' }}>
          {sidebarOpen ? (
            <div style={{ marginBottom: '10px', fontSize: '0.9rem' }}>
              <div style={{ fontWeight: 'bold' }} data-testid="layout-user-name">{user?.username}</div>
              <div style={{ color: '#9ca3af', fontSize: '0.8rem' }} data-testid="layout-user-role">{permissionGroupLabel}</div>
            </div>
          ) : null}
          <button
            type="button"
            onClick={handleLogout}
            data-testid="layout-logout"
            style={{ width: '100%', padding: '8px', backgroundColor: '#ef4444', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#dc2626';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#ef4444';
            }}
          >
            {sidebarOpen ? '退出' : 'X'}
          </button>
        </div>
      </aside>

      <main style={{ flex: 1, overflow: 'auto', backgroundColor: '#f9fafb', width: '100%' }}>
        <header
          style={{
            backgroundColor: 'white',
            padding: headerPadding,
            borderBottom: '1px solid #e5e7eb',
            boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          {isMobile ? (
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              data-testid="layout-mobile-menu-toggle"
              style={{
                border: '1px solid #d1d5db',
                backgroundColor: 'white',
                color: '#111827',
                borderRadius: '10px',
                padding: '8px 10px',
                fontSize: '1rem',
                lineHeight: 1,
                cursor: 'pointer',
                flexShrink: 0,
              }}
              aria-label="open sidebar"
            >
              ☰
            </button>
          ) : null}
          <h1
            style={{ margin: 0, fontSize: isMobile ? '1.2rem' : '1.5rem', color: '#111827', wordBreak: 'break-word' }}
            data-testid="layout-header-title"
          >
            {currentTitle}
          </h1>
        </header>

        <div style={{ padding: contentPadding }}>{children}</div>
      </main>
    </div>
  );
};

export default Layout;
