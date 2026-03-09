import React from 'react';

export default function DeleteSessionDialog({ open, sessionName, onCancel, onConfirm }) {
  if (!open) return null;

  return (
    <div
      data-testid="chat-delete-modal"
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
        <h3 style={{ margin: '0 0 12px 0' }}>确认删除会话</h3>
        <div style={{ color: '#374151', marginBottom: '16px' }}>
          确定要删除会话“<strong>{sessionName}</strong>”吗？
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={onCancel}
            data-testid="chat-delete-cancel"
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
            data-testid="chat-delete-confirm"
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: '#ef4444',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
            }}
          >
            确认删除
          </button>
        </div>
      </div>
    </div>
  );
}
