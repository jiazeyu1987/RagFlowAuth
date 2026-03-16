import React from 'react';

export default function DeleteSessionDialog({ open, sessionName, onCancel, onConfirm }) {
  if (!open) return null;

  return (
    <div data-testid="chat-delete-modal" className="medui-modal-backdrop">
      <div className="medui-modal" style={{ maxWidth: 440 }}>
        <div className="medui-modal__head">
          <div className="medui-modal__title">确认删除会话</div>
        </div>
        <div className="medui-modal__body">
          <div className="chat-med-dialog-sub">
            确定要删除会话“<strong>{sessionName}</strong>”吗？删除后不可恢复。
          </div>
        </div>
        <div className="medui-modal__foot">
          <button onClick={onCancel} data-testid="chat-delete-cancel" type="button" className="medui-btn medui-btn--neutral">
            取消
          </button>
          <button onClick={onConfirm} data-testid="chat-delete-confirm" type="button" className="medui-btn medui-btn--danger">
            确认删除
          </button>
        </div>
      </div>
    </div>
  );
}
