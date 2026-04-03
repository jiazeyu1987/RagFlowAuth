import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { knowledgeApi } from '../features/knowledge/api';
import SelectedFilesList from '../features/knowledge/upload/components/SelectedFilesList';
import UploadDropzone from '../features/knowledge/upload/components/UploadDropzone';
import UploadExtensionsPanel from '../features/knowledge/upload/components/UploadExtensionsPanel';
import {
  DEFAULT_ACCEPTED_EXTENSIONS,
  DEFAULT_KB_NAME,
  uploadPanelStyle,
} from '../features/knowledge/upload/constants';
import {
  getDisplayPath,
  getFileExtensionLower,
  getFileUniqueKey,
  normalizeExtension,
} from '../features/knowledge/upload/utils';
import { useAuth } from '../hooks/useAuth';

const MOBILE_BREAKPOINT = 768;

const getDatasetValue = (dataset) => dataset?.name || dataset?.id || '';

const getDatasetLabel = (dataset) => {
  const name = String(dataset?.name || dataset?.id || '').trim();
  const nodePath = String(dataset?.node_path || '').trim();
  if (!name) return '';
  if (!nodePath || nodePath === '/') return name;
  return `${nodePath}/${name}`;
};

const normalizeKbRef = (value) => String(value || '').trim();

const mergeDatasetDirectoryInfo = (datasetsPayload, directoryPayload) => {
  const list = Array.isArray(datasetsPayload) ? datasetsPayload : [];
  const directoryDatasets = Array.isArray(directoryPayload?.datasets) ? directoryPayload.datasets : [];
  const byId = new Map();
  const byName = new Map();

  directoryDatasets.forEach((dataset) => {
    const nodePath = String(dataset?.node_path || '').trim();
    const id = normalizeKbRef(dataset?.id);
    const name = normalizeKbRef(dataset?.name);
    if (id) byId.set(id, nodePath);
    if (name) byName.set(name, nodePath);
  });

  return list.map((dataset) => {
    const id = normalizeKbRef(dataset?.id);
    const name = normalizeKbRef(dataset?.name);
    const nodePath = byId.get(id) || byName.get(name) || dataset?.node_path || '/';
    return {
      ...dataset,
      node_path: nodePath,
    };
  });
};

const filterDatasetsByVisibility = (allDatasets, visibleKbRefs) => {
  const list = Array.isArray(allDatasets) ? allDatasets : [];
  if (visibleKbRefs.size === 0) return [];

  return list.filter((dataset) => {
    const id = normalizeKbRef(dataset?.id);
    const name = normalizeKbRef(dataset?.name);
    return (id && visibleKbRefs.has(id)) || (name && visibleKbRefs.has(name));
  });
};

const KnowledgeUpload = () => {
  const navigate = useNavigate();
  const { accessibleKbs, loading: authLoading, canViewKbConfig } = useAuth();
  const canManageExtensions = canViewKbConfig();
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

  const [selectedFiles, setSelectedFiles] = useState([]);
  const [kbId, setKbId] = useState(DEFAULT_KB_NAME);
  const [kbSearchKeyword, setKbSearchKeyword] = useState('');
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
  const datasetOptions = useMemo(
    () =>
      (datasets || [])
        .map((dataset) => ({
          key: dataset?.id || getDatasetValue(dataset),
          value: getDatasetValue(dataset),
          label: getDatasetLabel(dataset),
        }))
        .filter((option) => option.value && option.label)
        .sort((left, right) => String(left.label || '').localeCompare(String(right.label || ''), 'zh-Hans-CN')),
    [datasets]
  );
  const filteredDatasetOptions = useMemo(() => {
    const keyword = String(kbSearchKeyword || '').trim().toLowerCase();
    if (!keyword) return datasetOptions;

    return datasetOptions.filter((option) => {
      const label = String(option?.label || '').toLowerCase();
      const value = String(option?.value || '').toLowerCase();
      return label.includes(keyword) || value.includes(keyword);
    });
  }, [datasetOptions, kbSearchKeyword]);

  useEffect(() => {
    if (loadingDatasets) return;
    if (filteredDatasetOptions.length === 0) return;
    if (filteredDatasetOptions.some((option) => option.value === kbId)) return;
    setKbId(filteredDatasetOptions[0].value);
  }, [filteredDatasetOptions, kbId, loadingDatasets]);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    const fetchDatasets = async () => {
      if (authLoading) return;

      try {
        setLoadingDatasets(true);
        const [data, directoryData] = await Promise.all([
          knowledgeApi.listRagflowDatasets(),
          knowledgeApi.listKnowledgeDirectories(),
        ]);
        const allDatasets = mergeDatasetDirectoryInfo(data?.datasets, directoryData);
        const visibleKbRefs = new Set(
          (Array.isArray(accessibleKbs) ? accessibleKbs : [])
            .map(normalizeKbRef)
            .filter(Boolean)
        );
        const list = filterDatasetsByVisibility(allDatasets, visibleKbRefs);
        const datasetValues = new Set(
          list
            .map((dataset) => getDatasetValue(dataset))
            .filter(Boolean)
        );

        setDatasets(list);
        if (list.length > 0) {
          const fallback = getDatasetValue(list[0]) || DEFAULT_KB_NAME;
          setKbId((current) => (current && datasetValues.has(current) ? current : fallback));
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

    fetchDatasets();
  }, [accessibleKbs, authLoading]);

  useEffect(() => {
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
      valid.push(file);
    }

    setSelectedFiles((prev) => {
      const map = new Map((prev || []).map((file) => [getFileUniqueKey(file), file]));
      for (const file of valid) {
        map.set(getFileUniqueKey(file), file);
      }
      return Array.from(map.values());
    });

    if (rejected.length > 0) {
      const unsupported = rejected.filter((item) => item.reason === 'unsupported').length;
      const parts = [];
      if (unsupported) parts.push(`${unsupported} 个文件后缀不在允许列表中`);
      setError(`部分文件未加入上传队列：${parts.join('；')}`);
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
        setUploadProgress({
          current: index + 1,
          total: selectedFiles.length,
          filename: getDisplayPath(file),
        });
        try {
          const result = await knowledgeApi.uploadDocument(file, kbId);
          results.push({
            ok: true,
            filename: getDisplayPath(file),
            requestId: result?.request_id || '',
          });
        } catch (err) {
          results.push({ ok: false, filename: getDisplayPath(file), error: err?.message || '上传失败' });
        }
      }

      const okCount = results.filter((item) => item.ok).length;
      const failCount = results.length - okCount;
      if (failCount === 0) {
        const requestIds = results.map((item) => item.requestId).filter(Boolean);
        setSuccess(`申请已提交：成功 ${okCount} 个${requestIds.length > 0 ? `，申请单 ${requestIds.join(', ')}` : ''}`);
        setSelectedFiles([]);
        setTimeout(() => navigate('/documents'), 1200);
        return;
        // eslint-disable-next-line no-unreachable
        setSuccess(`上传完成：成功 ${okCount} 个，等待审核`);
        setSelectedFiles([]);
        setTimeout(() => navigate('/documents'), 1200);
      } else {
        const firstFail = results.find((item) => !item.ok);
        setError(
          `申请提交完成：成功 ${okCount} 个，失败 ${failCount} 个${
            firstFail ? `。例如 ${firstFail.filename}: ${firstFail.error}` : ''
          }`
        );
        return;
        // eslint-disable-next-line no-unreachable
        setError(`上传完成：成功 ${okCount} 个，失败 ${failCount} 个${firstFail ? `。（例如：${firstFail.filename}：${firstFail.error}）` : ''}`);
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
    const changeReason = window.prompt('请输入本次上传后缀配置变更原因');
    if (changeReason === null) {
      return;
    }
    const trimmedReason = String(changeReason || '').trim();
    if (!trimmedReason) {
      setExtensionsMessage({ type: 'error', text: '变更原因不能为空' });
      return;
    }
    setSavingExtensions(true);
    setExtensionsMessage(null);
    try {
      const payload = await knowledgeApi.updateAllowedUploadExtensions(allowedExtensions, trimmedReason);
      const next = Array.isArray(payload?.allowed_extensions)
        ? payload.allowed_extensions.map(normalizeExtension).filter(Boolean)
        : allowedExtensions;
      setAllowedExtensions(Array.from(new Set(next)).sort());
      setExtensionsMessage({ type: 'success', text: '文件后缀配置已保存并记录变更原因，后续上传立即生效' });
    } catch (err) {
      setExtensionsMessage({ type: 'error', text: err.message || '保存文件后缀配置失败' });
    } finally {
      setSavingExtensions(false);
    }
  };

  return (
    <div>
      <h2 style={{ marginBottom: '24px' }}>上传知识库文档</h2>

      {error ? (
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
      ) : null}

      {success ? (
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
      ) : null}

      <div style={{ ...uploadPanelStyle, padding: isMobile ? '14px' : uploadPanelStyle.padding }}>
        <form onSubmit={handleUpload}>
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#374151' }}>
              知识库
            </label>
            <input
              type="text"
              value={kbSearchKeyword}
              onChange={(event) => setKbSearchKeyword(event.target.value)}
              data-testid="upload-kb-search"
              placeholder="输入知识库名称进行模糊匹配"
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                fontSize: '0.95rem',
                boxSizing: 'border-box',
                marginBottom: '8px',
              }}
            />
            {!loadingDatasets ? (
              <div style={{ marginBottom: '8px', fontSize: '0.85rem', color: '#6b7280' }}>
                {`匹配 ${filteredDatasetOptions.length} / ${datasetOptions.length} 个知识库`}
              </div>
            ) : null}
            <select
              value={!loadingDatasets && filteredDatasetOptions.length === 0 ? '' : kbId}
              onChange={(event) => setKbId(event.target.value)}
              disabled={loadingDatasets || filteredDatasetOptions.length === 0}
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
              ) : filteredDatasetOptions.length > 0 ? (
                filteredDatasetOptions.map((option) => (
                  <option key={option.key} value={option.value}>
                    {option.label}
                  </option>
                ))
              ) : datasetOptions.length > 0 ? (
                <option value="">没有匹配到知识库，请调整搜索关键词</option>
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

          <div style={{ marginTop: '8px', fontSize: '0.85rem', color: '#6b7280', lineHeight: 1.6 }}>
            {`支持后缀：${acceptAttr}（文件夹上传会递归处理）`}
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
            padding: isMobile ? '14px' : '16px',
            backgroundColor: '#f9fafb',
            borderRadius: '4px',
            fontSize: '0.9rem',
            color: '#6b7280',
            lineHeight: 1.6,
          }}
        >
          <div style={{ marginBottom: '8px', fontWeight: '500', color: '#374151' }}>上传流程</div>
          <ol style={{ margin: 0, paddingLeft: '20px' }}>
            <li>选择知识库并上传文件</li>
            <li>文档进入“待审核”状态</li>
            <li>审核通过后自动同步到知识库</li>
          </ol>
        </div>
      </div>
    </div>
  );
};

export default KnowledgeUpload;
