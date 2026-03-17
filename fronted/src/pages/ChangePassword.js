import React, { useEffect, useState } from 'react';
import authClient from '../api/authClient';
import { useAuth } from '../hooks/useAuth';

const MOBILE_BREAKPOINT = 768;

const ChangePassword = () => {
  const { user } = useAuth();
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setMessage(null);

    if (!oldPassword || !newPassword) {
      setError('请输入旧密码和新密码');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('两次输入的新密码不一致');
      return;
    }

    try {
      setSubmitting(true);
      await authClient.changePassword(oldPassword, newPassword);
      setMessage('密码修改成功');
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError(err.message || '修改密码失败');
    } finally {
      setSubmitting(false);
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #d1d5db',
    borderRadius: 6,
    boxSizing: 'border-box',
  };

  return (
    <div style={{ maxWidth: 520, width: '100%' }}>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>修改密码</h2>
        <div style={{ marginTop: 6, color: '#6b7280', fontSize: '0.9rem', wordBreak: 'break-word' }}>
          当前用户：{user?.username || '-'}
        </div>
      </div>

      <div style={{ backgroundColor: 'white', borderRadius: 8, boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)', padding: isMobile ? 14 : 16 }}>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 6 }}>旧密码</label>
            <input type="password" value={oldPassword} autoComplete="current-password" onChange={(e) => setOldPassword(e.target.value)} data-testid="change-password-old" style={inputStyle} />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 6 }}>新密码</label>
            <input type="password" value={newPassword} autoComplete="new-password" onChange={(e) => setNewPassword(e.target.value)} data-testid="change-password-new" style={inputStyle} />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 6 }}>确认新密码</label>
            <input type="password" value={confirmPassword} autoComplete="new-password" onChange={(e) => setConfirmPassword(e.target.value)} data-testid="change-password-confirm" style={inputStyle} />
          </div>

          {error ? <div style={{ marginBottom: 12, color: '#ef4444' }} data-testid="change-password-error">{error}</div> : null}
          {message ? <div style={{ marginBottom: 12, color: '#10b981' }} data-testid="change-password-success">{message}</div> : null}

          <button type="submit" disabled={submitting} data-testid="change-password-submit" style={{ width: '100%', padding: '10px 14px', backgroundColor: submitting ? '#93c5fd' : '#3b82f6', color: 'white', border: 'none', borderRadius: 6, cursor: submitting ? 'not-allowed' : 'pointer' }}>
            {submitting ? '提交中...' : '修改密码'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChangePassword;
