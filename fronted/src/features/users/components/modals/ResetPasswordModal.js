import React from 'react';
import ModalActionRow from './ModalActionRow';
import UserModalFrame from './UserModalFrame';

const TEXT = {
  title: '\u4fee\u6539\u5bc6\u7801',
  newPassword: '\u65b0\u5bc6\u7801',
  confirmPassword: '\u786e\u8ba4\u65b0\u5bc6\u7801',
  cancel: '\u53d6\u6d88',
  save: '\u4fdd\u5b58',
  submitting: '\u63d0\u4ea4\u4e2d...',
};

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
  return (
    <UserModalFrame
      open={Boolean(open && user)}
      testId="users-reset-password-modal"
      title={`${TEXT.title} - ${user?.full_name || user?.username || ''}`}
      maxWidth="500px"
    >
      {({ isMobile }) => (
        <>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: '500' }}>{TEXT.newPassword}</label>
            <input
              type="password"
              value={value}
              autoComplete="new-password"
              onChange={(event) => onChangeValue(event.target.value)}
              data-testid="users-reset-password-new"
              style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '4px', boxSizing: 'border-box' }}
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: '500' }}>{TEXT.confirmPassword}</label>
            <input
              type="password"
              value={confirm}
              autoComplete="new-password"
              onChange={(event) => onChangeConfirm(event.target.value)}
              data-testid="users-reset-password-confirm"
              style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '4px', boxSizing: 'border-box' }}
            />
          </div>

          {error ? (
            <div style={{ marginBottom: 16, color: '#ef4444' }} data-testid="users-reset-password-error">
              {error}
            </div>
          ) : null}

          <ModalActionRow
            isMobile={isMobile}
            actions={[
              {
                onClick: onCancel,
                disabled: submitting,
                testId: 'users-reset-password-cancel',
                label: TEXT.cancel,
                backgroundColor: '#6b7280',
              },
              {
                onClick: onSubmit,
                disabled: submitting,
                testId: 'users-reset-password-save',
                label: submitting ? TEXT.submitting : TEXT.save,
                backgroundColor: '#3b82f6',
                disabledBackgroundColor: '#93c5fd',
              },
            ]}
          />
        </>
      )}
    </UserModalFrame>
  );
}
