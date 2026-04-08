import { useEffect, useRef, useState } from 'react';

import { knowledgeUploadApi } from './api';
import { getDisplayPath, getFileExtensionLower, getFileUniqueKey } from './utils';

const normalizeKbRef = (value) => String(value || '').trim();

export default function useKnowledgeUploadFiles({
  kbId,
  loadingExtensions,
  allowedExtensions,
  extensionSet,
  navigate,
  setError,
  setSuccess,
}) {
  const navigateTimerRef = useRef(null);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => () => {
    if (navigateTimerRef.current) {
      clearTimeout(navigateTimerRef.current);
    }
  }, []);

  const addFiles = (filesLike) => {
    if (loadingExtensions) {
      setError('upload_extensions_loading');
      return;
    }
    if (allowedExtensions.length === 0) {
      setError('upload_extensions_unavailable');
      return;
    }
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
    if (loadingExtensions) {
      setError('upload_extensions_loading');
      return;
    }
    if (allowedExtensions.length === 0) {
      setError('upload_extensions_unavailable');
      return;
    }
    const normalizedKbId = normalizeKbRef(kbId);
    if (!normalizedKbId) {
      setError('missing_kb_id');
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
          const result = await knowledgeUploadApi.uploadDocument(file, normalizedKbId);
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

  return {
    selectedFiles,
    uploading,
    uploadProgress,
    dragActive,
    handleUpload,
    handleFileSelect,
    handleFolderSelect,
    handleDrop,
    handleDragOver,
    handleDragLeave,
    clearSelectedFiles,
    removeFile,
  };
}
