import React from 'react';
import documentClient, { DOCUMENT_SOURCE } from '../../../shared/documents/documentClient';
import { formatDateTime } from '../utils';

const overlayStyle = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0,0,0,0.35)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 50,
  padding: '16px',
};

const panelStyle = {
  width: 'min(820px, 100%)',
  background: 'white',
  borderRadius: '12px',
  border: '1px solid #e5e7eb',
  padding: '16px',
};

const sectionStyle = {
  border: '1px solid #e5e7eb',
  borderRadius: '10px',
  padding: '12px',
};

const actionButtonStyle = {
  padding: '8px 12px',
  borderRadius: '8px',
  border: '1px solid #d1d5db',
  background: 'white',
  cursor: 'pointer',
};

const previewButtonStyle = {
  ...actionButtonStyle,
  border: 'none',
  background: '#10b981',
  color: 'white',
};

const OverwriteModal = ({ prompt, newDoc, onClose, onPreview, onOpenDiff, onKeepOld, onUseNew }) => {
  if (!prompt) return null;

  return (
    <div data-testid="docs-overwrite-modal" style={overlayStyle} onClick={onClose}>
      <div style={panelStyle} onClick={(event) => event.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
          <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>检测到重复文档冲突</div>
          <button
            type="button"
            onClick={onClose}
            data-testid="docs-overwrite-close"
            style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '1.2rem' }}
          >
            ×
          </button>
        </div>

        <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div style={sectionStyle}>
            <div style={{ fontWeight: 700, marginBottom: '6px', color: '#b91c1c' }}>已存在文档</div>
            <div style={{ color: '#111827' }}>{prompt.oldDoc.filename}</div>
            <div style={{ color: '#6b7280', fontSize: '0.9rem', marginTop: '6px' }}>
              上传时间：{formatDateTime(prompt.oldDoc.uploaded_at_ms)}
            </div>
            <div style={{ marginTop: '10px' }}>
              <button
                type="button"
                onClick={() => onPreview(prompt.oldDoc.doc_id, prompt.oldDoc.filename)}
                data-testid="docs-overwrite-old-preview"
                style={{ ...previewButtonStyle, marginRight: '8px' }}
              >
                预览文档
              </button>
              <button
                type="button"
                onClick={() => documentClient.downloadToBrowser({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId: prompt.oldDoc.doc_id })}
                data-testid="docs-overwrite-old-download"
                style={actionButtonStyle}
              >
                下载
              </button>
            </div>
          </div>

          <div style={sectionStyle}>
            <div style={{ fontWeight: 700, marginBottom: '6px', color: '#1d4ed8' }}>待审核文档</div>
            <div style={{ color: '#111827' }}>{newDoc?.filename || ''}</div>
            <div style={{ color: '#6b7280', fontSize: '0.9rem', marginTop: '6px' }}>归一化名称：{prompt.normalized || ''}</div>
            <div style={{ marginTop: '10px' }}>
              <button
                type="button"
                onClick={() => onPreview(prompt.newDocId, newDoc?.filename || '')}
                data-testid="docs-overwrite-new-preview"
                style={{ ...previewButtonStyle, marginRight: '8px' }}
              >
                预览文档
              </button>
              <button
                type="button"
                onClick={() => documentClient.downloadToBrowser({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId: prompt.newDocId })}
                data-testid="docs-overwrite-new-download"
                style={{ ...actionButtonStyle, marginRight: '8px' }}
              >
                下载
              </button>
            </div>
          </div>
        </div>

        <div style={{ marginTop: '14px', display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
          <button
            type="button"
            onClick={() => onOpenDiff(prompt.oldDoc.doc_id, prompt.oldDoc.filename, prompt.newDocId, newDoc?.filename || '')}
            style={actionButtonStyle}
          >
            查看文件差异
          </button>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button type="button" onClick={onKeepOld} data-testid="docs-overwrite-keep-old" style={actionButtonStyle}>
              保留旧文档并驳回新上传
            </button>
            <button
              type="button"
              onClick={onUseNew}
              data-testid="docs-overwrite-use-new"
              style={{ ...actionButtonStyle, border: 'none', background: '#3b82f6', color: 'white' }}
            >
              使用新文档覆盖
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OverwriteModal;
