import { useCallback, useMemo, useState } from 'react';

import { notificationApi } from '../notification/api';
import { orgDirectoryApi } from './api';
import {
  DINGTALK_DIRECTORY_REBUILD_FAILED_ERROR,
  ORG_EXCEL_FILE_REQUIRED_ERROR,
  ORG_EXCEL_FILE_TYPE_ERROR,
  buildDingtalkRebuildFailureError,
  buildDingtalkRebuildSkippedNotice,
  buildDingtalkRebuildSuccessNotice,
  buildRebuildConfirmMessage,
  isDingtalkChannel,
  isSupportedExcelFilename,
} from './helpers';

export default function useOrgDirectoryRebuild({
  excelFileInputRef,
  loadAll,
  resetAfterRebuild,
  setError,
  setNotice,
}) {
  const [rebuilding, setRebuilding] = useState(false);
  const [selectedExcelFile, setSelectedExcelFile] = useState(null);
  const [recipientMapRebuildSummary, setRecipientMapRebuildSummary] = useState(null);

  const canTriggerRebuild = useMemo(
    () => Boolean(selectedExcelFile) && !rebuilding,
    [rebuilding, selectedExcelFile]
  );

  const handleChooseExcelFile = useCallback(() => {
    excelFileInputRef.current?.click();
  }, [excelFileInputRef]);

  const handleClearExcelFile = useCallback(() => {
    setSelectedExcelFile(null);
    setError(null);
    setNotice(null);
    setRecipientMapRebuildSummary(null);
    if (excelFileInputRef.current) {
      excelFileInputRef.current.value = '';
    }
  }, [excelFileInputRef, setError, setNotice]);

  const handleExcelFileChange = useCallback(
    (event) => {
      const nextFile = event.target.files?.[0] || null;
      if (!nextFile) return;
      if (!isSupportedExcelFilename(nextFile.name)) {
        setSelectedExcelFile(null);
        setError(ORG_EXCEL_FILE_TYPE_ERROR);
        setNotice(null);
        setRecipientMapRebuildSummary(null);
        if (excelFileInputRef.current) {
          excelFileInputRef.current.value = '';
        }
        return;
      }
      setError(null);
      setNotice(null);
      setSelectedExcelFile(nextFile);
    },
    [excelFileInputRef, setError, setNotice]
  );

  const getConfiguredDingtalkChannelId = useCallback(async () => {
    const channels = await notificationApi.listChannels(false);
    const dingtalkChannel = (Array.isArray(channels) ? channels : []).find(isDingtalkChannel);
    return dingtalkChannel?.channel_id || null;
  }, []);

  const handleRebuild = useCallback(async () => {
    if (!selectedExcelFile) {
      setError(ORG_EXCEL_FILE_REQUIRED_ERROR);
      return;
    }

    if (!window.confirm(buildRebuildConfirmMessage(selectedExcelFile.name))) {
      return;
    }

    setRebuilding(true);
    setError(null);
    setNotice(null);
    setRecipientMapRebuildSummary(null);

    try {
      await orgDirectoryApi.rebuildFromExcel(selectedExcelFile);
      let nextError = null;
      let nextNotice = null;
      let nextRecipientMapRebuildSummary = null;

      try {
        const dingtalkChannelId = await getConfiguredDingtalkChannelId();
        if (!dingtalkChannelId) {
          nextNotice = buildDingtalkRebuildSkippedNotice();
        } else {
          const summary = await notificationApi.rebuildDingtalkRecipientMap(dingtalkChannelId);
          nextNotice = buildDingtalkRebuildSuccessNotice(summary);
          nextRecipientMapRebuildSummary = summary;
        }
      } catch (recipientMapError) {
        const detail =
          recipientMapError?.message ||
          String(recipientMapError || DINGTALK_DIRECTORY_REBUILD_FAILED_ERROR);
        nextError = buildDingtalkRebuildFailureError(detail);
      }

      resetAfterRebuild();
      await loadAll();
      setError(nextError);
      setNotice(nextNotice);
      setRecipientMapRebuildSummary(nextRecipientMapRebuildSummary);
    } catch (err) {
      setError(err?.message || String(err));
    } finally {
      setRebuilding(false);
    }
  }, [
    getConfiguredDingtalkChannelId,
    loadAll,
    resetAfterRebuild,
    selectedExcelFile,
    setError,
    setNotice,
  ]);

  return {
    rebuilding,
    selectedExcelFile,
    recipientMapRebuildSummary,
    canTriggerRebuild,
    handleChooseExcelFile,
    handleClearExcelFile,
    handleExcelFileChange,
    handleRebuild,
  };
}
