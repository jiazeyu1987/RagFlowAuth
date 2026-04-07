import React from 'react';

const TEXT = {
  disableAccount: '\u505c\u7528\u6b64\u8d26\u53f7',
  disableImmediate: '\u7acb\u5373',
  disableUntil: '\u5230\u671f\u65e5',
};

export default function DisableAccountSection({
  enabled = true,
  mode,
  untilDate,
  onChangeMode,
  onChangeUntilDate,
  showEnabledToggle = false,
  onToggleEnabled,
  radioName,
  enabledTestId,
  immediateTestId,
  untilTestId,
  dateTestId,
  inputStyle,
  marginBottom = 16,
}) {
  return (
    <div style={{ marginBottom, padding: 12, border: '1px solid #e5e7eb', borderRadius: 8 }}>
      {showEnabledToggle ? (
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginBottom: enabled ? 10 : 0 }}>
          <input
            type="checkbox"
            data-testid={enabledTestId}
            checked={!!enabled}
            onChange={(event) => onToggleEnabled?.(event.target.checked)}
          />
          {TEXT.disableAccount}
        </label>
      ) : null}

      {enabled ? (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: mode === 'until' ? 10 : 0 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
              <input
                type="radio"
                name={radioName}
                value="immediate"
                data-testid={immediateTestId}
                checked={mode !== 'until'}
                onChange={() => onChangeMode?.('immediate')}
              />
              {TEXT.disableImmediate}
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
              <input
                type="radio"
                name={radioName}
                value="until"
                data-testid={untilTestId}
                checked={mode === 'until'}
                onChange={() => onChangeMode?.('until')}
              />
              {TEXT.disableUntil}
            </label>
          </div>

          {mode === 'until' ? (
            <input
              type="date"
              data-testid={dateTestId}
              value={untilDate || ''}
              onChange={(event) => onChangeUntilDate?.(event.target.value)}
              style={inputStyle}
            />
          ) : null}
        </>
      ) : null}
    </div>
  );
}
