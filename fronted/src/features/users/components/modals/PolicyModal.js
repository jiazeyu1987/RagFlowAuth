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
    <div
      data-testid="users-policy-modal"
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
          {'登录策略 - '} {user.username}
        </h3>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 8, fontWeight: '500' }}>{'最大登录会话数 (1-1000)'}</label>
          <input
            type="number"
            min={1}
            max={1000}
            value={policyForm.max_login_sessions}
            onChange={(e) =>
              onChangePolicyForm({
                ...policyForm,
                max_login_sessions: e.target.value,
              })
            }
            data-testid="users-policy-max-login-sessions"
            style={{
              width: '100%',
              padding: '10px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
            }}
          />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 8, fontWeight: '500' }}>{'闲置超时 (分钟, 1-43200)'}</label>
          <input
            type="number"
            min={1}
            max={43200}
            value={policyForm.idle_timeout_minutes}
            onChange={(e) =>
              onChangePolicyForm({
                ...policyForm,
                idle_timeout_minutes: e.target.value,
              })
            }
            data-testid="users-policy-idle-timeout"
            style={{
              width: '100%',
              padding: '10px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
            }}
          />
        </div>

        {policyError && (
          <div style={{ marginBottom: 16, color: '#ef4444' }} data-testid="users-policy-error">
            {policyError}
          </div>
        )}

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            type="button"
            onClick={onCancel}
            disabled={policySubmitting}
            data-testid="users-policy-cancel"
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: '#6b7280',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: policySubmitting ? 'not-allowed' : 'pointer',
            }}
          >
            {'取消'}
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={policySubmitting}
            data-testid="users-policy-save"
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: policySubmitting ? '#7dd3fc' : '#0ea5e9',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: policySubmitting ? 'not-allowed' : 'pointer',
            }}
          >
            {policySubmitting ? '提交中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
