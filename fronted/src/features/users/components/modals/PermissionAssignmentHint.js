import React from 'react';

export default function PermissionAssignmentHint({
  label,
  text,
  marginBottom = 16,
  panelBorderRadius = '8px',
  panelPadding = '12px',
  fontSize = '0.9rem',
  testId,
}) {
  return (
    <div style={{ marginBottom }}>
      <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{label}</label>
      <div
        data-testid={testId}
        style={{
          border: '1px solid #d1d5db',
          borderRadius: panelBorderRadius,
          padding: panelPadding,
          backgroundColor: '#f9fafb',
          color: '#6b7280',
          fontSize,
        }}
      >
        {text}
      </div>
    </div>
  );
}
