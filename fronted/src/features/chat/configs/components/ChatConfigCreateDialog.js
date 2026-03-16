import React from 'react';

export default function ChatConfigCreateDialog({
  open,
  onClose,
  createName,
  onCreateNameChange,
  createFromId,
  onCreateFromIdChange,
  chatList,
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
      className="admin-med-dialog"
    >
      <div className="admin-med-dialog__panel">
        <div className="admin-med-dialog__head">
          <div style={{ fontWeight: 700, color: '#163f63' }}>新建对话</div>
          <button type="button" onClick={onClose} data-testid="chat-config-create-close" className="medui-btn medui-btn--secondary">
            关闭
          </button>
        </div>

        <div className="admin-med-dialog__body">
          <div className="admin-med-form-grid admin-med-form-grid--2">
            <div style={{ fontWeight: 700, color: '#17324d' }}>对话名称</div>
            <input
              value={createName}
              onChange={(event) => onCreateNameChange && onCreateNameChange(event.target.value)}
              placeholder="请输入新对话名称"
              data-testid="chat-config-create-name"
              className="medui-input"
            />
          </div>

          <div className="admin-med-form-grid admin-med-form-grid--2">
            <div style={{ fontWeight: 700, color: '#17324d' }}>复制来源</div>
            <select
              value={createFromId}
              onChange={(event) => onCreateFromIdChange && onCreateFromIdChange(event.target.value)}
              data-testid="chat-config-create-from"
              className="medui-select"
              disabled={!chatList.length}
            >
              {chatList.map((chat) => (
                <option key={String(chat?.id || '')} value={String(chat?.id || '')}>
                  {String(chat?.name || chat?.id || '')}
                </option>
              ))}
            </select>
          </div>

          {!chatList.length ? <div className="admin-med-inline-note">暂无可复制来源对话</div> : null}
          {createError ? <div data-testid="chat-config-create-error" className="admin-med-danger">{createError}</div> : null}
        </div>

        <div className="admin-med-dialog__foot">
          <button type="button" onClick={onClose} data-testid="chat-config-create-cancel" className="medui-btn medui-btn--neutral">
            取消
          </button>
          <button type="button" onClick={onCreate} disabled={!isAdmin || busy} data-testid="chat-config-create-confirm" className="medui-btn medui-btn--primary">
            {busy ? '创建中...' : '创建'}
          </button>
        </div>
      </div>
    </div>
  );
}
