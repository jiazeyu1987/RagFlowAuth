import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { knowledgeApi } from '../features/knowledge/api';
import SelectedFilesList from '../features/knowledge/upload/components/SelectedFilesList';
import UploadDropzone from '../features/knowledge/upload/components/UploadDropzone';
import UploadExtensionsPanel from '../features/knowledge/upload/components/UploadExtensionsPanel';
import {
  DEFAULT_ACCEPTED_EXTENSIONS,
  DEFAULT_KB_NAME,
  MAX_FILE_SIZE_BYTES,
  uploadPanelStyle,
} from '../features/knowledge/upload/constants';
import {
  getDisplayPath,
  getFileExtensionLower,
  getFileUniqueKey,
  normalizeExtension,
} from '../features/knowledge/upload/utils';
import { useAuth } from '../hooks/useAuth';

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
  const maxFileSizeMB = Math.floor(MAX_FILE_SIZE_BYTES / (1024 * 1024));

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
      if (tooLarge) parts.push(`${tooLarge} 个文件过大（超过 ${maxFileSizeMB}MB）`);
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

      <div style={uploadPanelStyle}>
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

          <UploadExtensionsPanel
            loadingExtensions={loadingExtensions}
            acceptAttr={acceptAttr}
            allowedExtensions={allowedExtensions}
            canManageExtensions={canManageExtensions}
            extensionDraft={extensionDraft}
            onExtensionDraftChange={setExtensionDraft}
            onAddExtension={handleAddExtension}
            onDeleteExtension={handleDeleteExtension}
            onSaveExtensions={handleSaveExtensions}
            savingExtensions={savingExtensions}
            extensionsMessage={extensionsMessage}
          />

          <UploadDropzone
            uploading={uploading}
            dragActive={dragActive}
            selectedFilesLength={selectedFiles.length}
            uploadProgress={uploadProgress}
            acceptAttr={acceptAttr}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onFileSelect={handleFileSelect}
            onFolderSelect={handleFolderSelect}
          />

          <SelectedFilesList
            selectedFiles={selectedFiles}
            uploading={uploading}
            onClear={() => setSelectedFiles([])}
            onRemove={removeFile}
          />

          <div style={{ marginTop: '8px', fontSize: '0.85rem', color: '#6b7280' }}>
            Supported extensions: {acceptAttr} (max 16MB per file; folder upload is recursive).
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
