import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import operationApprovalApi from '../features/operationApproval/api';
import { useAuth } from '../hooks/useAuth';
import PermissionGuard from './PermissionGuard';

const MOBILE_BREAKPOINT = 768;

const TEXT = {
  appName: '\u77e5\u8bc6\u5e93\u7cfb\u7edf',
  home: '\u9996\u9875',
  logout: '\u9000\u51fa',
  roles: {
    admin: '\u7ba1\u7406\u5458',
    subAdmin: '\u5b50\u7ba1\u7406\u5458',
    viewer: '\u666e\u901a\u7528\u6237',
  },
  nav: {
    chat: '\u667a\u80fd\u5bf9\u8bdd',
    agents: '\u5168\u5e93\u641c\u7d22',
    kbs: '\u77e5\u8bc6\u5e93\u914d\u7f6e',
    browser: '\u6587\u6863\u6d4f\u89c8',
    documentHistory: '\u6587\u6863\u8bb0\u5f55',
    upload: '\u6587\u6863\u4e0a\u4f20',
    approvalCenter: '\u5ba1\u6279\u4e2d\u5fc3',
    approvalConfig: '\u5ba1\u6279\u914d\u7f6e',
    inbox: '\u7ad9\u5185\u4fe1',
    changePassword: '\u4fee\u6539\u5bc6\u7801',
    tools: '\u5b9e\u7528\u5de5\u5177',
    users: '\u7528\u6237\u7ba1\u7406',
    orgDirectory: '\u7ec4\u7ec7\u7ba1\u7406',
    permissionGroups: '\u6743\u9650\u5206\u7ec4',
    dataSecurity: '\u6570\u636e\u5b89\u5168',
    logs: '\u65e5\u5fd7\u5ba1\u8ba1',
    messages: '\u6d88\u606f\u4e2d\u5fc3',
    notificationSettings: '\u901a\u77e5\u8bbe\u7f6e',
    electronicSignatures: '\u7535\u5b50\u7b7e\u540d\u7ba1\u7406',
    trainingCompliance: '\u57f9\u8bad\u5408\u89c4',
  },
  toolTitles: {
    patentDownload: '\u4e13\u5229\u4e0b\u8f7d',
    paperDownload: '\u8bba\u6587\u4e0b\u8f7d',
    nasBrowser: 'NAS\u4e91\u76d8',
    drugAdmin: '\u836f\u76d1\u5bfc\u822a',
    packageDrawing: '\u5305\u88c5\u56fe\u7eb8',
  },
};

const formatRoleLabel = (role) => {
  const value = String(role || '').trim();
  if (value === 'admin') return TEXT.roles.admin;
  if (value === 'sub_admin') return TEXT.roles.subAdmin;
  if (value === 'viewer') return TEXT.roles.viewer;
  return '';
};

const Layout = ({ children }) => {
  const {
    user,
    logout,
    can,
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
  const [inboxUnreadCount, setInboxUnreadCount] = useState(0);

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

  useEffect(() => {
    let cancelled = false;
    let timerId = null;

    const loadInboxUnreadCount = async () => {
      if (!user?.user_id) {
        if (!cancelled) setInboxUnreadCount(0);
        return;
      }
      try {
        const response = await operationApprovalApi.listInbox({ limit: 1 });
        if (!cancelled) {
          setInboxUnreadCount(Number(response?.unread_count || 0));
        }
      } catch {
        if (!cancelled) {
          setInboxUnreadCount(0);
        }
      }
    };

    loadInboxUnreadCount();
    timerId = window.setInterval(loadInboxUnreadCount, 30000);

    return () => {
      cancelled = true;
      if (timerId) window.clearInterval(timerId);
    };
  }, [user?.user_id]);

  const displayName = String(user?.full_name || '').trim();
  const displayRole = formatRoleLabel(user?.role);
  const canViewDocumentHistory = user?.role === 'admin' || canReview() || (typeof can === 'function' && can('kb_documents', 'view'));

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
    { name: TEXT.nav.chat, path: '/chat', icon: '\ud83d\udcac' },
    { name: TEXT.nav.agents, path: '/agents', icon: '\ud83d\udd0d' },
    { name: TEXT.nav.kbs, path: '/kbs', icon: '\ud83d\udcd6', show: canViewKbConfig, allowedRoles: ['sub_admin'] },
    { name: TEXT.nav.browser, path: '/browser', icon: '\ud83d\udcc4' },
    { name: TEXT.nav.documentHistory, path: '/document-history', icon: '\ud83d\uddc2\ufe0f', show: () => canViewDocumentHistory },
    { name: TEXT.nav.upload, path: '/upload', icon: '\ud83d\udce4', show: canUpload },
    { name: TEXT.nav.approvalCenter, path: '/approvals', icon: '\ud83d\udccb' },
    { name: TEXT.nav.inbox, path: '/inbox', icon: '\ud83d\udcec' },
    { name: TEXT.nav.approvalConfig, path: '/approval-config', icon: '\ud83d\udd27', allowedRoles: ['admin'] },
    { name: TEXT.nav.changePassword, path: '/change-password', icon: '\ud83d\udd11' },
    { name: TEXT.nav.tools, path: '/tools', icon: '\ud83e\uddf0', show: canViewTools },
    { name: TEXT.nav.users, path: '/users', icon: '\ud83d\udc65', allowedRoles: ['admin', 'sub_admin'] },
    { name: TEXT.nav.orgDirectory, path: '/org-directory', icon: '\ud83c\udfe2', allowedRoles: ['admin'] },
    { name: TEXT.nav.permissionGroups, path: '/permission-groups', icon: '\ud83d\udee1\ufe0f', allowedRoles: ['sub_admin'] },
    { name: TEXT.nav.dataSecurity, path: '/data-security', icon: '\ud83d\udd12', allowedRoles: ['admin'] },
    { name: TEXT.nav.notificationSettings, path: '/notification-settings', icon: '\ud83d\udd14', allowedRoles: ['admin'] },
    { name: TEXT.nav.electronicSignatures, path: '/electronic-signatures', icon: '\u270d\ufe0f', allowedRoles: ['admin'] },
    { name: TEXT.nav.trainingCompliance, path: '/training-compliance', icon: '\ud83c\udf93', allowedRoles: ['admin'] },
    { name: TEXT.nav.logs, path: '/logs', icon: '\ud83d\udccb', allowedRoles: ['admin'] },
  ];

  const adminHiddenPaths = new Set(['/chat', '/agents', '/kbs', '/browser', '/upload', '/tools']);
  navigation.forEach((item) => {
    if (adminHiddenPaths.has(item.path)) {
      item.hiddenRoles = ['admin'];
    }
  });

  const pageTitleOverrides = {
    '/tools/patent-download': TEXT.toolTitles.patentDownload,
    '/tools/paper-download': TEXT.toolTitles.paperDownload,
    '/tools/nas-browser': TEXT.toolTitles.nasBrowser,
    '/tools/drug-admin': TEXT.toolTitles.drugAdmin,
    '/tools/nmpa': 'NMPA',
    '/tools/package-drawing': TEXT.toolTitles.packageDrawing,
    '/electronic-signatures': TEXT.nav.electronicSignatures,
    '/approvals': TEXT.nav.approvalCenter,
    '/approval-config': TEXT.nav.approvalConfig,
    '/inbox': TEXT.nav.inbox,
    '/messages': TEXT.nav.inbox,
    '/document-history': TEXT.nav.documentHistory,
    '/training-compliance': TEXT.nav.trainingCompliance,
  };

  const currentTitle = pageTitleOverrides[location.pathname]
    || navigation.find((item) => item.path === location.pathname)?.name
    || TEXT.home;

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
            {sidebarOpen ? TEXT.appName : 'KB'}
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
            if (item.hiddenRoles && item.hiddenRoles.includes(user?.role)) return null;
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
                  {sidebarOpen ? (
                    <>
                      <span style={{ flex: 1 }}>{item.name}</span>
                      {item.path === '/inbox' && inboxUnreadCount > 0 ? (
                        <span
                          data-testid="layout-inbox-unread"
                          style={{
                            minWidth: '24px',
                            height: '24px',
                            borderRadius: '999px',
                            background: '#2563eb',
                            color: '#ffffff',
                            fontSize: '0.75rem',
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            padding: '0 6px',
                            flexShrink: 0,
                          }}
                        >
                          {inboxUnreadCount > 99 ? '99+' : String(inboxUnreadCount)}
                        </span>
                      ) : null}
                    </>
                  ) : null}
                </Link>
              </PermissionGuard>
            );
          })}
        </nav>

        <div style={{ padding: isMobile ? '16px' : '20px', borderTop: '1px solid #374151' }}>
          {sidebarOpen ? (
            <div style={{ marginBottom: '10px', fontSize: '0.9rem' }}>
              <div style={{ fontWeight: 'bold' }} data-testid="layout-user-name">{displayName}</div>
              <div style={{ color: '#9ca3af', fontSize: '0.8rem' }} data-testid="layout-user-role">{displayRole}</div>
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
            {sidebarOpen ? TEXT.logout : 'X'}
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
              \u2630
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
