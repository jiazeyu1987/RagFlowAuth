import React from 'react';

export default function PolicyModal({
  open,
  user,
  policyForm,
  policyError,
  policySubmitting,
  onChangePolicyForm,
  onCancel,
  onSave,
}) {
  if (!open || !user) return null;

  return (
    <div data-testid="users-policy-modal" className="medui-modal-backdrop">
      <div className="medui-modal users-med-modal">
        <div className="medui-modal__head">
          <div className="medui-modal__title">{`登录策略 - ${user.username}`}</div>
        </div>
        <div className="medui-modal__body">
          <div className="users-med-field" style={{ marginBottom: 12 }}>
            <label>最大登录会话数（1-1000）</label>
            <input type="number" min={1} max={1000} value={policyForm.max_login_sessions} onChange={(e) => onChangePolicyForm({ ...policyForm, max_login_sessions: e.target.value })} data-testid="users-policy-max-login-sessions" className="medui-input" />
          </div>
          <div className="users-med-field">
            <label>空闲超时（分钟，1-43200）</label>
            <input type="number" min={1} max={43200} value={policyForm.idle_timeout_minutes} onChange={(e) => onChangePolicyForm({ ...policyForm, idle_timeout_minutes: e.target.value })} data-testid="users-policy-idle-timeout" className="medui-input" />
          </div>
          {policyError && <div style={{ marginTop: 12, color: '#b23f3f' }} data-testid="users-policy-error">{policyError}</div>}
        </div>
        <div className="medui-modal__foot">
          <button type="button" onClick={onCancel} disabled={policySubmitting} data-testid="users-policy-cancel" className="medui-btn medui-btn--neutral">取消</button>
          <button type="button" onClick={onSave} disabled={policySubmitting} data-testid="users-policy-save" className="medui-btn medui-btn--primary">{policySubmitting ? '提交中...' : '保存'}</button>
        </div>
      </div>
    </div>
  );
}
