import React from 'react';
import useChangePasswordPage from '../features/me/useChangePasswordPage';

const ChangePassword = () => {
  const {
    user,
    isMobile,
    oldPassword,
    newPassword,
    confirmPassword,
    submitting,
    error,
    message,
    passwordPolicyChecks,
    setOldPassword,
    setNewPassword,
    setConfirmPassword,
    handleSubmit,
  } = useChangePasswordPage();

  const inputStyle = {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #d1d5db',
    borderRadius: 6,
    boxSizing: 'border-box',
  };
  const hiddenUsernameStyle = {
    position: 'absolute',
    width: 1,
    height: 1,
    padding: 0,
    margin: -1,
    overflow: 'hidden',
    clip: 'rect(0, 0, 0, 0)',
    whiteSpace: 'nowrap',
    border: 0,
  };

  return (
    <div style={{ maxWidth: 520, width: '100%' }}>
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: 8,
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          padding: isMobile ? 14 : 16,
        }}
      >
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            value={user?.username || ''}
            autoComplete="username"
            readOnly
            tabIndex={-1}
            aria-hidden="true"
            style={hiddenUsernameStyle}
          />
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 6 }}>旧密码</label>
            <input
              type="password"
              value={oldPassword}
              autoComplete="current-password"
              onChange={(event) => setOldPassword(event.target.value)}
              data-testid="change-password-old"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 6 }}>新密码</label>
            <input
              type="password"
              value={newPassword}
              autoComplete="new-password"
              onChange={(event) => setNewPassword(event.target.value)}
              data-testid="change-password-new"
              style={inputStyle}
            />
          </div>

          <div
            data-testid="change-password-policy"
            style={{
              marginBottom: 12,
              border: '1px solid #e5e7eb',
              borderRadius: 6,
              padding: '10px 12px',
              backgroundColor: '#f9fafb',
            }}
          >
            <div style={{ marginBottom: 8, fontWeight: 600, color: '#374151' }}>密码安全策略</div>
            {passwordPolicyChecks.map((item) => (
              <div
                key={item.key}
                data-testid={`change-password-policy-${item.key}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  marginBottom: 4,
                  color: item.passed ? '#16a34a' : '#dc2626',
                  fontSize: '0.9rem',
                }}
              >
                <span style={{ fontWeight: 700 }}>{item.passed ? '✓' : '✕'}</span>
                <span>{item.label}</span>
              </div>
            ))}
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 6 }}>确认新密码</label>
            <input
              type="password"
              value={confirmPassword}
              autoComplete="new-password"
              onChange={(event) => setConfirmPassword(event.target.value)}
              data-testid="change-password-confirm"
              style={inputStyle}
            />
          </div>

          {error ? (
            <div style={{ marginBottom: 12, color: '#ef4444' }} data-testid="change-password-error">
              {error}
            </div>
          ) : null}
          {message ? (
            <div style={{ marginBottom: 12, color: '#10b981' }} data-testid="change-password-success">
              {message}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={submitting}
            data-testid="change-password-submit"
            style={{
              width: '100%',
              padding: '10px 14px',
              backgroundColor: submitting ? '#93c5fd' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: 6,
              cursor: submitting ? 'not-allowed' : 'pointer',
            }}
          >
            {submitting ? '提交中...' : '修改密码'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChangePassword;
