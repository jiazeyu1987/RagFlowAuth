import { useEffect, useMemo } from 'react';

import { buildDownloadMessages } from './downloadPageMessages';
import useDownloadControllerConfig from './useDownloadControllerConfig';
import useDownloadCurrentSession from './useDownloadCurrentSession';
import useDownloadHistory from './useDownloadHistory';
import useDownloadHistoryActions from './useDownloadHistoryActions';

export default function useDownloadPageController({
  manager,
  storageKey,
  localKbRef,
  defaultSources,
  sourceLabelMap,
  normalizeHistoryKeywords,
  strictCompletionValidation = false,
  messages,
}) {
  const config = useDownloadControllerConfig({
    storageKey,
    defaultSources,
    sourceLabelMap,
  });

  const msg = useMemo(
    () => buildDownloadMessages(localKbRef, messages),
    [localKbRef, messages]
  );

  const parsedKeywords = useMemo(
    () => manager.parseKeywords(config.keywordText),
    [config.keywordText, manager]
  );

  const history = useDownloadHistory({
    manager,
    normalizeHistoryKeywords,
    keywordsErrorMessage: msg.keywordsError,
    itemsErrorMessage: msg.itemsError,
  });

  useEffect(() => {
    history.loadHistoryKeywords();
  }, [history.loadHistoryKeywords]);

  useEffect(() => {
    if (!history.selectedHistoryKey) return;
    history.loadHistoryItems(history.selectedHistoryKey);
  }, [history.loadHistoryItems, history.selectedHistoryKey]);

  const currentSession = useDownloadCurrentSession({
    manager,
    localKbRef,
    msg,
    keywordText: config.keywordText,
    useAnd: config.useAnd,
    autoAnalyze: config.autoAnalyze,
    sources: config.sources,
    strictCompletionValidation,
    loadHistoryKeywords: history.loadHistoryKeywords,
    loadHistoryItems: history.loadHistoryItems,
  });

  const historyActions = useDownloadHistoryActions({
    manager,
    localKbRef,
    msg,
    sessionId: currentSession.sessionId,
    selectedHistoryKey: history.selectedHistoryKey,
    setSelectedHistoryKey: history.setSelectedHistoryKey,
    loadHistoryKeywords: history.loadHistoryKeywords,
    loadHistoryItems: history.loadHistoryItems,
    clearHistoryPayload: history.clearHistoryPayload,
    refreshSession: currentSession.refreshSession,
    setError: currentSession.setError,
    setInfo: currentSession.setInfo,
  });

  return {
    keywordText: config.keywordText,
    useAnd: config.useAnd,
    autoAnalyze: config.autoAnalyze,
    sources: config.sources,
    sourceErrors: currentSession.sourceErrors,
    sourceStats: currentSession.sourceStats,
    loading: currentSession.loading,
    stopping: currentSession.stopping,
    addingAll: currentSession.addingAll,
    deletingSession: currentSession.deletingSession,
    addingItemId: currentSession.addingItemId,
    deletingItemId: currentSession.deletingItemId,
    resultTab: currentSession.resultTab,
    deletingHistoryKey: historyActions.deletingHistoryKey,
    addingHistoryKey: historyActions.addingHistoryKey,
    previewOpen: currentSession.previewOpen,
    previewTarget: currentSession.previewTarget,
    error: currentSession.error,
    info: currentSession.info,
    parsedKeywords,
    sessionId: currentSession.sessionId,
    sessionStatus: currentSession.sessionStatus,
    items: currentSession.items,
    historyKeywords: history.historyKeywords,
    historyLoading: history.historyLoading,
    historyError: history.historyError,
    selectedHistoryKey: history.selectedHistoryKey,
    historyPayload: history.historyPayload,
    historyItems: history.historyItems,
    historyItemsLoading: history.historyItemsLoading,
    setKeywordText: config.setKeywordText,
    setUseAnd: config.setUseAnd,
    setAutoAnalyze: config.setAutoAnalyze,
    setResultTab: currentSession.setResultTab,
    setPreviewOpen: currentSession.setPreviewOpen,
    setSelectedHistoryKey: history.setSelectedHistoryKey,
    updateSource: config.updateSource,
    runDownload: currentSession.runDownload,
    stopDownload: currentSession.stopDownload,
    openPreview: currentSession.openPreview,
    addOne: currentSession.addOne,
    deleteOne: currentSession.deleteOne,
    addAll: currentSession.addAll,
    removeSession: currentSession.removeSession,
    deleteHistoryKeyword: historyActions.deleteHistoryKeyword,
    addHistoryKeywordToKb: historyActions.addHistoryKeywordToKb,
    refreshHistoryPanel: historyActions.refreshHistoryPanel,
  };
}
