import React, { useEffect, useState } from 'react';

const MOBILE_BREAKPOINT = 768;

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
    <div data-testid="users-policy-modal" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.5)', display: 'flex', justifyContent: 'center', alignItems: isMobile ? 'stretch' : 'center', padding: isMobile ? '16px 12px' : '24px', zIndex: 1000 }}>
      <div style={{ backgroundColor: 'white', padding: isMobile ? '20px 16px' : '32px', borderRadius: '8px', width: '100%', maxWidth: '500px', maxHeight: isMobile ? '100%' : '90vh', overflowY: 'auto', margin: isMobile ? 'auto 0' : 0 }}>
        <h3 style={{ margin: '0 0 24px 0' }}>登录策略 - {user.username}</h3>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 8, fontWeight: '500' }}>最大登录会话数 (1-1000)</label>
          <input type="number" min={1} max={1000} value={policyForm.max_login_sessions} onChange={(e) => onChangePolicyForm({ ...policyForm, max_login_sessions: e.target.value })} data-testid="users-policy-max-login-sessions" style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '4px', boxSizing: 'border-box' }} />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 8, fontWeight: '500' }}>空闲超时 (分钟, 1-43200)</label>
          <input type="number" min={1} max={43200} value={policyForm.idle_timeout_minutes} onChange={(e) => onChangePolicyForm({ ...policyForm, idle_timeout_minutes: e.target.value })} data-testid="users-policy-idle-timeout" style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '4px', boxSizing: 'border-box' }} />
        </div>

        {policyError ? <div style={{ marginBottom: 16, color: '#ef4444' }} data-testid="users-policy-error">{policyError}</div> : null}

        <div style={{ display: 'flex', gap: '12px', flexDirection: isMobile ? 'column' : 'row' }}>
          <button type="button" onClick={onCancel} disabled={policySubmitting} data-testid="users-policy-cancel" style={{ flex: 1, padding: '10px', backgroundColor: '#6b7280', color: 'white', border: 'none', borderRadius: '4px', cursor: policySubmitting ? 'not-allowed' : 'pointer', width: isMobile ? '100%' : 'auto' }}>取消</button>
          <button type="button" onClick={onSave} disabled={policySubmitting} data-testid="users-policy-save" style={{ flex: 1, padding: '10px', backgroundColor: policySubmitting ? '#7dd3fc' : '#0ea5e9', color: 'white', border: 'none', borderRadius: '4px', cursor: policySubmitting ? 'not-allowed' : 'pointer', width: isMobile ? '100%' : 'auto' }}>{policySubmitting ? '提交中...' : '保存'}</button>
        </div>
      </div>
    </div>
  );
}
