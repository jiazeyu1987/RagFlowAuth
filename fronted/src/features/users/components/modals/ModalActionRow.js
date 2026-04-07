import React from 'react';

export default function ModalActionRow({
  isMobile,
  actions,
  gap = 12,
}) {
  const items = Array.isArray(actions) ? actions : [];

  return (
    <div style={{ display: 'flex', gap, flexDirection: isMobile ? 'column' : 'row' }}>
      {items.map((action) => {
        const disabled = !!action.disabled;
        return (
          <button
            key={action.testId || action.label}
            type={action.type || 'button'}
            onClick={action.onClick}
            disabled={disabled}
            data-testid={action.testId}
            style={{
              flex: 1,
              padding: '10px',
              backgroundColor: disabled
                ? action.disabledBackgroundColor || action.backgroundColor
                : action.backgroundColor,
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: disabled ? 'not-allowed' : 'pointer',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            {action.label}
          </button>
        );
      })}
    </div>
  );
}
