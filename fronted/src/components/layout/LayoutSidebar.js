import React from 'react';
import { Link } from 'react-router-dom';
import { NAVIGATION_ROUTES } from '../../routes/routeRegistry';
import PermissionGuard from '../PermissionGuard';
import { formatRoleLabel, LAYOUT_TEXT } from './layoutConfig';

const isActiveRoute = (pathname, route) => {
  if (pathname === route.path) return true;
  if (Array.isArray(route.matchPrefixes)) {
    return route.matchPrefixes.some((prefix) => pathname.startsWith(prefix));
  }
  return false;
};

const LayoutSidebar = ({
  inboxUnreadCount,
  isMobile,
  onLogout,
  onNavigate,
  onToggleSidebar,
  pathname,
  sidebarOpen,
  sidebarWidth,
  user,
}) => {
  const displayName = String(user?.full_name || '').trim();
  const displayRole = formatRoleLabel(user?.role);
  const sidebarUserId = String(user?.user_id || '').trim();

  return (
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
          alignItems: 'flex-start',
        }}
      >
        <div style={{ minWidth: 0, flex: 1, paddingRight: '8px' }}>
          <h2
            data-testid="layout-sidebar-title"
            style={{ margin: 0, fontSize: sidebarOpen ? (isMobile ? '1.2rem' : '1.5rem') : '0.9rem' }}
          >
            {sidebarOpen ? LAYOUT_TEXT.appName : 'KB'}
          </h2>
          {sidebarOpen && sidebarUserId ? (
            <div
              data-testid="layout-sidebar-subtitle"
              style={{
                marginTop: '4px',
                fontSize: '0.7rem',
                lineHeight: 1.2,
                color: '#9ca3af',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {sidebarUserId}
            </div>
          ) : null}
        </div>
        <button
          type="button"
          onClick={onToggleSidebar}
          data-testid="layout-sidebar-toggle"
          style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', fontSize: '1.2rem' }}
          aria-label="Toggle sidebar"
        >
          {sidebarOpen ? '<' : '>'}
        </button>
      </div>

      <nav style={{ flex: 1, padding: '10px 0', overflowY: 'auto' }}>
        {NAVIGATION_ROUTES.map((route) => {
          if (route.navHiddenRoles && route.navHiddenRoles.includes(user?.role)) return null;

          const navGuard = route.navGuard || route.guard || {};
          const active = isActiveRoute(pathname, route);

          return (
            <PermissionGuard
              key={route.path}
              allowedRoles={navGuard.allowedRoles}
              permission={navGuard.permission}
              permissions={navGuard.permissions}
              anyPermissions={navGuard.anyPermissions}
              fallback={null}
            >
              <Link
                to={route.path}
                data-testid={`nav-${route.path.replace('/', '') || 'home'}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: sidebarOpen ? 'flex-start' : 'center',
                  gap: sidebarOpen ? '10px' : '0px',
                  padding: sidebarOpen ? '12px 20px' : '12px 0px',
                  color: active ? '#60a5fa' : '#d1d5db',
                  textDecoration: 'none',
                  backgroundColor: active ? '#374151' : 'transparent',
                  transition: 'background-color 0.2s',
                  whiteSpace: sidebarOpen ? 'normal' : 'nowrap',
                  overflow: 'hidden',
                }}
                onClick={onNavigate}
                onMouseEnter={(event) => {
                  if (!active) event.currentTarget.style.backgroundColor = '#374151';
                }}
                onMouseLeave={(event) => {
                  if (!active) event.currentTarget.style.backgroundColor = 'transparent';
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
                  title={route.title}
                >
                  {route.icon || '-'}
                </span>
                {sidebarOpen ? (
                  <>
                    <span style={{ flex: 1 }}>{route.title}</span>
                    {route.path === '/inbox' && inboxUnreadCount > 0 ? (
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
          onClick={onLogout}
          data-testid="layout-logout"
          style={{ width: '100%', padding: '8px', backgroundColor: '#ef4444', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          onMouseEnter={(event) => {
            event.currentTarget.style.backgroundColor = '#dc2626';
          }}
          onMouseLeave={(event) => {
            event.currentTarget.style.backgroundColor = '#ef4444';
          }}
        >
          {sidebarOpen ? LAYOUT_TEXT.logout : 'X'}
        </button>
      </div>
    </aside>
  );
};

export default LayoutSidebar;
