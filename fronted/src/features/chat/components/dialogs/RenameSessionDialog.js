import React, { useEffect, useState } from 'react';

const MOBILE_BREAKPOINT = 768;

export default function RenameSessionDialog({ open, value, onChangeValue, onCancel, onConfirm }) {
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
        padding: isMobile ? '16px' : '24px',
      }}
    >
      <div
        style={{
          backgroundColor: 'white',
          padding: isMobile ? '18px 16px' : '24px',
          borderRadius: isMobile ? '14px' : '8px',
          width: '100%',
          maxWidth: '420px',
        }}
      >
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
              borderRadius: '10px',
              border: '1px solid #d1d5db',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>
        <div style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', gap: '10px' }}>
          <button
            onClick={onCancel}
            data-testid="chat-rename-cancel"
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: '#6b7280',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
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
              borderRadius: '10px',
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