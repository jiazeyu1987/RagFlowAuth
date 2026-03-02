import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { knowledgeApi } from '../features/knowledge/api';
import { useAuth } from '../hooks/useAuth';

const MAX_FILE_SIZE_BYTES = 16 * 1024 * 1024;
const DEFAULT_ACCEPTED_EXTENSIONS = ['.txt', '.pdf', '.docx', '.md', '.xlsx', '.xls', '.csv', '.png', '.jpg', '.jpeg'];
const DEFAULT_KB_NAME = '展厅';

const getFileExtensionLower = (name = '') => {
  const idx = name.lastIndexOf('.');
  if (idx < 0) return '';
  return name.slice(idx).toLowerCase();
};

const formatBytes = (bytes) => {
  if (!Number.isFinite(bytes)) return '-';
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(2)} KB`;
  const mb = kb / 1024;
  return `${mb.toFixed(2)} MB`;
};

const getDisplayPath = (file) => String(file?.webkitRelativePath || file?.name || '');
const getFileUniqueKey = (file) => `${getDisplayPath(file)}__${file?.size || 0}__${file?.lastModified || 0}`;

const normalizeExtension = (value = '') => {
  let next = String(value || '').trim().toLowerCase();
  if (!next) return '';
  if (!next.startsWith('.')) next = `.${next}`;
  return next;
};

const panelStyle = {
  backgroundColor: 'white',
  padding: '32px',
  borderRadius: '8px',
  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
  maxWidth: '720px',
};

const KnowledgeUpload = () => {
  const navigate = useNavigate();
  const auth = useAuth();
  const canManageExtensions = auth.isAdmin();

  const [selectedFiles, setSelectedFiles] = useState([]);
  const [kbId, setKbId] = useState(DEFAULT_KB_NAME);
  const [datasets, setDatasets] = useState([]);
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  const [allowedExtensions, setAllowedExtensions] = useState(DEFAULT_ACCEPTED_EXTENSIONS);
  const [loadingExtensions, setLoadingExtensions] = useState(true);
  const [savingExtensions, setSavingExtensions] = useState(false);
  const [extensionDraft, setExtensionDraft] = useState('');
  const [extensionsMessage, setExtensionsMessage] = useState(null);

  const acceptAttr = useMemo(() => {
    const values = Array.isArray(allowedExtensions) && allowedExtensions.length > 0
      ? allowedExtensions
      : DEFAULT_ACCEPTED_EXTENSIONS;
    return values.join(',');
  }, [allowedExtensions]);

  const extensionSet = useMemo(() => new Set(allowedExtensions), [allowedExtensions]);

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        setLoadingDatasets(true);
        const data = await knowledgeApi.listRagflowDatasets();
        const list = data.datasets || [];
        setDatasets(list);
        if (list.length > 0) {
          setKbId((current) => current || list[0].name || list[0].id || DEFAULT_KB_NAME);
          setError(null);
        } else {
          setKbId(DEFAULT_KB_NAME);
          setError('您没有被分配任何知识库权限，请联系管理员');
        }
      } catch (err) {
        setDatasets([]);
        setError(err.message || '无法加载知识库列表，请检查网络连接');
      } finally {
        setLoadingDatasets(false);
      }
    };

    const fetchAllowedExtensions = async () => {
      try {
        setLoadingExtensions(true);
        const payload = await knowledgeApi.getAllowedUploadExtensions();
        const items = Array.isArray(payload?.allowed_extensions) && payload.allowed_extensions.length > 0
          ? payload.allowed_extensions.map(normalizeExtension).filter(Boolean)
          : DEFAULT_ACCEPTED_EXTENSIONS;
        setAllowedExtensions(Array.from(new Set(items)).sort());
      } catch (err) {
        setAllowedExtensions(DEFAULT_ACCEPTED_EXTENSIONS);
        setExtensionsMessage({ type: 'error', text: err.message || '无法加载可上传文件后缀，已回退到默认配置' });
      } finally {
        setLoadingExtensions(false);
      }
    };

    fetchDatasets();
    fetchAllowedExtensions();
  }, []);

  const addFiles = (filesLike) => {
    const incoming = Array.from(filesLike || []);
    if (incoming.length === 0) return;

    const valid = [];
    const rejected = [];
    for (const file of incoming) {
      const ext = getFileExtensionLower(file.name);
      if (!extensionSet.has(ext)) {
        rejected.push({ file, reason: 'unsupported' });
        continue;
      }
      if (file.size > MAX_FILE_SIZE_BYTES) {
        rejected.push({ file, reason: 'too_large' });
        continue;
      }
      valid.push(file);
    }

    setSelectedFiles((prev) => {
      const map = new Map((prev || []).map((file) => [getFileUniqueKey(file), file]));
      for (const file of valid) map.set(getFileUniqueKey(file), file);
      return Array.from(map.values());
    });

    if (rejected.length > 0) {
      const tooLarge = rejected.filter((item) => item.reason === 'too_large').length;
      const unsupported = rejected.filter((item) => item.reason === 'unsupported').length;
      const parts = [];
      if (tooLarge) parts.push(`${tooLarge} 个文件超过 16MB`);
      if (unsupported) parts.push(`${unsupported} 个文件后缀不在允许列表中`);
      setError(`部分文件未加入上传队列：${parts.join('，')}`);
    } else {
      setError(null);
    }
  };

  const handleUpload = async (event) => {
    event.preventDefault();
    if (selectedFiles.length === 0) {
      setError('请选择文件');
      return;
    }

    setUploading(true);
    setUploadProgress(null);
    setError(null);
    setSuccess(null);

    try {
      const results = [];
      for (let index = 0; index < selectedFiles.length; index += 1) {
        const file = selectedFiles[index];
        setUploadProgress({ current: index + 1, total: selectedFiles.length, filename: getDisplayPath(file) });
        try {
          const result = await knowledgeApi.uploadDocument(file, kbId);
          results.push({ ok: true, filename: result?.filename || getDisplayPath(file) });
        } catch (err) {
          results.push({ ok: false, filename: getDisplayPath(file), error: err?.message || '上传失败' });
        }
      }

      const okCount = results.filter((item) => item.ok).length;
      const failCount = results.length - okCount;
      if (failCount === 0) {
        setSuccess(`上传完成：成功 ${okCount} 个，等待审核`);
        setSelectedFiles([]);
        setTimeout(() => navigate('/documents'), 1200);
      } else {
        const firstFail = results.find((item) => !item.ok);
        setError(
          `上传完成：成功 ${okCount} 个，失败 ${failCount} 个${firstFail ? `。（例如：${firstFail.filename}：${firstFail.error}）` : ''}`
        );
      }
    } catch (err) {
      setError(err.message || '上传失败');
    } finally {
      setUploading(false);
      setUploadProgress(null);
    }
  };

  const handleFileSelect = (event) => {
    addFiles(event.target.files);
    event.target.value = '';
  };

  const handleFolderSelect = (event) => {
    addFiles(event.target.files);
    event.target.value = '';
  };

  const handleDrop = (event) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(false);
    if (!uploading) addFiles(event.dataTransfer?.files);
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (!uploading) setDragActive(true);
  };

  const handleDragLeave = (event) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(false);
  };

  const removeFile = (key) => {
    setSelectedFiles((prev) => prev.filter((file) => getFileUniqueKey(file) !== key));
  };

  const handleAddExtension = () => {
    const normalized = normalizeExtension(extensionDraft);
    if (!normalized) {
      setExtensionsMessage({ type: 'error', text: '请输入有效的文件后缀，例如 .pdf' });
      return;
    }
    if (/\s/.test(normalized) || normalized.length < 2) {
      setExtensionsMessage({ type: 'error', text: '文件后缀格式不正确' });
      return;
    }
    setAllowedExtensions((prev) => Array.from(new Set([...prev, normalized])).sort());
    setExtensionDraft('');
    setExtensionsMessage(null);
  };

  const handleDeleteExtension = (extension) => {
    setAllowedExtensions((prev) => prev.filter((item) => item !== extension));
    setExtensionsMessage(null);
  };

  const handleSaveExtensions = async () => {
    if (!canManageExtensions) return;
    if (allowedExtensions.length === 0) {
      setExtensionsMessage({ type: 'error', text: '至少保留一个允许上传的后缀' });
      return;
    }
    setSavingExtensions(true);
    setExtensionsMessage(null);
    try {
      const payload = await knowledgeApi.updateAllowedUploadExtensions(allowedExtensions);
      const next = Array.isArray(payload?.allowed_extensions) ? payload.allowed_extensions.map(normalizeExtension).filter(Boolean) : allowedExtensions;
      setAllowedExtensions(Array.from(new Set(next)).sort());
      setExtensionsMessage({ type: 'success', text: '文件后缀配置已保存，后续上传立即生效' });
    } catch (err) {
      setExtensionsMessage({ type: 'error', text: err.message || '保存文件后缀配置失败' });
    } finally {
      setSavingExtensions(false);
    }
  };

  return (
    <div>
      <h2 style={{ marginBottom: '24px' }}>上传知识库文档</h2>

      {error && (
        <div
          data-testid="upload-error"
          style={{
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            padding: '12px 16px',
            borderRadius: '4px',
            marginBottom: '20px',
          }}
        >
          {error}
        </div>
      )}

      {success && (
        <div
          data-testid="upload-success"
          style={{
            backgroundColor: '#d1fae5',
            color: '#065f46',
            padding: '12px 16px',
            borderRadius: '4px',
            marginBottom: '20px',
          }}
        >
          {success}
        </div>
      )}

      <div style={panelStyle}>
        <form onSubmit={handleUpload}>
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#374151' }}>
              知识库
            </label>
            <select
              value={kbId}
              onChange={(event) => setKbId(event.target.value)}
              disabled={loadingDatasets}
              data-testid="upload-kb-select"
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                fontSize: '1rem',
                boxSizing: 'border-box',
                backgroundColor: loadingDatasets ? '#f3f4f6' : 'white',
              }}
            >
              {loadingDatasets ? (
                <option>加载知识库中...</option>
              ) : datasets.length > 0 ? (
                datasets.map((dataset) => (
                  <option key={dataset.id} value={dataset.name || dataset.id}>
                    {dataset.name || dataset.id}
                  </option>
                ))
              ) : (
                <option value={DEFAULT_KB_NAME}>{DEFAULT_KB_NAME}</option>
              )}
            </select>
          </div>

          <div style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'center', flexWrap: 'wrap', marginBottom: 8 }}>
              <label style={{ fontWeight: '500', color: '#374151' }}>允许上传的文件后缀</label>
              <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                {loadingExtensions ? '正在加载配置...' : `当前配置：${acceptAttr}`}
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
              {allowedExtensions.map((extension) => (
                <span
                  key={extension}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '6px 10px',
                    borderRadius: 999,
                    backgroundColor: '#eff6ff',
                    color: '#1d4ed8',
                    fontSize: '0.9rem',
                  }}
                >
                  {extension}
                  {canManageExtensions && (
                    <button
                      type="button"
                      onClick={() => handleDeleteExtension(extension)}
                      style={{
                        border: 'none',
                        background: 'transparent',
                        color: '#1d4ed8',
                        cursor: 'pointer',
                        fontWeight: 700,
                        padding: 0,
                        lineHeight: 1,
                      }}
                      aria-label={`删除 ${extension}`}
                    >
                      ×
                    </button>
                  )}
                </span>
              ))}
            </div>

            {canManageExtensions && (
              <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, backgroundColor: '#f9fafb', marginBottom: 12 }}>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                  <input
                    type="text"
                    value={extensionDraft}
                    onChange={(event) => setExtensionDraft(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.preventDefault();
                        handleAddExtension();
                      }
                    }}
                    placeholder="输入后缀，例如 .dwg 或 dwg"
                    style={{
                      flex: '1 1 260px',
                      minWidth: 220,
                      padding: '10px 12px',
                      border: '1px solid #d1d5db',
                      borderRadius: 6,
                      fontSize: '0.95rem',
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleAddExtension}
                    style={{
                      padding: '10px 14px',
                      backgroundColor: '#2563eb',
                      color: 'white',
                      border: 'none',
                      borderRadius: 6,
                      cursor: 'pointer',
                      fontWeight: 500,
                    }}
                  >
                    添加后缀
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveExtensions}
                    disabled={savingExtensions}
                    style={{
                      padding: '10px 14px',
                      backgroundColor: savingExtensions ? '#9ca3af' : '#059669',
                      color: 'white',
                      border: 'none',
                      borderRadius: 6,
                      cursor: savingExtensions ? 'not-allowed' : 'pointer',
                      fontWeight: 500,
                    }}
                  >
                    {savingExtensions ? '保存中...' : '保存配置'}
                  </button>
                </div>
                <div style={{ marginTop: 10, fontSize: '0.85rem', color: '#6b7280' }}>
                  admin 可在这里新增、删除并保存允许上传的文件后缀。修改后会影响后续上传校验。
                </div>
              </div>
            )}

            {extensionsMessage && (
              <div
                style={{
                  marginBottom: 12,
                  padding: '10px 12px',
                  borderRadius: 6,
                  backgroundColor: extensionsMessage.type === 'success' ? '#d1fae5' : '#fee2e2',
                  color: extensionsMessage.type === 'success' ? '#065f46' : '#991b1b',
                  fontSize: '0.9rem',
                }}
              >
                {extensionsMessage.text}
              </div>
            )}
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#374151' }}>
              选择文件
            </label>
            <div style={{ display: 'flex', gap: '10px', marginBottom: '12px', flexWrap: 'wrap' }}>
              <button
                type="button"
                disabled={uploading}
                onClick={() => !uploading && document.getElementById('fileInput')?.click()}
                style={{
                  padding: '10px 14px',
                  backgroundColor: uploading ? '#9ca3af' : '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: uploading ? 'not-allowed' : 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: 500,
                }}
              >
                选择文件
              </button>
              <button
                type="button"
                disabled={uploading}
                onClick={() => !uploading && document.getElementById('folderInput')?.click()}
                style={{
                  padding: '10px 14px',
                  backgroundColor: uploading ? '#9ca3af' : '#0f766e',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: uploading ? 'not-allowed' : 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: 500,
                }}
              >
                选择文件夹
              </button>
            </div>

            <div
              data-testid="upload-file-dropzone"
              style={{
                border: `2px dashed ${dragActive ? '#3b82f6' : '#d1d5db'}`,
                borderRadius: '4px',
                padding: '40px',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'border-color 0.2s',
                backgroundColor: dragActive ? '#eff6ff' : 'transparent',
              }}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => !uploading && document.getElementById('fileInput')?.click()}
            >
              <input
                type="file"
                onChange={handleFileSelect}
                accept={acceptAttr}
                multiple
                style={{ display: 'none' }}
                id="fileInput"
                data-testid="upload-file-input"
              />
              <input
                type="file"
                onChange={handleFolderSelect}
                accept={acceptAttr}
                multiple
                webkitdirectory=""
                directory=""
                style={{ display: 'none' }}
                id="folderInput"
                data-testid="upload-folder-input"
              />
              <div style={{ fontSize: '2rem', marginBottom: '12px' }}>文件</div>
              <div style={{ color: '#6b7280', marginBottom: '8px' }}>
                {selectedFiles.length > 0
                  ? `已选择 ${selectedFiles.length} 个文件`
                  : '拖动文件到此处，或点击选择文件/文件夹（支持子文件夹）'}
              </div>
              {uploadProgress && (
                <div style={{ fontSize: '0.9rem', color: '#6b7280' }} data-testid="upload-progress">
                  正在上传 {uploadProgress.current}/{uploadProgress.total}：{uploadProgress.filename}
                </div>
              )}
            </div>

            {selectedFiles.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div style={{ fontSize: '0.9rem', color: '#374151', fontWeight: 500 }}>已选择文件</div>
                  <button
                    type="button"
                    disabled={uploading}
                    onClick={() => setSelectedFiles([])}
                    data-testid="upload-files-clear"
                    style={{
                      padding: '6px 10px',
                      backgroundColor: '#6b7280',
                      color: 'white',
                      border: 'none',
                      borderRadius: 6,
                      cursor: uploading ? 'not-allowed' : 'pointer',
                      fontSize: '0.85rem',
                    }}
                  >
                    清空
                  </button>
                </div>
                <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden' }}>
                  {selectedFiles.map((file) => {
                    const key = getFileUniqueKey(file);
                    const displayPath = getDisplayPath(file);
                    return (
                      <div
                        key={key}
                        data-testid={`upload-file-item-${key}`}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '10px 12px',
                          borderBottom: '1px solid #f3f4f6',
                          backgroundColor: 'white',
                          gap: 12,
                        }}
                      >
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontSize: '0.95rem', color: '#111827', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {file.name}
                          </div>
                          <div style={{ fontSize: '0.82rem', color: '#6b7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {displayPath}
                          </div>
                          <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{formatBytes(file.size)}</div>
                        </div>
                        <button
                          type="button"
                          disabled={uploading}
                          onClick={() => removeFile(key)}
                          data-testid={`upload-file-remove-${key}`}
                          style={{
                            padding: '6px 10px',
                            backgroundColor: '#ef4444',
                            color: 'white',
                            border: 'none',
                            borderRadius: 6,
                            cursor: uploading ? 'not-allowed' : 'pointer',
                            fontSize: '0.85rem',
                            flexShrink: 0,
                          }}
                        >
                          移除
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            <div style={{ marginTop: '8px', fontSize: '0.85rem', color: '#6b7280' }}>
              支持的文件后缀：{acceptAttr}（单文件最大 16MB，支持选择文件夹并递归读取子文件夹）
            </div>
          </div>

          <button
            type="submit"
            disabled={selectedFiles.length === 0 || uploading}
            data-testid="upload-submit"
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: selectedFiles.length === 0 || uploading ? '#9ca3af' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontSize: '1rem',
              fontWeight: '500',
              cursor: selectedFiles.length === 0 || uploading ? 'not-allowed' : 'pointer',
            }}
          >
            {uploading ? '上传中...' : `上传文档${selectedFiles.length > 0 ? `（${selectedFiles.length}）` : ''}`}
          </button>
        </form>

        <div
          style={{
            marginTop: '24px',
            padding: '16px',
            backgroundColor: '#f9fafb',
            borderRadius: '4px',
            fontSize: '0.9rem',
            color: '#6b7280',
          }}
        >
          <div style={{ marginBottom: '8px', fontWeight: '500', color: '#374151' }}>上传流程</div>
          <ol style={{ margin: 0, paddingLeft: '20px' }}>
            <li>选择知识库并上传文件</li>
            <li>文档进入“待审核”状态</li>
            <li>审核通过后自动上传到 RAGFlow 知识库</li>
          </ol>
        </div>
      </div>
    </div>
  );
};

export default KnowledgeUpload;
