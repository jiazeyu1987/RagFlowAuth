import React from 'react';

export default function UserTypeField({
  label,
  inputStyle,
  value,
  onChange,
  testId,
  normalLabel,
  subAdminLabel,
  readonly = false,
  readonlyLabel = '',
  readonlyTestId,
  marginBottom = 16,
}) {
  return (
    <div style={{ marginBottom }}>
      <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{label}</label>
      {readonly ? (
        <div
          data-testid={readonlyTestId}
          style={{
            ...inputStyle,
            color: '#6b7280',
            backgroundColor: '#f9fafb',
          }}
        >
          {readonlyLabel}
        </div>
      ) : (
        <select value={value || 'normal'} onChange={onChange} data-testid={testId} style={inputStyle}>
          <option value="normal">{normalLabel}</option>
          <option value="sub_admin">{subAdminLabel}</option>
        </select>
      )}
    </div>
  );
}
