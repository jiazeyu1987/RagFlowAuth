import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { knowledgeApi } from '../features/knowledge/api';

const MAX_FILE_SIZE_BYTES = 16 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = ['.txt', '.pdf', '.docx', '.md', '.xlsx', '.xls', '.csv', '.png', '.jpg', '.jpeg'];

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

const KnowledgeUpload = () => {
  const navigate = useNavigate();
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [kbId, setKbId] = useState('展厅');
  const [datasets, setDatasets] = useState([]);
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null); // {current, total, filename}
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        setLoadingDatasets(true);
        const data = await knowledgeApi.listRagflowDatasets();
        const list = data.datasets || [];
        setDatasets(list);

        if (list.length > 0) {
          setKbId(list[0].name || list[0].id);
          setError(null);
        } else {
          setError('您没有被分配任何知识库权限，请联系管理员');
        }
      } catch (err) {
        setError(err.message || '无法加载知识库列表，请检查网络连接');
        setDatasets([]);
      } finally {
        setLoadingDatasets(false);
      }
    };

    fetchDatasets();
  }, []);

  const addFiles = (filesLike) => {
    const incoming = Array.from(filesLike || []);
    if (incoming.length === 0) return;

    const valid = [];
    const rejected = [];

    for (const f of incoming) {
      const ext = getFileExtensionLower(f.name);
      if (!ACCEPTED_EXTENSIONS.includes(ext)) {
        rejected.push({ file: f, reason: 'unsupported' });
        continue;
      }
      if (f.size > MAX_FILE_SIZE_BYTES) {
        rejected.push({ file: f, reason: 'too_large' });
        continue;
      }
      valid.push(f);
    }

    setSelectedFiles((prev) => {
      const existing = prev || [];
      const map = new Map();
      for (const f of existing) map.set(`${f.name}__${f.size}__${f.lastModified}`, f);
      for (const f of valid) map.set(`${f.name}__${f.size}__${f.lastModified}`, f);
      return Array.from(map.values());
    });

    if (rejected.length > 0) {
      const tooLarge = rejected.filter((r) => r.reason === 'too_large').length;
      const unsupported = rejected.filter((r) => r.reason === 'unsupported').length;
      const parts = [];
      if (tooLarge) parts.push(`${tooLarge} 个文件超过 16MB`);
      if (unsupported) parts.push(`${unsupported} 个文件类型不支持`);
      setError(`部分文件未添加：${parts.join('，')}`);
    } else {
      setError(null);
    }
  };

  const handleFileSelect = (e) => {
    addFiles(e.target.files);
    // allow selecting same file again later
    e.target.value = '';
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (uploading) return;
    addFiles(e.dataTransfer?.files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!uploading) setDragActive(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const removeFile = (key) => {
    setSelectedFiles((prev) => (prev || []).filter((f) => `${f.name}__${f.size}__${f.lastModified}` !== key));
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFiles || selectedFiles.length === 0) {
      setError('请选择文件');
      return;
    }

    setUploading(true);
    setUploadProgress(null);
    setError(null);
    setSuccess(null);

    try {
      const results = [];
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        setUploadProgress({ current: i + 1, total: selectedFiles.length, filename: file.name });
        try {
          const result = await knowledgeApi.uploadDocument(file, kbId);
          results.push({ ok: true, filename: result?.filename || file.name });
        } catch (err) {
          results.push({ ok: false, filename: file.name, error: err?.message || '上传失败' });
        }
      }

      const okCount = results.filter((r) => r.ok).length;
      const failCount = results.length - okCount;

      if (failCount === 0) {
        setSuccess(`已上传 ${okCount} 个文件，等待审核`);
        setSelectedFiles([]);
        setTimeout(() => navigate('/documents'), 1200);
      } else {
        const firstFail = results.find((r) => !r.ok);
        setError(`上传完成：成功 ${okCount} 个，失败 ${failCount} 个。${firstFail?.filename ? `（例如：${firstFail.filename}：${firstFail.error}）` : ''}`);
      }
    } catch (err) {
      setError(err.message || '上传失败');
    } finally {
      setUploading(false);
      setUploadProgress(null);
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

      <div
        style={{
          backgroundColor: 'white',
          padding: '32px',
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          maxWidth: '600px',
        }}
      >
        <form onSubmit={handleUpload}>
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#374151' }}>
              知识库
            </label>
            <select
              value={kbId}
              onChange={(e) => setKbId(e.target.value)}
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
                datasets.map((ds) => (
                  <option key={ds.id} value={ds.name || ds.id}>
                    {ds.name || ds.id}
                  </option>
                ))
              ) : (
                <option value="展厅">展厅</option>
              )}
            </select>
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#374151' }}>
              选择文件
            </label>
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
                accept=".txt,.pdf,.docx,.md,.xlsx,.xls,.csv,.png,.jpg,.jpeg"
                multiple
                style={{ display: 'none' }}
                id="fileInput"
                data-testid="upload-file-input"
              />
              <div style={{ fontSize: '2rem', marginBottom: '12px' }}>文件</div>
              <div style={{ color: '#6b7280', marginBottom: '8px' }}>
                {selectedFiles && selectedFiles.length > 0
                  ? `已选择 ${selectedFiles.length} 个文件`
                  : '拖动文件到此处，或点击选择文件（支持多选）'}
              </div>
              {uploadProgress && (
                <div style={{ fontSize: '0.9rem', color: '#6b7280' }} data-testid="upload-progress">
                  正在上传 {uploadProgress.current}/{uploadProgress.total}：{uploadProgress.filename}
                </div>
              )}
            </div>

            {selectedFiles && selectedFiles.length > 0 && (
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
                <div style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: 8,
                  overflow: 'hidden',
                }}>
                  {selectedFiles.map((f) => {
                    const key = `${f.name}__${f.size}__${f.lastModified}`;
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
                            {f.name}
                          </div>
                          <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{formatBytes(f.size)}</div>
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
              支持的文件类型：.txt, .pdf, .docx, .md, .xlsx, .xls, .csv, .png, .jpg, .jpeg（最大 16MB）
            </div>
          </div>

          <button
            type="submit"
            disabled={!selectedFiles || selectedFiles.length === 0 || uploading}
            data-testid="upload-submit"
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: !selectedFiles || selectedFiles.length === 0 || uploading ? '#9ca3af' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontSize: '1rem',
              fontWeight: '500',
              cursor: !selectedFiles || selectedFiles.length === 0 || uploading ? 'not-allowed' : 'pointer',
            }}
          >
            {uploading ? '上传中...' : `上传文档${selectedFiles && selectedFiles.length > 0 ? `（${selectedFiles.length}）` : ''}`}
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
