import React from 'react';
import ReactDiffViewer from 'react-diff-viewer-continued';

export function DocumentReviewDiffModal({
  diffLoading,
  diffOldText,
  diffNewText,
  diffOnly,
  diffOpen,
  diffTitle,
  onClose,
  onDiffOnlyChange,
}) {
  if (!diffOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.35)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 70,
        padding: '16px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: 'min(1200px, 100%)',
          background: 'white',
          borderRadius: '12px',
          border: '1px solid #e5e7eb',
          padding: '16px',
          height: '82vh',
          display: 'flex',
          flexDirection: 'column',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
          <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>{diffTitle || '文档差异对比'}</div>
          <button
            type="button"
            onClick={onClose}
            style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '1.2rem' }}
          >
            ×
          </button>
        </div>

        <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <label style={{ display: 'flex', gap: '8px', alignItems: 'center', color: '#374151' }}>
            <input type="checkbox" checked={diffOnly} onChange={(e) => onDiffOnlyChange(e.target.checked)} />
            只看差异
          </label>
          <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>左侧为旧文档，右侧为新文档</div>
        </div>

        <div style={{ marginTop: '10px', flex: 1, overflow: 'auto', border: '1px solid #e5e7eb', borderRadius: '10px' }}>
          {diffLoading ? (
            <div style={{ padding: '24px', color: '#6b7280' }}>正在加载差异...</div>
          ) : (
            <div style={{ padding: '12px' }}>
              <ReactDiffViewer
                oldValue={diffOldText || ''}
                newValue={diffNewText || ''}
                splitView={true}
                showDiffOnly={diffOnly}
                disableWordDiff={false}
                compareMethod="diffLines"
                leftTitle="旧文档"
                rightTitle="新文档"
                styles={{
                  variables: {
                    light: {
                      diffViewerBackground: '#ffffff',
                      addedBackground: '#dcfce7',
                      removedBackground: '#fee2e2',
                      gutterBackground: '#f9fafb',
                      gutterBackgroundDark: '#f3f4f6',
                      highlightBackground: '#fff7ed',
                    },
                  },
                  contentText: { fontSize: 12 },
                  line: { fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace" },
                }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
