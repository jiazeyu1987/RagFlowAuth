import React from 'react';
import documentClient, { DOCUMENT_SOURCE } from '../../../shared/documents/documentClient';

export function DocumentReviewOverwriteModal({
  activeDocMap,
  handleOverwriteKeepOld,
  handleOverwriteUseNew,
  openDiff,
  openLocalPreview,
  overwritePrompt,
  setOverwritePrompt,
}) {
  if (!overwritePrompt) return null;

  const newFilename = activeDocMap.get(overwritePrompt.newDocId)?.filename || '';

  return (
    <div
      data-testid="docs-overwrite-modal"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.35)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
        padding: '16px',
      }}
      onClick={() => setOverwritePrompt(null)}
    >
      <div
        style={{
          width: 'min(820px, 100%)',
          background: 'white',
          borderRadius: '12px',
          border: '1px solid #e5e7eb',
          padding: '16px',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
          <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>检测到可能重复文档</div>
          <button
            type="button"
            onClick={() => setOverwritePrompt(null)}
            data-testid="docs-overwrite-close"
            style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '1.2rem' }}
          >
            ×
          </button>
        </div>

        <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '12px' }}>
            <div style={{ fontWeight: 700, marginBottom: '6px', color: '#b91c1c' }}>已通过文档</div>
            <div style={{ color: '#111827' }}>{overwritePrompt.oldDoc.filename}</div>
            <div style={{ color: '#6b7280', fontSize: '0.9rem', marginTop: '6px' }}>
              上传时间：{overwritePrompt.oldDoc.uploaded_at_ms ? new Date(overwritePrompt.oldDoc.uploaded_at_ms).toLocaleString('zh-CN') : ''}
            </div>
            <div style={{ marginTop: '10px' }}>
              <button
                type="button"
                onClick={() => openLocalPreview(overwritePrompt.oldDoc.doc_id, overwritePrompt.oldDoc.filename)}
                data-testid="docs-overwrite-old-preview"
                style={{
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: 'none',
                  background: '#10b981',
                  color: 'white',
                  cursor: 'pointer',
                  marginRight: '8px',
                }}
              >
                查看预览
              </button>
              <button
                type="button"
                onClick={() => documentClient.downloadToBrowser({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId: overwritePrompt.oldDoc.doc_id })}
                data-testid="docs-overwrite-old-download"
                style={{
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: '1px solid #d1d5db',
                  background: 'white',
                  cursor: 'pointer',
                }}
              >
                下载
              </button>
            </div>
          </div>

          <div style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '12px' }}>
            <div style={{ fontWeight: 700, marginBottom: '6px', color: '#1d4ed8' }}>待审核文档</div>
            <div style={{ color: '#111827' }}>{newFilename}</div>
            <div style={{ color: '#6b7280', fontSize: '0.9rem', marginTop: '6px' }}>
              归一化名称：{overwritePrompt.normalized || ''}
            </div>
            <div style={{ marginTop: '10px' }}>
              <button
                type="button"
                onClick={() => openLocalPreview(overwritePrompt.newDocId, newFilename)}
                data-testid="docs-overwrite-new-preview"
                style={{
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: 'none',
                  background: '#10b981',
                  color: 'white',
                  cursor: 'pointer',
                  marginRight: '8px',
                }}
              >
                查看预览
              </button>
              <button
                type="button"
                onClick={() => documentClient.downloadToBrowser({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId: overwritePrompt.newDocId })}
                data-testid="docs-overwrite-new-download"
                style={{
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: '1px solid #d1d5db',
                  background: 'white',
                  cursor: 'pointer',
                  marginRight: '8px',
                }}
              >
                下载
              </button>
            </div>
          </div>
        </div>

        <div style={{ marginTop: '14px', display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
          <button
            type="button"
            onClick={() =>
              openDiff(
                overwritePrompt.oldDoc.doc_id,
                overwritePrompt.oldDoc.filename,
                overwritePrompt.newDocId,
                newFilename,
              )
            }
            style={{
              padding: '10px 12px',
              borderRadius: '8px',
              border: '1px solid #d1d5db',
              background: 'white',
              cursor: 'pointer',
            }}
          >
            对比差异
          </button>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button
              type="button"
              onClick={handleOverwriteKeepOld}
              data-testid="docs-overwrite-keep-old"
              style={{
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid #d1d5db',
                background: 'white',
                cursor: 'pointer',
              }}
            >
              保留旧文档并驳回新文档
            </button>
            <button
              type="button"
              onClick={handleOverwriteUseNew}
              data-testid="docs-overwrite-use-new"
              style={{
                padding: '10px 12px',
                borderRadius: '8px',
                border: 'none',
                background: '#3b82f6',
                color: 'white',
                cursor: 'pointer',
              }}
            >
              使用新文档覆盖
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
