import React from 'react';

export default function ChatConfigCreateDialog({
  open,
  onClose,
  isMobile,
  createName,
  onCreateNameChange,
  createError,
  onCreate,
  isAdmin,
  busy,
}) {
  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      data-testid="chat-config-create-dialog"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose && onClose();
      }}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(17, 24, 39, 0.55)',
        display: 'flex',
        alignItems: isMobile ? 'stretch' : 'center',
        justifyContent: 'center',
        padding: isMobile ? '12px' : '20px',
        zIndex: 1000,
      }}
    >
      <div
        style={{
          width: 'min(980px, 96vw)',
          maxHeight: isMobile ? '100%' : '90vh',
          background: 'white',
          borderRadius: '14px',
          border: '1px solid #e5e7eb',
          overflow: 'hidden',
          boxShadow: '0 20px 50px rgba(0,0,0,0.35)',
          display: 'flex',
          flexDirection: 'column',
          margin: isMobile ? 'auto 0' : 0,
        }}
      >
        <div
          style={{
            padding: '14px 16px',
            borderBottom: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: isMobile ? 'stretch' : 'center',
            flexDirection: isMobile ? 'column' : 'row',
            gap: '10px',
          }}
        >
          <div style={{ fontWeight: 950, color: '#111827' }}>新建对话</div>
          <button
            type="button"
            onClick={onClose}
            data-testid="chat-config-create-close"
            style={{
              border: '1px solid #e5e7eb',
              background: '#ffffff',
              borderRadius: '10px',
              padding: '8px 10px',
              cursor: 'pointer',
              fontWeight: 900,
              alignSelf: isMobile ? 'flex-end' : 'auto',
            }}
          >
            关闭
          </button>
        </div>

        <div style={{ padding: '14px 16px', overflowY: 'auto' }}>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: isMobile ? '1fr' : '160px 1fr',
              gap: '10px',
              alignItems: 'center',
            }}
          >
            <div style={{ fontWeight: 900, color: '#111827' }}>名称</div>
            <input
              value={createName}
              onChange={(event) => onCreateNameChange && onCreateNameChange(event.target.value)}
              placeholder="输入新对话名称"
              data-testid="chat-config-create-name"
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '10px',
                border: '1px solid #e5e7eb',
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ marginTop: '10px', color: '#6b7280', fontSize: '13px' }}>
            新对话将以空白配置直接创建，不会默认复制旧对话的知识库或已解析文档绑定。
          </div>

          {createError ? (
            <div data-testid="chat-config-create-error" style={{ marginTop: '10px', color: '#b91c1c' }}>
              {createError}
            </div>
          ) : null}
        </div>

        <div
          style={{
            padding: '14px 16px',
            borderTop: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '10px',
            flexDirection: isMobile ? 'column' : 'row',
          }}
        >
          <button
            type="button"
            onClick={onClose}
            data-testid="chat-config-create-cancel"
            style={{
              padding: '10px 14px',
              borderRadius: '12px',
              border: '1px solid #e5e7eb',
              background: '#ffffff',
              cursor: 'pointer',
              fontWeight: 900,
              width: isMobile ? '100%' : 'auto',
            }}
          >
            取消
          </button>
          <button
            type="button"
            onClick={onCreate}
            disabled={!isAdmin || busy}
            data-testid="chat-config-create-confirm"
            style={{
              padding: '10px 14px',
              borderRadius: '12px',
              border: '1px solid #1d4ed8',
              background: busy ? '#93c5fd' : '#2563eb',
              color: '#ffffff',
              cursor: busy ? 'not-allowed' : 'pointer',
              fontWeight: 950,
              width: isMobile ? '100%' : 'auto',
            }}
          >
            创建
          </button>
        </div>
      </div>
    </div>
  );
}
