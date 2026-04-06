import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../../hooks/useAuth';
import {
  isDownloadedItem,
  isSessionActive,
} from '../download/downloadPageUtils';
import useDownloadPageController from '../download/useDownloadPageController';
import patentDownloadApi from './api';
import {
  buildPatentFrontendLogs,
  DEFAULT_PATENT_SOURCES,
  enrichPatentHistoryKeywords,
  PATENT_LAST_CONFIG_KEY,
  PATENT_LOCAL_KB_REF,
  PATENT_SOURCE_LABEL_MAP,
} from './patentDownloadPageUtils';

const MOBILE_BREAKPOINT = 768;

const getInitialIsMobile = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};

export default function usePatentDownloadPage() {
  const navigate = useNavigate();
  const { canDownload } = useAuth();
  const canDownloadFiles = typeof canDownload === 'function' ? !!canDownload() : false;
  const [isMobile, setIsMobile] = useState(getInitialIsMobile);

  const normalizePatentHistoryKeywords = useCallback(
    async (rawList) =>
      enrichPatentHistoryKeywords(rawList, patentDownloadApi, isDownloadedItem),
    []
  );

  const controller = useDownloadPageController({
    manager: patentDownloadApi,
    storageKey: PATENT_LAST_CONFIG_KEY,
    localKbRef: PATENT_LOCAL_KB_REF,
    defaultSources: DEFAULT_PATENT_SOURCES,
    sourceLabelMap: PATENT_SOURCE_LABEL_MAP,
    normalizeHistoryKeywords: normalizePatentHistoryKeywords,
    strictCompletionValidation: true,
  });

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const frontendLogs = useMemo(
    () =>
      buildPatentFrontendLogs({
        sourceErrors: controller.sourceErrors,
        sourceStats: controller.sourceStats,
        items: controller.items,
        autoAnalyze: controller.autoAnalyze,
        sourceLabelMap: PATENT_SOURCE_LABEL_MAP,
      }),
    [
      controller.autoAnalyze,
      controller.items,
      controller.sourceErrors,
      controller.sourceStats,
    ]
  );

  const handleBackToTools = () => {
    navigate('/tools');
  };

  return {
    ...controller,
    isMobile,
    canDownloadFiles,
    handleBackToTools,
    frontendLogs,
  };
}

export { isSessionActive };
