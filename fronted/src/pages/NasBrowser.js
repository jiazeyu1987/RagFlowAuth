import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authClient from '../api/authClient';
import { knowledgeApi } from '../features/knowledge/api';
import { useAuth } from '../hooks/useAuth';
import {
  buildImportSummary,
  BUTTON_STYLES,
  CARD_STYLE,
  formatFileSize,
  formatImportReason,
  formatTime,
  normalizeFailedEntries,
  normalizeSkippedEntries,
  PAGE_STYLE,
  pathSegments,
  readStoredFolderImportTaskId,
  writeStoredFolderImportTaskId,
} from '../features/knowledge/nasBrowser/utils';

const MOBILE_BREAKPOINT = 768;

export default function NasBrowser() {
  const navigate = useNavigate();
  const { isAdmin } = useAuth();
  const pollTimerRef = useRef(null);
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

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

  const breadcrumbs = useMemo(() => pathSegments(currentPath), [currentPath]);
  const skippedDetails = useMemo(
    () => normalizeSkippedEntries(folderImportProgress?.skipped),
    [folderImportProgress?.skipped],
  );
  const failedDetails = useMemo(
    () => normalizeFailedEntries(folderImportProgress?.failed),
    [folderImportProgress?.failed],
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
      const data = await authClient.listNasFiles(path);
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
        const status = await authClient.getNasFolderImportStatus(taskId);
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
    [clearStoredTask, stopPolling],
  );

  useEffect(() => {
    loadPath('');
  }, [loadPath]);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    const loadDatasets = async () => {
      try {
        const data = await knowledgeApi.listRagflowDatasets();
        const nextDatasets = Array.isArray(data?.datasets) ? data.datasets : [];
        setDatasets(nextDatasets);
        if (nextDatasets.length > 0) {
          setSelectedKb((current) => current || nextDatasets[0].name);
        }
      } catch (_err) {
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
      setError('请选择要上传到的知识库');
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
      setError(err.message || `上传${importTarget.is_dir ? '文件夹' : '文件'}失败`);
    }
  };

  const closeProgressPanel = () => {
    if (folderImportProgress?.status === 'running' || folderImportProgress?.status === 'pending') {
      return;
    }
    clearStoredTask();
    setFolderImportProgress(null);
  };

  if (!isAdmin()) {
    return <div style={{ color: '#991b1b' }}>仅管理员可访问 NAS 云盘。</div>;
  }

  return (
    <div style={PAGE_STYLE} data-testid="nas-browser-page">
      <div
        style={{
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          justifyContent: 'space-between',
          alignItems: isMobile ? 'stretch' : 'center',
          gap: '12px',
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: '1.4rem', color: '#111827' }}>NAS 云盘</h2>
          <div style={{ marginTop: '6px', color: '#6b7280', fontSize: '0.95rem' }}>
            NAS: `172.30.30.4` / 共享目录: `it共享`
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', gap: '8px', width: isMobile ? '100%' : 'auto' }}>
          <button
            type="button"
            onClick={() => navigate('/tools')}
            style={{ ...BUTTON_STYLES.neutral, width: isMobile ? '100%' : 'auto' }}
          >
            返回实用工具
          </button>
          <button
            type="button"
            onClick={() => loadPath(currentPath)}
            style={{ ...BUTTON_STYLES.primary, width: isMobile ? '100%' : 'auto' }}
          >
            刷新
          </button>
        </div>
      </div>

      <div style={{ ...CARD_STYLE, marginTop: '16px', padding: isMobile ? '14px' : '14px 16px' }}>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          {breadcrumbs.map((segment, index) => (
            <React.Fragment key={segment.path || 'root'}>
              {index > 0 && <span style={{ color: '#9ca3af' }}>/</span>}
              <button
                type="button"
                onClick={() => loadPath(segment.path)}
                style={{
                  border: 'none',
                  background: 'transparent',
                  padding: 0,
                  color: segment.path === currentPath ? '#111827' : '#2563eb',
                  cursor: 'pointer',
                  fontWeight: segment.path === currentPath ? 800 : 600,
                }}
              >
                {segment.label}
              </button>
            </React.Fragment>
          ))}
        </div>
        <div style={{ marginTop: '12px', display: 'flex', flexDirection: isMobile ? 'column' : 'row', gap: '8px' }}>
          <button
            type="button"
            onClick={() => loadPath(parentPath || '')}
            disabled={parentPath === null}
            style={{
              ...BUTTON_STYLES.neutral,
              background: parentPath === null ? '#f3f4f6' : '#fff',
              color: parentPath === null ? '#9ca3af' : '#111827',
              cursor: parentPath === null ? 'not-allowed' : 'pointer',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            上一级
          </button>
        </div>
      </div>

      {folderImportProgress && (
        <div style={{ ...CARD_STYLE, marginTop: '16px', padding: isMobile ? '14px' : '16px 18px' }}>
          <div
            style={{
              display: 'flex',
              flexDirection: isMobile ? 'column' : 'row',
              justifyContent: 'space-between',
              gap: '12px',
              alignItems: isMobile ? 'stretch' : 'center',
            }}
          >
            <div>
              <div style={{ fontSize: '1rem', fontWeight: 800, color: '#111827' }}>文件夹上传进度</div>
              <div style={{ marginTop: '4px', color: '#475569' }}>路径: {folderImportProgress.folder_path}</div>
              <div style={{ marginTop: '4px', color: '#475569' }}>知识库: {folderImportProgress.kb_ref}</div>
            </div>
            <button
              type="button"
              onClick={closeProgressPanel}
              disabled={folderImportProgress.status === 'running' || folderImportProgress.status === 'pending'}
              style={{
                ...BUTTON_STYLES.neutral,
                cursor:
                  folderImportProgress.status === 'running' || folderImportProgress.status === 'pending'
                    ? 'not-allowed'
                    : 'pointer',
                width: isMobile ? '100%' : 'auto',
              }}
            >
              关闭
            </button>
          </div>
          <div style={{ marginTop: '14px', color: '#111827', fontWeight: 700 }}>
            待上传文件数: {folderImportProgress.total_files}
          </div>
          <div style={{ marginTop: '8px', color: '#475569' }}>
            当前进度: {folderImportProgress.processed_files} / {folderImportProgress.total_files} ({folderImportProgress.progress_percent}%)
          </div>
          <div style={{ marginTop: '10px', height: '10px', background: '#e5e7eb', borderRadius: '999px', overflow: 'hidden' }}>
            <div
              style={{
                width: `${folderImportProgress.progress_percent}%`,
                height: '100%',
                background: folderImportProgress.status === 'failed' ? '#dc2626' : '#2563eb',
                transition: 'width 0.3s ease',
              }}
            />
          </div>
          <div style={{ marginTop: '10px', display: 'flex', gap: '16px', flexWrap: 'wrap', color: '#475569' }}>
            <span>已导入: {folderImportProgress.imported_count}</span>
            <span>跳过: {folderImportProgress.skipped_count}</span>
            <span>失败: {folderImportProgress.failed_count}</span>
            <span>状态: {folderImportProgress.status}</span>
          </div>
          {folderImportProgress.current_file && (
            <div style={{ marginTop: '10px', color: '#1f2937' }}>当前文件: {folderImportProgress.current_file}</div>
          )}
          {folderImportProgress.error && (
            <div style={{ marginTop: '10px', color: '#b91c1c' }}>错误: {folderImportProgress.error}</div>
          )}
          {(skippedDetails.length > 0 || failedDetails.length > 0) && (
            <div style={{ marginTop: '14px', borderTop: '1px solid #e5e7eb', paddingTop: '12px' }}>
              {skippedDetails.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontWeight: 700, color: '#92400e' }}>跳过明细（最多显示 50 条）</div>
                  <div style={{ marginTop: '6px', maxHeight: '180px', overflowY: 'auto', border: '1px solid #fcd34d', borderRadius: '8px', background: '#fffbeb' }}>
                    {skippedDetails.map((item, index) => (
                      <div key={`skipped_${item.path}_${index}`} style={{ padding: '8px 10px', borderBottom: index === skippedDetails.length - 1 ? 'none' : '1px solid #fde68a', color: '#78350f', fontSize: '13px' }}>
                        <div>路径: {item.path}</div>
                        <div>原因: {formatImportReason(item.reason, item.detail)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {failedDetails.length > 0 && (
                <div>
                  <div style={{ fontWeight: 700, color: '#991b1b' }}>失败明细（最多显示 50 条）</div>
                  <div style={{ marginTop: '6px', maxHeight: '220px', overflowY: 'auto', border: '1px solid #fca5a5', borderRadius: '8px', background: '#fef2f2' }}>
                    {failedDetails.map((item, index) => (
                      <div key={`failed_${item.path}_${index}`} style={{ padding: '8px 10px', borderBottom: index === failedDetails.length - 1 ? 'none' : '1px solid #fecaca', color: '#7f1d1d', fontSize: '13px' }}>
                        <div>路径: {item.path}</div>
                        <div>原因: {formatImportReason(item.reason, item.detail)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {error && (
        <div
          style={{
            marginTop: '16px',
            padding: '12px 16px',
            borderRadius: '12px',
            background: '#fef2f2',
            color: '#b91c1c',
            border: '1px solid #fecaca',
          }}
        >
          {error}
        </div>
      )}

      <div style={{ ...CARD_STYLE, marginTop: '16px', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '32px', color: '#6b7280' }}>正在加载 NAS 内容...</div>
        ) : items.length === 0 ? (
          <div style={{ padding: '32px', color: '#6b7280' }}>当前目录为空</div>
        ) : (
          <div style={{ width: '100%', overflowX: 'auto' }}>
            <table style={{ width: '100%', minWidth: isMobile ? '760px' : '100%', borderCollapse: 'collapse' }}>
              <thead style={{ background: '#f8fafc' }}>
                <tr>
                  <th style={{ padding: '14px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>名称</th>
                  <th style={{ padding: '14px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb', width: isMobile ? '96px' : '120px' }}>类型</th>
                  <th style={{ padding: '14px 16px', textAlign: 'right', borderBottom: '1px solid #e5e7eb', width: isMobile ? '110px' : '140px' }}>大小</th>
                  <th style={{ padding: '14px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb', width: isMobile ? '180px' : '220px' }}>修改时间</th>
                  <th style={{ padding: '14px 16px', textAlign: 'right', borderBottom: '1px solid #e5e7eb', width: isMobile ? '220px' : '280px' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.path} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '14px 16px', wordBreak: 'break-word' }}>
                      {item.is_dir ? (
                        <button
                          type="button"
                          onClick={() => loadPath(item.path)}
                          style={{ border: 'none', background: 'transparent', padding: 0, cursor: 'pointer', color: '#1d4ed8', fontWeight: 700, textAlign: 'left' }}
                        >
                          {`[目录] ${item.name}`}
                        </button>
                      ) : (
                        <span style={{ color: '#111827', wordBreak: 'break-word' }}>{`[文件] ${item.name}`}</span>
                      )}
                    </td>
                    <td style={{ padding: '14px 16px', color: '#475569' }}>{item.is_dir ? '文件夹' : '文件'}</td>
                    <td style={{ padding: '14px 16px', textAlign: 'right', color: '#475569' }}>{item.is_dir ? '-' : formatFileSize(item.size)}</td>
                    <td style={{ padding: '14px 16px', color: '#475569', whiteSpace: 'nowrap' }}>{formatTime(item.modified_at)}</td>
                    <td style={{ padding: '14px 16px', textAlign: isMobile ? 'left' : 'right' }}>
                      <div style={{ display: 'flex', justifyContent: isMobile ? 'flex-start' : 'flex-end', flexWrap: 'wrap', gap: '8px' }}>
                        <button
                          type="button"
                          onClick={() => openImportDialog(item)}
                          data-testid={`nas-import-btn-${String(item.path || item.name || 'item').replace(/[^a-zA-Z0-9_-]/g, '_')}`}
                          style={{ ...(item.is_dir ? BUTTON_STYLES.primary : BUTTON_STYLES.success), maxWidth: '100%' }}
                        >
                          {item.is_dir ? '上传文件夹到知识库' : '上传文件到知识库'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {importDialogOpen && importTarget && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.45)',
            display: 'flex',
            alignItems: isMobile ? 'flex-end' : 'center',
            justifyContent: 'center',
            padding: isMobile ? '16px' : '24px',
            zIndex: 50,
          }}
          onClick={closeImportDialog}
        >
          <div
            data-testid="nas-import-dialog"
            style={{
              width: 'min(520px, 100%)',
              maxHeight: '90vh',
              overflowY: 'auto',
              background: '#fff',
              borderRadius: isMobile ? '14px' : '16px',
              padding: isMobile ? '16px' : '20px',
              border: '1px solid #e5e7eb',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#111827' }}>
              {importTarget.is_dir ? '上传文件夹到知识库' : '上传文件到知识库'}
            </div>
            <div style={{ marginTop: '10px', color: '#475569', lineHeight: 1.6 }}>
              名称: {importTarget.name}
              <br />
              路径: {importTarget.path}
              <br />
              {importTarget.is_dir
                ? '会先统计支持格式的文件数量，然后递归上传当前文件夹及其子目录中的文件。'
                : '仅上传当前文件，并且只支持知识库允许的文件格式。'}
            </div>
            <div style={{ marginTop: '16px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 700, color: '#111827' }}>选择知识库</label>
              <select
                data-testid="nas-import-kb-select"
                value={selectedKb}
                onChange={(e) => setSelectedKb(e.target.value)}
                style={{ width: '100%', padding: '10px 12px', borderRadius: '10px', border: '1px solid #d1d5db', background: '#fff' }}
              >
                {datasets.map((ds) => (
                  <option key={ds.id} value={ds.name}>
                    {ds.name}
                  </option>
                ))}
              </select>
            </div>
            <div
              style={{
                marginTop: '18px',
                display: 'flex',
                flexDirection: isMobile ? 'column' : 'row',
                justifyContent: 'flex-end',
                gap: '10px',
              }}
            >
              <button
                type="button"
                onClick={closeImportDialog}
                disabled={importLoading}
                data-testid="nas-import-cancel"
                style={{
                  ...BUTTON_STYLES.neutral,
                  cursor: importLoading ? 'not-allowed' : 'pointer',
                  width: isMobile ? '100%' : 'auto',
                }}
              >
                取消
              </button>
              <button
                type="button"
                onClick={handleImport}
                disabled={importLoading || !selectedKb}
                data-testid="nas-import-confirm"
                style={{
                  ...BUTTON_STYLES.primary,
                  border: 'none',
                  background: importLoading || !selectedKb ? '#94a3b8' : '#2563eb',
                  color: '#fff',
                  cursor: importLoading || !selectedKb ? 'not-allowed' : 'pointer',
                  width: isMobile ? '100%' : 'auto',
                }}
              >
                {importLoading ? '处理中...' : '开始上传'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
