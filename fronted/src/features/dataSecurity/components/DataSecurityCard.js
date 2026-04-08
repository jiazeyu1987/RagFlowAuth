import React from 'react';

export default function DataSecurityCard({ title, children }) {
  return (
    <div
      style={{
        marginTop: '16px',
        background: 'white',
        borderRadius: '12px',
        padding: '16px',
        border: '1px solid #e5e7eb',
      }}
    >
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      {children}
    </div>
  );
}
