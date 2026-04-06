import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../../../hooks/useAuth';
import { knowledgeApi } from '../api';
import { knowledgeUploadApi } from './api';
import {
  DEFAULT_ACCEPTED_EXTENSIONS,
  DEFAULT_KB_NAME,
} from './constants';
import {
  getDisplayPath,
  getFileExtensionLower,
  getFileUniqueKey,
  normalizeExtension,
} from './utils';

const MOBILE_BREAKPOINT = 768;

const getInitialIsMobile = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};

const normalizeKbRef = (value) => String(value || '').trim();

const getDatasetValue = (dataset) => dataset?.name || dataset?.id || '';

const getDatasetLabel = (dataset) => {
  const name = String(dataset?.name || dataset?.id || '').trim();
  const nodePath = String(dataset?.node_path || '').trim();
  if (!name) return '';
  if (!nodePath || nodePath === '/') return name;
  return `${nodePath}/${name}`;
};

const mergeDatasetDirectoryInfo = (datasetsPayload, directoryPayload) => {
  const list = Array.isArray(datasetsPayload) ? datasetsPayload : [];
  const directoryDatasets = Array.isArray(directoryPayload?.datasets)
    ? directoryPayload.datasets
    : [];
  const nodePathById = new Map();
  const nodePathByName = new Map();

  directoryDatasets.forEach((dataset) => {
    const nodePath = String(dataset?.node_path || '').trim();
    const id = normalizeKbRef(dataset?.id);
    const name = normalizeKbRef(dataset?.name);

    if (id) nodePathById.set(id, nodePath);
    if (name) nodePathByName.set(name, nodePath);
  });

  return list.map((dataset) => {
    const id = normalizeKbRef(dataset?.id);
    const name = normalizeKbRef(dataset?.name);
    const nodePath = nodePathById.get(id) || nodePathByName.get(name) || dataset?.node_path || '/';

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

export default function useKnowledgeUploadPage() {
  const navigate = useNavigate();
  const navigateTimerRef = useRef(null);
  const { accessibleKbs, loading: authLoading, canViewKbConfig } = useAuth();
  const canManageExtensions = canViewKbConfig();
  const [isMobile, setIsMobile] = useState(getInitialIsMobile);
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
    const values =
      Array.isArray(allowedExtensions) && allowedExtensions.length > 0
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
        .sort((left, right) =>
          String(left.label || '').localeCompare(String(right.label || ''), 'zh-Hans-CN')
        ),
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

  useEffect(() => () => {
    if (navigateTimerRef.current) {
      clearTimeout(navigateTimerRef.current);
    }
  }, []);

  useEffect(() => {
    let active = true;

    const fetchDatasets = async () => {
      if (authLoading) return;

      try {
        setLoadingDatasets(true);

        const [datasetPayload, directoryPayload] = await Promise.all([
          knowledgeApi.listRagflowDatasets(),
          knowledgeApi.listKnowledgeDirectories(),
        ]);

        if (!active) return;

        const allDatasets = mergeDatasetDirectoryInfo(datasetPayload, directoryPayload);
        const visibleKbRefs = new Set(
          (Array.isArray(accessibleKbs) ? accessibleKbs : [])
            .map(normalizeKbRef)
            .filter(Boolean)
        );
        const visibleDatasets = filterDatasetsByVisibility(allDatasets, visibleKbRefs);
        const datasetValues = new Set(
          visibleDatasets.map((dataset) => getDatasetValue(dataset)).filter(Boolean)
        );

        setDatasets(visibleDatasets);

        if (visibleDatasets.length > 0) {
          const fallbackKb = getDatasetValue(visibleDatasets[0]) || DEFAULT_KB_NAME;
          setKbId((current) => (current && datasetValues.has(current) ? current : fallbackKb));
          setError(null);
        } else {
          setKbId(DEFAULT_KB_NAME);
          setError('您没有被分配任何知识库权限，请联系管理员');
        }
      } catch (requestError) {
        if (!active) return;
        setDatasets([]);
        setError(requestError?.message || '无法加载知识库列表，请检查网络连接');
      } finally {
        if (active) {
          setLoadingDatasets(false);
        }
      }
    };

    fetchDatasets();

    return () => {
      active = false;
    };
  }, [accessibleKbs, authLoading]);

  useEffect(() => {
    let active = true;

    const fetchAllowedExtensions = async () => {
      try {
        setLoadingExtensions(true);
        const payload = await knowledgeUploadApi.getAllowedExtensions();
        if (!active) return;

        const normalizedExtensions =
          Array.isArray(payload?.allowed_extensions) && payload.allowed_extensions.length > 0
            ? payload.allowed_extensions.map(normalizeExtension).filter(Boolean)
            : DEFAULT_ACCEPTED_EXTENSIONS;

        setAllowedExtensions(Array.from(new Set(normalizedExtensions)).sort());
      } catch (requestError) {
        if (!active) return;
        setAllowedExtensions(DEFAULT_ACCEPTED_EXTENSIONS);
        setExtensionsMessage({
          type: 'error',
          text:
            requestError?.message || '无法加载可上传文件后缀，已回退到默认配置',
        });
      } finally {
        if (active) {
          setLoadingExtensions(false);
        }
      }
    };

    fetchAllowedExtensions();

    return () => {
      active = false;
    };
  }, []);

  const addFiles = (filesLike) => {
    const incomingFiles = Array.from(filesLike || []);
    if (incomingFiles.length === 0) return;

    const validFiles = [];
    const rejectedFiles = [];

    incomingFiles.forEach((file) => {
      const extension = getFileExtensionLower(file.name);
      if (!extensionSet.has(extension)) {
        rejectedFiles.push(file);
        return;
      }
      validFiles.push(file);
    });

    setSelectedFiles((previous) => {
      const uniqueFiles = new Map(
        (previous || []).map((file) => [getFileUniqueKey(file), file])
      );

      validFiles.forEach((file) => {
        uniqueFiles.set(getFileUniqueKey(file), file);
      });

      return Array.from(uniqueFiles.values());
    });

    setSuccess(null);

    if (rejectedFiles.length > 0) {
      setError(`部分文件未加入上传队列：${rejectedFiles.length} 个文件后缀不在允许列表中`);
      return;
    }

    setError(null);
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
        setUploadProgress({
          current: index + 1,
          total: selectedFiles.length,
          filename: getDisplayPath(file),
        });

        try {
          const result = await knowledgeUploadApi.uploadDocument(file, kbId);
          results.push({
            ok: true,
            filename: getDisplayPath(file),
            requestId: result?.request_id || '',
          });
        } catch (requestError) {
          results.push({
            ok: false,
            filename: getDisplayPath(file),
            error: requestError?.message || '上传失败',
          });
        }
      }

      const successCount = results.filter((item) => item.ok).length;
      const failedCount = results.length - successCount;

      if (failedCount === 0) {
        const requestIds = results.map((item) => item.requestId).filter(Boolean);
        const requestIdText = requestIds.length > 0 ? `，申请单 ${requestIds.join(', ')}` : '';

        setSuccess(`申请已提交：成功 ${successCount} 个${requestIdText}`);
        setSelectedFiles([]);

        if (navigateTimerRef.current) {
          clearTimeout(navigateTimerRef.current);
        }
        navigateTimerRef.current = setTimeout(() => navigate('/approvals?view=mine'), 1200);
        return;
      }

      const firstFailedResult = results.find((item) => !item.ok);
      const failureExample = firstFailedResult
        ? `。例如 ${firstFailedResult.filename}: ${firstFailedResult.error}`
        : '';

      setError(
        `申请提交完成：成功 ${successCount} 个，失败 ${failedCount} 个${failureExample}`
      );
    } catch (requestError) {
      setError(requestError?.message || '上传失败');
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

    if (!uploading) {
      addFiles(event.dataTransfer?.files);
    }
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    event.stopPropagation();

    if (!uploading) {
      setDragActive(true);
    }
  };

  const handleDragLeave = (event) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(false);
  };

  const clearSelectedFiles = () => {
    setSelectedFiles([]);
  };

  const removeFile = (fileKey) => {
    setSelectedFiles((previous) =>
      previous.filter((file) => getFileUniqueKey(file) !== fileKey)
    );
  };

  const handleAddExtension = () => {
    const normalizedExtension = normalizeExtension(extensionDraft);
    if (!normalizedExtension) {
      setExtensionsMessage({
        type: 'error',
        text: '请输入有效的文件后缀，例如 .pdf',
      });
      return;
    }

    if (/\s/.test(normalizedExtension) || normalizedExtension.length < 2) {
      setExtensionsMessage({
        type: 'error',
        text: '文件后缀格式不正确',
      });
      return;
    }

    setAllowedExtensions((previous) =>
      Array.from(new Set([...previous, normalizedExtension])).sort()
    );
    setExtensionDraft('');
    setExtensionsMessage(null);
  };

  const handleDeleteExtension = (extension) => {
    setAllowedExtensions((previous) => previous.filter((item) => item !== extension));
    setExtensionsMessage(null);
  };

  const handleSaveExtensions = async () => {
    if (!canManageExtensions) return;

    if (allowedExtensions.length === 0) {
      setExtensionsMessage({
        type: 'error',
        text: '至少保留一个允许上传的后缀',
      });
      return;
    }

    const changeReason = window.prompt('请输入本次上传后缀配置变更原因');
    if (changeReason === null) return;

    const trimmedReason = String(changeReason || '').trim();
    if (!trimmedReason) {
      setExtensionsMessage({
        type: 'error',
        text: '变更原因不能为空',
      });
      return;
    }

    setSavingExtensions(true);
    setExtensionsMessage(null);

    try {
      const payload = await knowledgeUploadApi.updateAllowedExtensions(
        allowedExtensions,
        trimmedReason
      );
      const nextExtensions = Array.isArray(payload?.allowed_extensions)
        ? payload.allowed_extensions.map(normalizeExtension).filter(Boolean)
        : allowedExtensions;

      setAllowedExtensions(Array.from(new Set(nextExtensions)).sort());
      setExtensionsMessage({
        type: 'success',
        text: '文件后缀配置已保存并记录变更原因，后续上传立即生效',
      });
    } catch (requestError) {
      setExtensionsMessage({
        type: 'error',
        text: requestError?.message || '保存文件后缀配置失败',
      });
    } finally {
      setSavingExtensions(false);
    }
  };

  return {
    canManageExtensions,
    isMobile,
    selectedFiles,
    kbId,
    kbSearchKeyword,
    datasets,
    loadingDatasets,
    uploading,
    uploadProgress,
    error,
    success,
    dragActive,
    allowedExtensions,
    loadingExtensions,
    savingExtensions,
    extensionDraft,
    extensionsMessage,
    acceptAttr,
    datasetOptions,
    filteredDatasetOptions,
    setKbId,
    setKbSearchKeyword,
    setExtensionDraft,
    handleUpload,
    handleFileSelect,
    handleFolderSelect,
    handleDrop,
    handleDragOver,
    handleDragLeave,
    clearSelectedFiles,
    removeFile,
    handleAddExtension,
    handleDeleteExtension,
    handleSaveExtensions,
  };
}
