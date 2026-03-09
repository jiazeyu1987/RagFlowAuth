import React from 'react';

export default function RenameSessionDialog({ open, value, onChangeValue, onCancel, onConfirm }) {
  if (!open) return null;

  return (
    <div
      data-testid="chat-rename-modal"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 1000,
      }}
    >
      <div style={{ backgroundColor: 'white', padding: '24px', borderRadius: '8px', width: '100%', maxWidth: '420px' }}>
        <h3 style={{ margin: '0 0 12px 0' }}>重命名会话</h3>
        <div style={{ marginBottom: '12px' }}>
          <input
            value={value}
            onChange={(e) => onChangeValue(e.target.value)}
            data-testid="chat-rename-input"
            placeholder="请输入会话名称"
            style={{
              width: '100%',
              padding: '10px 12px',
              borderRadius: '6px',
              border: '1px solid #d1d5db',
              outline: 'none',
            }}
          />
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={onCancel}
            data-testid="chat-rename-cancel"
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: '#6b7280',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
            }}
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            data-testid="chat-rename-confirm"
            disabled={!String(value || '').trim()}
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: !String(value || '').trim() ? '#9ca3af' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: !String(value || '').trim() ? 'not-allowed' : 'pointer',
            }}
          >
            确定
          </button>
        </div>
      </div>
    </div>
  );
}
