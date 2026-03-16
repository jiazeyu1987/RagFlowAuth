import React from 'react';

export default function ResetPasswordModal({
  open,
  user,
  value,
  confirm,
  error,
  submitting,
  onChangeValue,
  onChangeConfirm,
  onCancel,
  onSubmit,
}) {
  if (!open || !user) return null;

  return (
    <div data-testid="users-reset-password-modal" className="medui-modal-backdrop">
      <div className="medui-modal users-med-modal">
        <div className="medui-modal__head">
          <div className="medui-modal__title">{`修改密码 - ${user.username}`}</div>
        </div>
        <div className="medui-modal__body">
          <div className="users-med-field" style={{ marginBottom: 12 }}>
            <label>新密码</label>
            <input type="password" value={value} autoComplete="new-password" onChange={(e) => onChangeValue(e.target.value)} data-testid="users-reset-password-new" className="medui-input" />
          </div>
          <div className="users-med-field">
            <label>确认新密码</label>
            <input type="password" value={confirm} autoComplete="new-password" onChange={(e) => onChangeConfirm(e.target.value)} data-testid="users-reset-password-confirm" className="medui-input" />
          </div>
          {error && <div style={{ marginTop: 12, color: '#b23f3f' }} data-testid="users-reset-password-error">{error}</div>}
        </div>
        <div className="medui-modal__foot">
          <button type="button" onClick={onCancel} disabled={submitting} data-testid="users-reset-password-cancel" className="medui-btn medui-btn--neutral">取消</button>
          <button type="button" onClick={onSubmit} disabled={submitting} data-testid="users-reset-password-save" className="medui-btn medui-btn--primary">{submitting ? '提交中...' : '保存'}</button>
        </div>
      </div>
    </div>
  );
}
