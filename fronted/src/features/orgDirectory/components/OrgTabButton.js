import React from 'react';

export default function OrgTabButton({ active, children, dataTestId, onClick }) {
  return (
    <button
      type="button"
      data-testid={dataTestId}
      onClick={onClick}
      style={{
        padding: '10px 12px',
        borderRadius: 10,
        border: `1px solid ${active ? '#93c5fd' : '#d1d5db'}`,
        backgroundColor: active ? '#eff6ff' : '#ffffff',
        color: active ? '#1d4ed8' : '#374151',
        fontWeight: 700,
        cursor: 'pointer',
        width: '100%',
      }}
    >
      {children}
    </button>
  );
}
