import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { knowledgeApi } from '../features/knowledge/api';

const KnowledgeUpload = () => {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState(null);
  const [kbId, setKbId] = useState('展厅');
  const [datasets, setDatasets] = useState([]);
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

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

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const maxSize = 16 * 1024 * 1024;
    if (file.size > maxSize) {
      setError('文件大小不能超过 16MB');
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setError(null);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('请选择文件');
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await knowledgeApi.uploadDocument(selectedFile, kbId);
      setSuccess(`文件“${result.filename}”上传成功，等待审核`);
      setSelectedFile(null);
      setTimeout(() => navigate('/documents'), 1200);
    } catch (err) {
      setError(err.message || '上传失败');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <h2 style={{ marginBottom: '24px' }}>上传知识库文档</h2>

      {error && (
        <div
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
              style={{
                border: '2px dashed #d1d5db',
                borderRadius: '4px',
                padding: '40px',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'border-color 0.2s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#3b82f6')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#d1d5db')}
              onClick={() => document.getElementById('fileInput')?.click()}
            >
              <input
                type="file"
                onChange={handleFileSelect}
                accept=".txt,.pdf,.doc,.docx,.md,.ppt,.pptx"
                style={{ display: 'none' }}
                id="fileInput"
              />
              <div style={{ fontSize: '2rem', marginBottom: '12px' }}>文件</div>
              <div style={{ color: '#6b7280', marginBottom: '8px' }}>
                {selectedFile ? selectedFile.name : '点击选择文件'}
              </div>
              {selectedFile && (
                <div style={{ fontSize: '0.9rem', color: '#6b7280' }}>{(selectedFile.size / 1024).toFixed(2)} KB</div>
              )}
            </div>
            <div style={{ marginTop: '8px', fontSize: '0.85rem', color: '#6b7280' }}>
              支持的文件类型：.txt, .pdf, .doc, .docx, .md, .ppt, .pptx（最大 16MB）
            </div>
          </div>

          <button
            type="submit"
            disabled={!selectedFile || uploading}
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: !selectedFile || uploading ? '#9ca3af' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontSize: '1rem',
              fontWeight: '500',
              cursor: !selectedFile || uploading ? 'not-allowed' : 'pointer',
            }}
          >
            {uploading ? '上传中...' : '上传文档'}
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

