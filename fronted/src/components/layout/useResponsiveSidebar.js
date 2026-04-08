import { useEffect, useState } from 'react';
import { MOBILE_BREAKPOINT } from './layoutConfig';

export const useResponsiveSidebar = () => {
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
      setSidebarOpen((previous) => {
        if (mobile) return false;
        return previous === false ? true : previous;
      });
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return {
    isMobile,
    sidebarOpen,
    openSidebar: () => setSidebarOpen(true),
    closeSidebar: () => setSidebarOpen(false),
    toggleSidebar: () => setSidebarOpen((previous) => !previous),
    sidebarWidth: isMobile ? 'min(78vw, 280px)' : (sidebarOpen ? '250px' : '60px'),
    headerPadding: isMobile ? '14px 16px' : '16px 24px',
    contentPadding: isMobile ? '16px' : '24px',
  };
};
