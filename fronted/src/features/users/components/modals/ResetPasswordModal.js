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
    <div
      data-testid="users-reset-password-modal"
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
      <div
        style={{
          backgroundColor: 'white',
          padding: '32px',
          borderRadius: '8px',
          width: '100%',
          maxWidth: '500px',
        }}
      >
        <h3 style={{ margin: '0 0 24px 0' }}>
          {'修改密码 - '} {user.username}
        </h3>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 8, fontWeight: '500' }}>{'新密码'}</label>
          <input
            type="password"
            value={value}
            autoComplete="new-password"
            onChange={(e) => onChangeValue(e.target.value)}
            data-testid="users-reset-password-new"
            style={{
              width: '100%',
              padding: '10px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
            }}
          />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 8, fontWeight: '500' }}>{'确认新密码'}</label>
          <input
            type="password"
            value={confirm}
            autoComplete="new-password"
            onChange={(e) => onChangeConfirm(e.target.value)}
            data-testid="users-reset-password-confirm"
            style={{
              width: '100%',
              padding: '10px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
            }}
          />
        </div>

        {error && (
          <div style={{ marginBottom: 16, color: '#ef4444' }} data-testid="users-reset-password-error">
            {error}
          </div>
        )}

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            data-testid="users-reset-password-cancel"
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: '#6b7280',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: submitting ? 'not-allowed' : 'pointer',
            }}
          >
            {'取消'}
          </button>
          <button
            type="button"
            onClick={onSubmit}
            disabled={submitting}
            data-testid="users-reset-password-save"
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: submitting ? '#93c5fd' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: submitting ? 'not-allowed' : 'pointer',
            }}
          >
            {submitting ? '提交中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
