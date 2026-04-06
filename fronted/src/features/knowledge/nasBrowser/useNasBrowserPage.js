import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { knowledgeApi } from '../api';
import nasApi from '../../nas/api';
import { useAuth } from '../../../hooks/useAuth';
import {
  buildImportSummary,
  formatImportReason,
  normalizeFailedEntries,
  normalizeSkippedEntries,
  pathSegments,
  readStoredFolderImportTaskId,
  writeStoredFolderImportTaskId,
} from './utils';

export default function useNasBrowserPage() {
  const { isAdmin } = useAuth();
  const pollTimerRef = useRef(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [currentPath, setCurrentPath] = useState('');
  const [parentPath, setParentPath] = useState(null);
  const [items, setItems] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importTarget, setImportTarget] = useState(null);
  const [selectedKb, setSelectedKb] = useState('');
  const [importLoading, setImportLoading] = useState(false);
  const [folderImportProgress, setFolderImportProgress] = useState(null);

  const admin = isAdmin();
  const breadcrumbs = useMemo(() => pathSegments(currentPath), [currentPath]);
  const skippedDetails = useMemo(
    () => normalizeSkippedEntries(folderImportProgress?.skipped),
    [folderImportProgress?.skipped]
  );
  const failedDetails = useMemo(
    () => normalizeFailedEntries(folderImportProgress?.failed),
    [folderImportProgress?.failed]
  );

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      window.clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const clearStoredTask = useCallback(() => {
    writeStoredFolderImportTaskId('');
  }, []);

  const loadPath = useCallback(async (path = '') => {
    setLoading(true);
    setError('');
    try {
      const data = await nasApi.listFiles(path);
      setCurrentPath(data.current_path || '');
      setParentPath(data.parent_path ?? null);
      setItems(Array.isArray(data.items) ? data.items : []);
    } catch (err) {
      setError(err.message || '加载 NAS 目录失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const pollFolderImportStatus = useCallback(
    async (taskId, options = {}) => {
      try {
        const status = await nasApi.getFolderImportStatus(taskId);
        setFolderImportProgress(status);
        writeStoredFolderImportTaskId(taskId);

        if (status.status === 'completed') {
          stopPolling();
          setImportLoading(false);
          clearStoredTask();
          if (!options.silentOnComplete) {
            window.alert(buildImportSummary(status, '文件夹'));
          }
          return;
        }

        if (status.status === 'failed') {
          stopPolling();
          setImportLoading(false);
          clearStoredTask();
          setError(status.error || '文件夹上传失败');
          return;
        }

        pollTimerRef.current = window.setTimeout(() => {
          pollFolderImportStatus(taskId);
        }, 1000);
      } catch (err) {
        stopPolling();
        setImportLoading(false);
        clearStoredTask();
        setFolderImportProgress(null);
        setError(err.message || '获取文件夹上传进度失败');
      }
    },
    [clearStoredTask, stopPolling]
  );

  useEffect(() => {
    loadPath('');
  }, [loadPath]);

  useEffect(() => {
    const loadDatasets = async () => {
      try {
        const nextDatasets = await knowledgeApi.listRagflowDatasets();
        setDatasets(nextDatasets);
        if (nextDatasets.length > 0) {
          setSelectedKb((current) => current || nextDatasets[0].name);
        }
      } catch {
        setDatasets([]);
      }
    };

    loadDatasets();
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  useEffect(() => {
    const storedTaskId = readStoredFolderImportTaskId();
    if (!storedTaskId) return;
    setImportLoading(true);
    pollFolderImportStatus(storedTaskId, { silentOnComplete: true });
  }, [pollFolderImportStatus]);

  const openImportDialog = useCallback(
    (item) => {
      setImportTarget(item);
      if (!selectedKb && datasets.length > 0) {
        setSelectedKb(datasets[0].name);
      }
      setImportDialogOpen(true);
    },
    [datasets, selectedKb]
  );

  const closeImportDialog = useCallback(() => {
    if (importLoading) return;
    setImportDialogOpen(false);
    setImportTarget(null);
  }, [importLoading]);

  const handleImport = useCallback(async () => {
    if (!importTarget || !selectedKb) {
      setError('请选择要上传到的知识库');
      return;
    }

    setImportLoading(true);
    setError('');
    try {
      if (importTarget.is_dir) {
        stopPolling();
        const task = await nasApi.importFolder(importTarget.path, selectedKb);
        setFolderImportProgress(task);
        writeStoredFolderImportTaskId(task.task_id || '');
        setImportDialogOpen(false);
        setImportTarget(null);
        if (task.status === 'completed') {
          setImportLoading(false);
          clearStoredTask();
          window.alert(buildImportSummary(task, '文件夹'));
          return;
        }
        pollFolderImportStatus(task.task_id);
        return;
      }

      const result = await nasApi.importFile(importTarget.path, selectedKb);
      setImportDialogOpen(false);
      setImportTarget(null);
      setImportLoading(false);
      window.alert(buildImportSummary(result, '文件'));
    } catch (err) {
      setImportLoading(false);
      setError(err.message || `上传${importTarget.is_dir ? '文件夹' : '文件'}失败`);
    }
  }, [clearStoredTask, importTarget, pollFolderImportStatus, selectedKb, stopPolling]);

  const closeProgressPanel = useCallback(() => {
    if (
      folderImportProgress?.status === 'running' ||
      folderImportProgress?.status === 'pending'
    ) {
      return;
    }
    clearStoredTask();
    setFolderImportProgress(null);
  }, [clearStoredTask, folderImportProgress?.status]);

  return {
    admin,
    loading,
    error,
    currentPath,
    parentPath,
    items,
    datasets,
    importDialogOpen,
    importTarget,
    selectedKb,
    importLoading,
    folderImportProgress,
    breadcrumbs,
    skippedDetails,
    failedDetails,
    setSelectedKb,
    loadPath,
    openImportDialog,
    closeImportDialog,
    handleImport,
    closeProgressPanel,
    formatImportReason,
  };
}
