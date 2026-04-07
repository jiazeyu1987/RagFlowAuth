import React from 'react';

export default function SessionLimitFields({
  inputStyle,
  maxSessionsLabel,
  maxSessionsValue,
  maxSessionsRequired = false,
  maxSessionsTestId,
  onChangeMaxSessions,
  idleTimeoutLabel,
  idleTimeoutValue,
  idleTimeoutRequired = false,
  idleTimeoutTestId,
  onChangeIdleTimeout,
}) {
  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{maxSessionsLabel}</label>
        <input
          type="number"
          min={1}
          max={1000}
          required={maxSessionsRequired}
          value={maxSessionsValue}
          onChange={onChangeMaxSessions}
          data-testid={maxSessionsTestId}
          style={inputStyle}
        />
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{idleTimeoutLabel}</label>
        <input
          type="number"
          min={1}
          max={43200}
          required={idleTimeoutRequired}
          value={idleTimeoutValue}
          onChange={onChangeIdleTimeout}
          data-testid={idleTimeoutTestId}
          style={inputStyle}
        />
      </div>
    </>
  );
}
