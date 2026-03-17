import React, { useEffect, useState } from 'react';

const MOBILE_BREAKPOINT = 768;

export default function DeleteSessionDialog({ open, sessionName, onCancel, onConfirm }) {
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
        <h3 style={{ margin: '0 0 12px 0' }}>确认删除会话</h3>
        <div style={{ color: '#374151', marginBottom: '16px', lineHeight: 1.6 }}>
          确定要删除会话“<strong>{sessionName}</strong>”吗？
        </div>
        <div style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', gap: '10px' }}>
          <button
            onClick={onCancel}
            data-testid="chat-delete-cancel"
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
            data-testid="chat-delete-confirm"
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: '#ef4444',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
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