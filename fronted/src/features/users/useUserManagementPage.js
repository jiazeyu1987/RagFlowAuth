import { useEffect, useState } from 'react';

import { useUserManagement } from './hooks/useUserManagement';

const MOBILE_BREAKPOINT = 768;

export default function useUserManagementPage() {
  const management = useUserManagement();
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return {
    ...management,
    isMobile,
  };
}
