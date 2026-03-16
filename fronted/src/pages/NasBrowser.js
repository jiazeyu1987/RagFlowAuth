import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authClient from '../api/authClient';
import { knowledgeApi } from '../features/knowledge/api';
import { useAuth } from '../hooks/useAuth';
import {
  buildImportSummary,
  formatFileSize,
  formatImportReason,
  formatTime,
  normalizeFailedEntries,
  normalizeSkippedEntries,
  pathSegments,
  readStoredFolderImportTaskId,
  writeStoredFolderImportTaskId,
} from '../features/knowledge/nasBrowser/utils';

const ACTIVE_TASK_STATUSES = new Set(['pending', 'running', 'canceling', 'pausing']);
const TASK_STATUS_LABELS = {
  pending: '待处理',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  canceling: '取消中',
  pausing: '暂停中',
  paused: '已暂停',
  canceled: '已取消',
};

export default function NasBrowser() {
  const navigate = useNavigate();
  const { isAdmin } = useAuth();
  const pollTimerRef = useRef(null);

  const normalizeDisplayError = useCallback((message, fallback) => {
    const text = String(message || '').trim();
    if (!text) return fallback;
    return /[\u4e00-\u9fff]/.test(text) ? text : fallback;
  }, []);

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
  const [taskActionLoading, setTaskActionLoading] = useState(false);

  const breadcrumbs = useMemo(() => pathSegments(currentPath), [currentPath]);
  const skippedDetails = useMemo(() => normalizeSkippedEntries(folderImportProgress?.skipped), [folderImportProgress?.skipped]);
  const failedDetails = useMemo(() => normalizeFailedEntries(folderImportProgress?.failed), [folderImportProgress?.failed]);

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
      const data = await authClient.listNasFiles(path);
      setCurrentPath(data.current_path || '');
      setParentPath(data.parent_path ?? null);
      setItems(Array.isArray(data.items) ? data.items : []);
    } catch (err) {
      setError(normalizeDisplayError(err?.message, '加载 NAS 目录失败'));
    } finally {
      setLoading(false);
    }
  }, [normalizeDisplayError]);

  const pollFolderImportStatus = useCallback(
    async (taskId, options = {}) => {
      try {
        const status = await authClient.getNasFolderImportStatus(taskId);
        setFolderImportProgress(status);
        writeStoredFolderImportTaskId(taskId);

        if (status.status === 'completed') {
          stopPolling();
          setImportLoading(false);
          setTaskActionLoading(false);
          clearStoredTask();
          if (!options.silentOnComplete) {
            window.alert(buildImportSummary(status, '文件夹'));
          }
          return;
        }

        if (status.status === 'failed' || status.status === 'canceled') {
          stopPolling();
          setImportLoading(false);
          setTaskActionLoading(false);
          clearStoredTask();
          if (status.status === 'failed') {
            setError(normalizeDisplayError(status.error, '文件夹导入失败'));
          }
          return;
        }

        if (status.status === 'paused') {
          stopPolling();
          setImportLoading(false);
          setTaskActionLoading(false);
          return;
        }

        pollTimerRef.current = window.setTimeout(() => {
          pollFolderImportStatus(taskId);
        }, 1000);
      } catch (err) {
        stopPolling();
        setImportLoading(false);
        setTaskActionLoading(false);
        clearStoredTask();
        setFolderImportProgress(null);
        setError(normalizeDisplayError(err?.message, '获取文件夹导入进度失败'));
      }
    },
    [clearStoredTask, normalizeDisplayError, stopPolling]
  );

  useEffect(() => {
    loadPath('');
  }, [loadPath]);

  useEffect(() => {
    const loadDatasets = async () => {
      try {
        const data = await knowledgeApi.listRagflowDatasets();
        const nextDatasets = Array.isArray(data?.datasets) ? data.datasets : [];
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

  const openImportDialog = (item) => {
    setImportTarget(item);
    if (!selectedKb && datasets.length > 0) {
      setSelectedKb(datasets[0].name);
    }
    setImportDialogOpen(true);
  };

  const closeImportDialog = () => {
    if (importLoading) return;
    setImportDialogOpen(false);
    setImportTarget(null);
  };

  const handleImport = async () => {
    if (!importTarget || !selectedKb) {
      setError('请选择要导入到的知识库');
      return;
    }

    setImportLoading(true);
    setError('');
    try {
      if (importTarget.is_dir) {
        stopPolling();
        const task = await authClient.importNasFolder(importTarget.path, selectedKb);
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

      const result = await authClient.importNasFile(importTarget.path, selectedKb);
      setImportDialogOpen(false);
      setImportTarget(null);
      setImportLoading(false);
      window.alert(buildImportSummary(result, '文件'));
    } catch (err) {
      setImportLoading(false);
      setError(normalizeDisplayError(err?.message, `${importTarget.is_dir ? '文件夹' : '文件'}导入失败`));
    }
  };

  const handleCancelFolderImport = async () => {
    const taskId = folderImportProgress?.task_id;
    if (!taskId) return;
    setTaskActionLoading(true);
    setError('');
    try {
      const status = await authClient.cancelNasFolderImport(taskId);
      setFolderImportProgress(status);
      if (status.status === 'canceled') {
        stopPolling();
        setImportLoading(false);
        clearStoredTask();
      }
    } catch (err) {
      setError(normalizeDisplayError(err?.message, '取消文件夹导入任务失败'));
    } finally {
      setTaskActionLoading(false);
    }
  };

  const handlePauseFolderImport = async () => {
    const taskId = folderImportProgress?.task_id;
    if (!taskId) return;
    setTaskActionLoading(true);
    setError('');
    try {
      const status = await authClient.pauseNasFolderImport(taskId);
      setFolderImportProgress(status);
      if (status.status === 'paused') {
        stopPolling();
        setImportLoading(false);
      }
    } catch (err) {
      setError(normalizeDisplayError(err?.message, '暂停文件夹导入任务失败'));
    } finally {
      setTaskActionLoading(false);
    }
  };

  const handleResumeFolderImport = async () => {
    const taskId = folderImportProgress?.task_id;
    if (!taskId) return;
    setTaskActionLoading(true);
    setImportLoading(true);
    setError('');
    try {
      const status = await authClient.resumeNasFolderImport(taskId);
      setFolderImportProgress(status);
      writeStoredFolderImportTaskId(taskId);
      if (status.status === 'pending' || status.status === 'running') {
        stopPolling();
        await pollFolderImportStatus(taskId);
      } else {
        setImportLoading(false);
      }
      setTaskActionLoading(false);
    } catch (err) {
      setImportLoading(false);
      setTaskActionLoading(false);
      setError(normalizeDisplayError(err?.message, '继续文件夹导入任务失败'));
    }
  };

  const handleRetryFolderImport = async () => {
    const taskId = folderImportProgress?.task_id;
    if (!taskId) return;
    setTaskActionLoading(true);
    setImportLoading(true);
    setError('');
    try {
      const status = await authClient.retryNasFolderImport(taskId);
      setFolderImportProgress(status);
      writeStoredFolderImportTaskId(taskId);
      stopPolling();
      await pollFolderImportStatus(taskId);
      setTaskActionLoading(false);
    } catch (err) {
      setImportLoading(false);
      setTaskActionLoading(false);
      setError(normalizeDisplayError(err?.message, '重试文件夹导入任务失败'));
    }
  };

  const closeProgressPanel = () => {
    if (ACTIVE_TASK_STATUSES.has(folderImportProgress?.status)) return;
    clearStoredTask();
    setFolderImportProgress(null);
  };

  const folderTaskStatus = folderImportProgress?.status || '';
  const folderTaskStatusLabel = TASK_STATUS_LABELS[folderTaskStatus] || '未知状态';
  const isFolderTaskActive = ACTIVE_TASK_STATUSES.has(folderTaskStatus);
  const canPauseFolderTask = Boolean(folderImportProgress?.can_pause && folderImportProgress?.task_id && !taskActionLoading);
  const canResumeFolderTask = Boolean(folderImportProgress?.can_resume && folderImportProgress?.task_id && !taskActionLoading);
  const canCancelFolderTask = Boolean(folderImportProgress?.can_cancel && folderImportProgress?.task_id && !taskActionLoading);
  const canRetryFolderTask = Boolean(folderImportProgress?.can_retry && folderImportProgress?.task_id && !isFolderTaskActive && !taskActionLoading);
  const progressBarColor = {
    failed: '#d05656',
    canceled: '#cc8a2e',
    paused: '#60788e',
    pausing: '#60788e',
  }[folderTaskStatus] || '#0d5ea6';

  if (!isAdmin()) {
    return (
      <div className="admin-med-page">
        <div className="admin-med-danger">仅管理员可访问 NAS 网盘页面。</div>
      </div>
    );
  }

  return (
    <div className="admin-med-page" data-testid="nas-browser-page">
      <section className="medui-surface medui-card-pad">
        <div className="admin-med-head">
          <div>
            <h2 className="admin-med-title" style={{ margin: 0 }}>NAS 网盘浏览</h2>
            <div className="admin-med-inline-note" style={{ marginTop: 6 }}>
              共享地址：`172.30.30.4`，共享目录：`共享资料`
            </div>
          </div>
          <div className="admin-med-actions">
            <button type="button" onClick={() => navigate('/tools')} className="medui-btn medui-btn--secondary">
              返回实用工具
            </button>
            <button type="button" onClick={() => loadPath(currentPath)} className="medui-btn medui-btn--primary">
              刷新
            </button>
          </div>
        </div>
      </section>

      <section className="medui-surface medui-card-pad">
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {breadcrumbs.map((segment, index) => (
            <React.Fragment key={segment.path || 'root'}>
              {index > 0 ? <span style={{ color: '#99acc0' }}>/</span> : null}
              <button
                type="button"
                onClick={() => loadPath(segment.path)}
                style={{
                  border: 'none',
                  background: 'transparent',
                  padding: 0,
                  color: segment.path === currentPath ? '#16324d' : '#0d5ea6',
                  cursor: 'pointer',
                  fontWeight: segment.path === currentPath ? 700 : 600,
                }}
              >
                {segment.label}
              </button>
            </React.Fragment>
          ))}
        </div>

        <div className="admin-med-actions" style={{ marginTop: 12 }}>
          <button
            type="button"
            onClick={() => loadPath(parentPath || '')}
            disabled={parentPath === null}
            className="medui-btn medui-btn--neutral"
          >
            上一级目录
          </button>
        </div>
      </section>

      {folderImportProgress ? (
        <section className="medui-surface medui-card-pad">
          <div className="admin-med-head" style={{ alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#16324d' }}>文件夹导入进度</div>
              <div className="admin-med-inline-note" style={{ marginTop: 4 }}>路径：{folderImportProgress.folder_path}</div>
              <div className="admin-med-inline-note" style={{ marginTop: 4 }}>知识库：{folderImportProgress.kb_ref}</div>
            </div>

            <div className="admin-med-actions">
              <button type="button" onClick={handlePauseFolderImport} disabled={!canPauseFolderTask} className="medui-btn medui-btn--secondary">
                {taskActionLoading && canPauseFolderTask ? '暂停中...' : '暂停任务'}
              </button>
              <button type="button" onClick={handleResumeFolderImport} disabled={!canResumeFolderTask} className="medui-btn medui-btn--success">
                {taskActionLoading && canResumeFolderTask ? '继续中...' : '继续任务'}
              </button>
              <button type="button" onClick={handleCancelFolderImport} disabled={!canCancelFolderTask} className="medui-btn medui-btn--danger">
                {taskActionLoading && canCancelFolderTask ? '取消中...' : '取消任务'}
              </button>
              <button type="button" onClick={handleRetryFolderImport} disabled={!canRetryFolderTask} className="medui-btn medui-btn--warn">
                {taskActionLoading && canRetryFolderTask ? '重试中...' : '重试失败文件'}
              </button>
              <button type="button" onClick={closeProgressPanel} disabled={isFolderTaskActive} className="medui-btn medui-btn--neutral">
                关闭
              </button>
            </div>
          </div>

          <div style={{ marginTop: 14, color: '#17324d', fontWeight: 700 }}>待导入文件数：{folderImportProgress.total_files}</div>
          <div className="admin-med-inline-note" style={{ marginTop: 8 }}>
            当前进度：{folderImportProgress.processed_files} / {folderImportProgress.total_files}（{folderImportProgress.progress_percent}%）
          </div>

          <div style={{ marginTop: 10, height: 10, background: '#dbe7f3', borderRadius: 999, overflow: 'hidden' }}>
            <div
              style={{
                width: `${folderImportProgress.progress_percent}%`,
                height: '100%',
                background: progressBarColor,
                transition: 'width 0.3s ease',
              }}
            />
          </div>

          <div style={{ marginTop: 10, display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            <span className="medui-chip">已导入：{folderImportProgress.imported_count}</span>
            <span className="medui-chip">已跳过：{folderImportProgress.skipped_count}</span>
            <span className="medui-chip">失败：{folderImportProgress.failed_count}</span>
            <span className="medui-chip">状态：{folderTaskStatusLabel}</span>
            <span className="medui-chip">优先级：{folderImportProgress.task_priority ?? '-'}</span>
            {Number.isInteger(folderImportProgress.queue_position) ? <span className="medui-chip">队列位置：{folderImportProgress.queue_position}</span> : null}
            <span className="medui-chip">重试次数：{folderImportProgress.retry_count || 0}</span>
          </div>

          {folderImportProgress.current_file ? <div className="admin-med-inline-note" style={{ marginTop: 10 }}>当前文件：{folderImportProgress.current_file}</div> : null}
          {folderImportProgress.error ? <div className="admin-med-danger" style={{ marginTop: 10 }}>{normalizeDisplayError(folderImportProgress.error, '文件夹导入失败')}</div> : null}

          {skippedDetails.length > 0 || failedDetails.length > 0 ? (
            <div className="admin-med-grid admin-med-grid--2" style={{ marginTop: 14 }}>
              {skippedDetails.length > 0 ? (
                <div className="medui-surface medui-card-pad" style={{ borderColor: '#f2d6a6', background: '#fffaf1' }}>
                  <div style={{ fontWeight: 700, color: '#9a651f', marginBottom: 8 }}>跳过明细（最多显示 50 条）</div>
                  <div style={{ maxHeight: 180, overflowY: 'auto' }}>
                    {skippedDetails.map((item, index) => (
                      <div key={`skipped_${item.path}_${index}`} style={{ borderBottom: index === skippedDetails.length - 1 ? 'none' : '1px solid #f2e3c6', padding: '8px 0' }}>
                        <div style={{ color: '#8a632c', fontSize: '0.85rem' }}>路径：{item.path}</div>
                        <div style={{ color: '#8a632c', fontSize: '0.85rem' }}>原因：{formatImportReason(item.reason, item.detail)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {failedDetails.length > 0 ? (
                <div className="medui-surface medui-card-pad" style={{ borderColor: '#f3c1c1', background: '#fff6f6' }}>
                  <div style={{ fontWeight: 700, color: '#9a3939', marginBottom: 8 }}>失败明细（最多显示 50 条）</div>
                  <div style={{ maxHeight: 220, overflowY: 'auto' }}>
                    {failedDetails.map((item, index) => (
                      <div key={`failed_${item.path}_${index}`} style={{ borderBottom: index === failedDetails.length - 1 ? 'none' : '1px solid #f4d7d7', padding: '8px 0' }}>
                        <div style={{ color: '#9a3939', fontSize: '0.85rem' }}>路径：{item.path}</div>
                        <div style={{ color: '#9a3939', fontSize: '0.85rem' }}>原因：{formatImportReason(item.reason, item.detail)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}
        </section>
      ) : null}

      {error ? <div className="admin-med-danger">{error}</div> : null}

      <section className="medui-surface medui-card-pad">
        {loading ? (
          <div className="medui-empty" style={{ padding: '28px 0' }}>正在加载 NAS 内容...</div>
        ) : items.length === 0 ? (
          <div className="medui-empty" style={{ padding: '28px 0' }}>当前目录为空</div>
        ) : (
          <div className="medui-table-wrap">
            <table className="medui-table">
              <thead>
                <tr>
                  <th>名称</th>
                  <th style={{ width: 120 }}>类型</th>
                  <th style={{ width: 140, textAlign: 'right' }}>大小</th>
                  <th style={{ width: 220 }}>修改时间</th>
                  <th style={{ width: 260, textAlign: 'right' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.path}>
                    <td>
                      {item.is_dir ? (
                        <button
                          type="button"
                          onClick={() => loadPath(item.path)}
                          style={{ border: 'none', background: 'transparent', padding: 0, cursor: 'pointer', color: '#0d5ea6', fontWeight: 700 }}
                        >
                          [目录] {item.name}
                        </button>
                      ) : (
                        <span>[文件] {item.name}</span>
                      )}
                    </td>
                    <td>{item.is_dir ? '目录' : '文件'}</td>
                    <td style={{ textAlign: 'right' }}>{item.is_dir ? '-' : formatFileSize(item.size)}</td>
                    <td>{formatTime(item.modified_at)}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        type="button"
                        onClick={() => openImportDialog(item)}
                        data-testid={`nas-import-btn-${String(item.path || item.name || 'item').replace(/[^a-zA-Z0-9_-]/g, '_')}`}
                        className={`medui-btn ${item.is_dir ? 'medui-btn--primary' : 'medui-btn--success'}`}
                      >
                        {item.is_dir ? '导入目录到知识库' : '导入文件到知识库'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {importDialogOpen && importTarget ? (
        <div className="admin-med-dialog" onClick={closeImportDialog}>
          <div data-testid="nas-import-dialog" className="admin-med-dialog__panel" style={{ width: 'min(560px, 96vw)' }} onClick={(e) => e.stopPropagation()}>
            <div className="admin-med-dialog__head">
              <div style={{ fontWeight: 700, color: '#16324d' }}>{importTarget.is_dir ? '导入目录到知识库' : '导入文件到知识库'}</div>
            </div>

            <div className="admin-med-dialog__body">
              <div className="admin-med-inline-note" style={{ lineHeight: 1.7 }}>
                名称：{importTarget.name}
                <br />
                路径：{importTarget.path}
                <br />
                {importTarget.is_dir ? '将递归导入当前目录及其子目录中的文件。' : '仅当文件格式受支持时才会导入。'}
              </div>

              <label>
                <div style={{ fontWeight: 700, color: '#17324d', marginBottom: 8 }}>选择知识库</div>
                <select data-testid="nas-import-kb-select" value={selectedKb} onChange={(e) => setSelectedKb(e.target.value)} className="medui-select">
                  {datasets.map((ds) => (
                    <option key={ds.id} value={ds.name}>
                      {ds.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="admin-med-dialog__foot">
              <button type="button" onClick={closeImportDialog} disabled={importLoading} data-testid="nas-import-cancel" className="medui-btn medui-btn--neutral">
                取消
              </button>
              <button
                type="button"
                onClick={handleImport}
                disabled={importLoading || !selectedKb}
                data-testid="nas-import-confirm"
                className="medui-btn medui-btn--primary"
              >
                {importLoading ? '处理中...' : '开始导入'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
