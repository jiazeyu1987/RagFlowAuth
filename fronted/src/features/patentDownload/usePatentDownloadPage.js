import { useCallback, useMemo } from 'react';
import {
  isDownloadedItem,
  isSessionActive,
} from '../download/downloadPageUtils';
import useDownloadPageController from '../download/useDownloadPageController';
import patentDownloadManager from './PatentDownloadManager';
import {
  buildPatentFrontendLogs,
  DEFAULT_PATENT_SOURCES,
  enrichPatentHistoryKeywords,
  PATENT_LAST_CONFIG_KEY,
  PATENT_LOCAL_KB_REF,
  PATENT_SOURCE_LABEL_MAP,
} from './patentDownloadPageUtils';

export default function usePatentDownloadPage() {
  const normalizePatentHistoryKeywords = useCallback(
    async (rawList) =>
      enrichPatentHistoryKeywords(rawList, patentDownloadManager, isDownloadedItem),
    []
  );

  const controller = useDownloadPageController({
    manager: patentDownloadManager,
    storageKey: PATENT_LAST_CONFIG_KEY,
    localKbRef: PATENT_LOCAL_KB_REF,
    defaultSources: DEFAULT_PATENT_SOURCES,
    sourceLabelMap: PATENT_SOURCE_LABEL_MAP,
    normalizeHistoryKeywords: normalizePatentHistoryKeywords,
    strictCompletionValidation: true,
  });

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

  return {
    ...controller,
    frontendLogs,
  };
}

export { isSessionActive };
