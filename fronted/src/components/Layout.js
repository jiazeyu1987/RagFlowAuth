import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { ROUTE_TEXT, getRouteTitle } from '../routes/routeRegistry';
import LayoutHeader from './layout/LayoutHeader';
import LayoutSidebar from './layout/LayoutSidebar';
import { useInboxUnreadCount } from './layout/useInboxUnreadCount';
import { useResponsiveSidebar } from './layout/useResponsiveSidebar';

const Layout = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const {
    isMobile,
    sidebarOpen,
    openSidebar,
    closeSidebar,
    toggleSidebar,
    sidebarWidth,
    headerPadding,
    contentPadding,
  } = useResponsiveSidebar();
  const inboxUnreadCount = useInboxUnreadCount(user?.user_id);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleNavigate = () => {
    if (isMobile) closeSidebar();
  };

  const currentTitle = getRouteTitle(location.pathname) || ROUTE_TEXT.home;

  return (
    <div style={{ display: 'flex', height: '100vh', position: 'relative', overflow: 'hidden' }}>
      {isMobile && sidebarOpen ? (
        <button
          type="button"
          aria-label="close sidebar overlay"
          onClick={closeSidebar}
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

      <LayoutSidebar
        inboxUnreadCount={inboxUnreadCount}
        isMobile={isMobile}
        onLogout={handleLogout}
        onNavigate={handleNavigate}
        onToggleSidebar={toggleSidebar}
        pathname={location.pathname}
        sidebarOpen={sidebarOpen}
        sidebarWidth={sidebarWidth}
        user={user}
      />

      <main style={{ flex: 1, overflow: 'auto', backgroundColor: '#f9fafb', width: '100%' }}>
        <LayoutHeader
          currentTitle={currentTitle}
          headerPadding={headerPadding}
          isMobile={isMobile}
          onOpenSidebar={openSidebar}
        />
        <div style={{ padding: contentPadding }}>{children}</div>
      </main>
    </div>
  );
};

export default Layout;
