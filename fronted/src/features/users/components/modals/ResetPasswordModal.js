import React, { useEffect, useState } from 'react';

const MOBILE_BREAKPOINT = 768;

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

  if (!open || !user) return null;

  return (
    <div data-testid="users-reset-password-modal" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.5)', display: 'flex', justifyContent: 'center', alignItems: isMobile ? 'stretch' : 'center', padding: isMobile ? '16px 12px' : '24px', zIndex: 1000 }}>
      <div style={{ backgroundColor: 'white', padding: isMobile ? '20px 16px' : '32px', borderRadius: '8px', width: '100%', maxWidth: '500px', maxHeight: isMobile ? '100%' : '90vh', overflowY: 'auto', margin: isMobile ? 'auto 0' : 0 }}>
        <h3 style={{ margin: '0 0 24px 0' }}>修改密码 - {user.full_name || user.username}</h3>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 8, fontWeight: '500' }}>新密码</label>
          <input type="password" value={value} autoComplete="new-password" onChange={(e) => onChangeValue(e.target.value)} data-testid="users-reset-password-new" style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '4px', boxSizing: 'border-box' }} />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 8, fontWeight: '500' }}>确认新密码</label>
          <input type="password" value={confirm} autoComplete="new-password" onChange={(e) => onChangeConfirm(e.target.value)} data-testid="users-reset-password-confirm" style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '4px', boxSizing: 'border-box' }} />
        </div>

        {error ? <div style={{ marginBottom: 16, color: '#ef4444' }} data-testid="users-reset-password-error">{error}</div> : null}

        <div style={{ display: 'flex', gap: '12px', flexDirection: isMobile ? 'column' : 'row' }}>
          <button type="button" onClick={onCancel} disabled={submitting} data-testid="users-reset-password-cancel" style={{ flex: 1, padding: '10px', backgroundColor: '#6b7280', color: 'white', border: 'none', borderRadius: '4px', cursor: submitting ? 'not-allowed' : 'pointer', width: isMobile ? '100%' : 'auto' }}>取消</button>
          <button type="button" onClick={onSubmit} disabled={submitting} data-testid="users-reset-password-save" style={{ flex: 1, padding: '10px', backgroundColor: submitting ? '#93c5fd' : '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: submitting ? 'not-allowed' : 'pointer', width: isMobile ? '100%' : 'auto' }}>{submitting ? '提交中...' : '保存'}</button>
        </div>
      </div>
    </div>
  );
}
