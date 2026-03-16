import React from 'react';

export default function RenameSessionDialog({ open, value, onChangeValue, onCancel, onConfirm }) {
  if (!open) return null;

  return (
    <div data-testid="chat-rename-modal" className="medui-modal-backdrop">
      <div className="medui-modal" style={{ maxWidth: 440 }}>
        <div className="medui-modal__head">
          <div className="medui-modal__title">重命名会话</div>
        </div>
        <div className="medui-modal__body">
          <input
            value={value}
            onChange={(event) => onChangeValue(event.target.value)}
            data-testid="chat-rename-input"
            placeholder="请输入会话名称"
            className="medui-input"
          />
        </div>
        <div className="medui-modal__foot">
          <button onClick={onCancel} data-testid="chat-rename-cancel" type="button" className="medui-btn medui-btn--neutral">
            取消
          </button>
          <button
            onClick={onConfirm}
            data-testid="chat-rename-confirm"
            disabled={!String(value || '').trim()}
            type="button"
            className="medui-btn medui-btn--primary"
          >
            确定
          </button>
        </div>
      </div>
    </div>
  );
}
