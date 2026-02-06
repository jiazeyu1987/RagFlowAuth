import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import PermissionGuard from './PermissionGuard';

const Layout = ({ children }) => {
  const { user, logout, canUpload, canReview } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  const navigation = [
    { name: 'AI对话', path: '/chat' },
    { name: '搜索', path: '/agents' },
    { name: '文档浏览', path: '/browser' },
    { name: '文档审核', path: '/documents', show: canReview },
    { name: '上传文档', path: '/upload', show: canUpload },
    { name: '修改密码', path: '/change-password' },
    { name: '工具', path: '/tools' },
    { name: '用户管理', path: '/users', allowedRoles: ['admin'] },
    { name: '公司/部门', path: '/org-directory', allowedRoles: ['admin'] },
    { name: '权限组管理', path: '/permission-groups', allowedRoles: ['admin'] },
    { name: '数据安全', path: '/data-security', allowedRoles: ['admin'] },
    { name: '日志', path: '/logs', allowedRoles: ['admin'] },
  ];

  const currentTitle = navigation.find((item) => item.path === location.pathname)?.name || 'Dashboard';

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <aside
        style={{
          width: sidebarOpen ? '250px' : '60px',
          backgroundColor: '#1f2937',
          color: 'white',
          transition: 'width 0.3s',
          display: 'flex',
          flexDirection: 'column',
        }}
        data-testid="layout-sidebar"
      >
        <div
          style={{
            padding: '20px',
            borderBottom: '1px solid #374151',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <h2 style={{ margin: 0, fontSize: sidebarOpen ? '1.5rem' : '0.9rem' }}>
            {sidebarOpen ? '瑛泰知识库' : 'KB'}
          </h2>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            data-testid="layout-sidebar-toggle"
            style={{
              background: 'none',
              border: 'none',
              color: 'white',
              cursor: 'pointer',
              fontSize: '1.2rem',
            }}
            aria-label="toggle sidebar"
          >
            {sidebarOpen ? '◀' : '▶'}
          </button>
        </div>

        <nav style={{ flex: 1, padding: '10px 0' }}>
          {navigation.map((item) => {
            if (item.show !== undefined && !item.show()) return null;

            return (
              <PermissionGuard key={item.path} allowedRoles={item.allowedRoles} fallback={null}>
                <Link
                  to={item.path}
                  data-testid={`nav-${item.path.replace('/', '') || 'home'}`}
                  style={{
                    display: 'block',
                    padding: '12px 20px',
                    color: isActive(item.path) ? '#60a5fa' : '#d1d5db',
                    textDecoration: 'none',
                    backgroundColor: isActive(item.path) ? '#374151' : 'transparent',
                    transition: 'background-color 0.2s',
                    whiteSpace: sidebarOpen ? 'normal' : 'nowrap',
                    overflow: 'hidden',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive(item.path)) e.target.style.backgroundColor = '#374151';
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive(item.path)) e.target.style.backgroundColor = 'transparent';
                  }}
                >
                  {sidebarOpen ? item.name : item.name[0]}
                </Link>
              </PermissionGuard>
            );
          })}
        </nav>

        <div style={{ padding: '20px', borderTop: '1px solid #374151' }}>
          {sidebarOpen && (
            <div style={{ marginBottom: '10px', fontSize: '0.9rem' }}>
              <div style={{ fontWeight: 'bold' }} data-testid="layout-user-name">
                {user?.username}
              </div>
              <div style={{ color: '#9ca3af', fontSize: '0.8rem' }} data-testid="layout-user-role">
                {user?.role}
              </div>
            </div>
          )}
          <button
            onClick={handleLogout}
            data-testid="layout-logout"
            style={{
              width: '100%',
              padding: '8px',
              backgroundColor: '#ef4444',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
            onMouseEnter={(e) => {
              e.target.style.backgroundColor = '#dc2626';
            }}
            onMouseLeave={(e) => {
              e.target.style.backgroundColor = '#ef4444';
            }}
          >
            {sidebarOpen ? '登出' : '⏻'}
          </button>
        </div>
      </aside>

      <main style={{ flex: 1, overflow: 'auto', backgroundColor: '#f9fafb' }}>
        <header
          style={{
            backgroundColor: 'white',
            padding: '16px 24px',
            borderBottom: '1px solid #e5e7eb',
            boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
          }}
        >
          <h1 style={{ margin: 0, fontSize: '1.5rem', color: '#111827' }} data-testid="layout-header-title">
            {currentTitle}
          </h1>
        </header>

        <div style={{ padding: '24px' }}>{children}</div>
      </main>
    </div>
  );
};

export default Layout;
