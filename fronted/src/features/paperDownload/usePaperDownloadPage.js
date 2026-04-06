import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../../hooks/useAuth';
import { isSessionActive } from '../download/downloadPageUtils';
import useDownloadPageController from '../download/useDownloadPageController';
import paperDownloadApi from './api';
import {
  DEFAULT_PAPER_SOURCES,
  PAPER_LAST_CONFIG_KEY,
  PAPER_LOCAL_KB_REF,
  PAPER_SOURCE_LABEL_MAP,
} from './paperDownloadPageUtils';

const MOBILE_BREAKPOINT = 768;

const getInitialIsMobile = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};

export default function usePaperDownloadPage() {
  const navigate = useNavigate();
  const { canDownload } = useAuth();
  const canDownloadFiles = typeof canDownload === 'function' ? !!canDownload() : false;
  const [isMobile, setIsMobile] = useState(getInitialIsMobile);

  const controller = useDownloadPageController({
    manager: paperDownloadApi,
    storageKey: PAPER_LAST_CONFIG_KEY,
    localKbRef: PAPER_LOCAL_KB_REF,
    defaultSources: DEFAULT_PAPER_SOURCES,
    sourceLabelMap: PAPER_SOURCE_LABEL_MAP,
  });

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleBackToTools = () => {
    navigate('/tools');
  };

  return {
    ...controller,
    isMobile,
    canDownloadFiles,
    handleBackToTools,
  };
}

export { isSessionActive };
