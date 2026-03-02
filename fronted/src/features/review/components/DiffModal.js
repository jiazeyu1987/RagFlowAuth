import React from 'react';
import ReactDiffViewer from 'react-diff-viewer-continued';

const overlayStyle = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0,0,0,0.35)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 70,
  padding: '16px',
};

const cardStyle = {
  width: 'min(1200px, 100%)',
  background: 'white',
  borderRadius: '12px',
  border: '1px solid #e5e7eb',
  padding: '16px',
  height: '82vh',
  display: 'flex',
  flexDirection: 'column',
};

const DiffModal = ({ open, title, loading, diffOnly, oldText, newText, onClose, onToggleDiffOnly }) => {
  if (!open) return null;

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={cardStyle} onClick={(event) => event.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
          <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>{title || '文件差异对比'}</div>
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
            <input type="checkbox" checked={diffOnly} onChange={(event) => onToggleDiffOnly(event.target.checked)} />
            仅显示差异
          </label>
          <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>绿色=新增，红色=删除，黄色=修改</div>
        </div>

        <div style={{ marginTop: '10px', flex: 1, overflow: 'auto', border: '1px solid #e5e7eb', borderRadius: '10px' }}>
          {loading ? (
            <div style={{ padding: '24px', color: '#6b7280' }}>加载对比中...</div>
          ) : (
            <div style={{ padding: '12px' }}>
              <ReactDiffViewer
                oldValue={oldText || ''}
                newValue={newText || ''}
                splitView={true}
                showDiffOnly={diffOnly}
                disableWordDiff={false}
                compareMethod="diffLines"
                leftTitle="旧版本"
                rightTitle="新版本"
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
};

export default DiffModal;
