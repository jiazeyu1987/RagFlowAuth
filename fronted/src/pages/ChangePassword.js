import React, { useState } from 'react';
import authClient from '../api/authClient';
import { useAuth } from '../hooks/useAuth';
import { normalizeDisplayError } from '../shared/utils/displayError';

const ChangePassword = () => {
  const { user } = useAuth();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

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
      setError(normalizeDisplayError(err?.message ?? err, '修改密码失败'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="admin-med-page" style={{ maxWidth: 620 }}>
      <section className="medui-surface medui-card-pad">
        <h2 className="admin-med-title" style={{ margin: 0 }}>修改密码</h2>
        <div className="admin-med-inline-note" style={{ marginTop: 6 }}>当前用户：{user?.username || '-'}</div>
      </section>

      <section className="medui-surface medui-card-pad">
        <form onSubmit={handleSubmit} className="admin-med-grid" style={{ gap: 12 }}>
          <label>
            <div className="admin-med-small" style={{ marginBottom: 6, fontWeight: 700 }}>旧密码</div>
            <input
              type="password"
              value={oldPassword}
              autoComplete="current-password"
              onChange={(e) => setOldPassword(e.target.value)}
              data-testid="change-password-old"
              className="medui-input"
            />
          </label>

          <label>
            <div className="admin-med-small" style={{ marginBottom: 6, fontWeight: 700 }}>新密码</div>
            <input
              type="password"
              value={newPassword}
              autoComplete="new-password"
              onChange={(e) => setNewPassword(e.target.value)}
              data-testid="change-password-new"
              className="medui-input"
            />
          </label>

          <label>
            <div className="admin-med-small" style={{ marginBottom: 6, fontWeight: 700 }}>确认新密码</div>
            <input
              type="password"
              value={confirmPassword}
              autoComplete="new-password"
              onChange={(e) => setConfirmPassword(e.target.value)}
              data-testid="change-password-confirm"
              className="medui-input"
            />
          </label>

          {error ? <div data-testid="change-password-error" className="admin-med-danger">{error}</div> : null}
          {message ? <div data-testid="change-password-success" className="admin-med-success">{message}</div> : null}

          <div className="admin-med-actions">
            <button type="submit" disabled={submitting} data-testid="change-password-submit" className="medui-btn medui-btn--primary">
              {submitting ? '提交中...' : '确认修改'}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
};

export default ChangePassword;
