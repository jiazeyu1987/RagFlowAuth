import React, { useEffect, useState } from 'react';
import documentClient, { DOCUMENT_SOURCE } from '../../../shared/documents/documentClient';

const MOBILE_BREAKPOINT = 768;

export function DocumentReviewOverwriteModal({
  activeDocMap,
  handleOverwriteKeepOld,
  handleOverwriteUseNew,
  openDiff,
  openLocalPreview,
  overwritePrompt,
  setOverwritePrompt,
}) {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  if (!overwritePrompt) return null;

  const newFilename = activeDocMap.get(overwritePrompt.newDocId)?.filename || '';
  const actionButtonStyle = (primary = false) => ({
    padding: '8px 12px',
    borderRadius: '8px',
    border: primary ? 'none' : '1px solid #d1d5db',
    background: primary ? '#3b82f6' : 'white',
    color: primary ? 'white' : '#111827',
    cursor: 'pointer',
    width: isMobile ? '100%' : 'auto',
  });

  return (
    <div
      data-testid="docs-overwrite-modal"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.35)',
        display: 'flex',
        alignItems: isMobile ? 'stretch' : 'center',
        justifyContent: 'center',
        zIndex: 50,
        padding: '16px',
      }}
      onClick={() => setOverwritePrompt(null)}
    >
      <div
        style={{
          width: 'min(820px, 100%)',
          maxHeight: isMobile ? '100%' : '90vh',
          background: 'white',
          borderRadius: '12px',
          border: '1px solid #e5e7eb',
          padding: '16px',
          overflowY: 'auto',
          margin: isMobile ? 'auto 0' : 0,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: '10px',
            alignItems: isMobile ? 'stretch' : 'center',
            flexDirection: isMobile ? 'column' : 'row',
          }}
        >
          <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>检测到可能重复文档</div>
          <button
            type="button"
            onClick={() => setOverwritePrompt(null)}
            data-testid="docs-overwrite-close"
            style={{
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: '1.2rem',
              alignSelf: isMobile ? 'flex-end' : 'auto',
            }}
          >
            ×
          </button>
        </div>

        <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: '12px' }}>
          <div style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '12px' }}>
            <div style={{ fontWeight: 700, marginBottom: '6px', color: '#b91c1c' }}>当前生效版本</div>
            <div style={{ color: '#111827', wordBreak: 'break-all' }}>{overwritePrompt.oldDoc.filename}</div>
            <div style={{ color: '#6b7280', fontSize: '0.9rem', marginTop: '6px' }}>
              版本：v{overwritePrompt.oldDoc.version_no || 1}
            </div>
            <div style={{ color: '#6b7280', fontSize: '0.9rem', marginTop: '6px' }}>
              上传时间：
              {overwritePrompt.oldDoc.uploaded_at_ms
                ? new Date(overwritePrompt.oldDoc.uploaded_at_ms).toLocaleString('zh-CN')
                : ''}
            </div>
            <div style={{ marginTop: '10px', display: 'flex', gap: '8px', flexDirection: isMobile ? 'column' : 'row' }}>
              <button
                type="button"
                onClick={() => openLocalPreview(overwritePrompt.oldDoc.doc_id, overwritePrompt.oldDoc.filename)}
                data-testid="docs-overwrite-old-preview"
                style={{ ...actionButtonStyle(), background: '#10b981', color: 'white', border: 'none' }}
              >
                查看预览
              </button>
              <button
                type="button"
                onClick={() =>
                  documentClient.downloadToBrowser({
                    source: DOCUMENT_SOURCE.KNOWLEDGE,
                    docId: overwritePrompt.oldDoc.doc_id,
                  })
                }
                data-testid="docs-overwrite-old-download"
                style={actionButtonStyle()}
              >
                下载
              </button>
            </div>
          </div>

          <div style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '12px' }}>
            <div style={{ fontWeight: 700, marginBottom: '6px', color: '#1d4ed8' }}>新上传版本（待审核）</div>
            <div style={{ color: '#111827', wordBreak: 'break-all' }}>{newFilename}</div>
            <div style={{ color: '#6b7280', fontSize: '0.9rem', marginTop: '6px', wordBreak: 'break-all' }}>
              归一化名称：{overwritePrompt.normalized || ''}
            </div>
            <div style={{ marginTop: '10px', display: 'flex', gap: '8px', flexDirection: isMobile ? 'column' : 'row' }}>
              <button
                type="button"
                onClick={() => openLocalPreview(overwritePrompt.newDocId, newFilename)}
                data-testid="docs-overwrite-new-preview"
                style={{ ...actionButtonStyle(), background: '#10b981', color: 'white', border: 'none' }}
              >
                查看预览
              </button>
              <button
                type="button"
                onClick={() =>
                  documentClient.downloadToBrowser({
                    source: DOCUMENT_SOURCE.KNOWLEDGE,
                    docId: overwritePrompt.newDocId,
                  })
                }
                data-testid="docs-overwrite-new-download"
                style={actionButtonStyle()}
              >
                下载
              </button>
            </div>
          </div>
        </div>

        <div
          style={{
            marginTop: '14px',
            display: 'flex',
            justifyContent: 'space-between',
            gap: '10px',
            alignItems: isMobile ? 'stretch' : 'center',
            flexDirection: isMobile ? 'column' : 'row',
          }}
        >
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
            style={actionButtonStyle()}
          >
            对比当前版本差异
          </button>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', width: isMobile ? '100%' : 'auto', flexDirection: isMobile ? 'column' : 'row' }}>
            <button
              type="button"
              onClick={handleOverwriteKeepOld}
              data-testid="docs-overwrite-keep-old"
              style={actionButtonStyle()}
            >
              保留旧文档并驳回新文档
            </button>
            <button
              type="button"
              onClick={handleOverwriteUseNew}
              data-testid="docs-overwrite-use-new"
              style={actionButtonStyle(true)}
            >
              生成新版本并替换当前版本
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
