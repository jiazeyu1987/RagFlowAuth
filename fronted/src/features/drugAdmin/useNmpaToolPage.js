import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const MOBILE_BREAKPOINT = 768;

export const NMPA_HOME_URL = 'https://www.cmde.org.cn/index.html';
export const NMPA_CATALOG_URL =
  'https://www.cmde.org.cn/flfg/zdyz/flmlbzh/flmlylqx/index.html';

const getInitialIsMobile = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};

const openUrl = (url) => {
  window.open(url, '_blank', 'noopener,noreferrer');
};

export default function useNmpaToolPage() {
  const navigate = useNavigate();
  const [isMobile, setIsMobile] = useState(getInitialIsMobile);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleBack = () => {
    navigate('/tools');
  };

  const handleOpenHome = () => {
    openUrl(NMPA_HOME_URL);
  };

  const handleOpenCatalog = () => {
    openUrl(NMPA_CATALOG_URL);
  };

  return {
    isMobile,
    handleBack,
    handleOpenHome,
    handleOpenCatalog,
  };
}
