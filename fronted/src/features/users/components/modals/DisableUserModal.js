import React, { useEffect, useState } from 'react';

const MOBILE_BREAKPOINT = 768;

export default function DisableUserModal({
  open,
  user,
  mode,
  untilDate,
  error,
  submitting,
  onChangeMode,
  onChangeUntilDate,
  onCancel,
  onConfirm,
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
    <div
      data-testid="users-disable-modal"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: isMobile ? 'stretch' : 'center',
        padding: isMobile ? '16px 12px' : '24px',
        zIndex: 1000,
      }}
    >
      <div
        style={{
          backgroundColor: 'white',
          padding: isMobile ? '20px 16px' : '28px',
          borderRadius: '8px',
          width: '100%',
          maxWidth: '520px',
          maxHeight: isMobile ? '100%' : '90vh',
          overflowY: 'auto',
          margin: isMobile ? 'auto 0' : 0,
        }}
      >
        <h3 style={{ margin: '0 0 8px 0' }}>禁用账户 - {user.full_name || user.username}</h3>
        <div style={{ marginBottom: 16, color: '#6b7280', fontSize: '0.9rem' }}>
          请选择禁用方式：立即禁用，或禁用到指定日期。
        </div>

        <div style={{ marginBottom: 16, padding: 12, border: '1px solid #e5e7eb', borderRadius: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: mode === 'until' ? 10 : 0 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
              <input
                type="radio"
                name="users-disable-mode"
                value="immediate"
                data-testid="users-disable-mode-immediate"
                checked={mode !== 'until'}
                onChange={() => onChangeMode('immediate')}
              />
              立即禁用
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
              <input
                type="radio"
                name="users-disable-mode"
                value="until"
                data-testid="users-disable-mode-until"
                checked={mode === 'until'}
                onChange={() => onChangeMode('until')}
              />
              到期禁用
            </label>
          </div>

          {mode === 'until' ? (
            <input
              type="date"
              data-testid="users-disable-until-date"
              value={untilDate || ''}
              onChange={(e) => onChangeUntilDate(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 12px',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                boxSizing: 'border-box',
              }}
            />
          ) : null}
        </div>

        {error ? (
          <div style={{ marginBottom: 16, color: '#ef4444' }} data-testid="users-disable-error">
            {error}
          </div>
        ) : null}

        <div style={{ display: 'flex', gap: 12, flexDirection: isMobile ? 'column' : 'row' }}>
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            data-testid="users-disable-cancel"
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: '#6b7280',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: submitting ? 'not-allowed' : 'pointer',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            取消
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={submitting}
            data-testid="users-disable-confirm"
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: submitting ? '#fbbf24' : '#f59e0b',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: submitting ? 'not-allowed' : 'pointer',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            {submitting ? '提交中...' : '确认禁用'}
          </button>
        </div>
      </div>
    </div>
  );
}
