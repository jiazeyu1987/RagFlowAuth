import React from 'react';
import DisableAccountSection from './DisableAccountSection';
import ModalActionRow from './ModalActionRow';
import UserModalFrame from './UserModalFrame';

const TEXT = {
  title: '\u7981\u7528\u8d26\u6237',
  description: '\u8bf7\u9009\u62e9\u7981\u7528\u65b9\u5f0f\uff1a\u7acb\u5373\u7981\u7528\uff0c\u6216\u7981\u7528\u5230\u6307\u5b9a\u65e5\u671f\u3002',
  cancel: '\u53d6\u6d88',
  confirm: '\u786e\u8ba4\u7981\u7528',
  submitting: '\u63d0\u4ea4\u4e2d...',
};

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
  return (
    <UserModalFrame
      open={Boolean(open && user)}
      testId="users-disable-modal"
      title={`${TEXT.title} - ${user?.full_name || user?.username || ''}`}
      titleMarginBottom="8px"
      maxWidth="520px"
      desktopPadding="28px"
    >
      {({ isMobile }) => (
        <>
          <div style={{ marginBottom: 16, color: '#6b7280', fontSize: '0.9rem' }}>{TEXT.description}</div>

          <DisableAccountSection
            enabled
            mode={mode}
            untilDate={untilDate}
            onChangeMode={onChangeMode}
            onChangeUntilDate={onChangeUntilDate}
            radioName="users-disable-mode"
            immediateTestId="users-disable-mode-immediate"
            untilTestId="users-disable-mode-until"
            dateTestId="users-disable-until-date"
            inputStyle={{
              width: '100%',
              padding: '10px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              boxSizing: 'border-box',
            }}
          />

          {error ? (
            <div style={{ marginBottom: 16, color: '#ef4444' }} data-testid="users-disable-error">
              {error}
            </div>
          ) : null}

          <ModalActionRow
            isMobile={isMobile}
            actions={[
              {
                onClick: onCancel,
                disabled: submitting,
                testId: 'users-disable-cancel',
                label: TEXT.cancel,
                backgroundColor: '#6b7280',
              },
              {
                onClick: onConfirm,
                disabled: submitting,
                testId: 'users-disable-confirm',
                label: submitting ? TEXT.submitting : TEXT.confirm,
                backgroundColor: '#f59e0b',
                disabledBackgroundColor: '#fbbf24',
              },
            ]}
          />
        </>
      )}
    </UserModalFrame>
  );
}
