import React from 'react';

export const panelStyle = {
  border: '1px solid #e5e7eb',
  borderRadius: 10,
  background: '#fff',
};

const iconButtonPalette = {
  neutral: {
    borderColor: '#d1d5db',
    background: '#ffffff',
    color: '#475569',
    shadow: 'rgba(148, 163, 184, 0.2)',
  },
  blue: {
    borderColor: '#2563eb',
    background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
    color: '#ffffff',
    shadow: 'rgba(37, 99, 235, 0.28)',
  },
  orange: {
    borderColor: '#f59e0b',
    background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
    color: '#ffffff',
    shadow: 'rgba(245, 158, 11, 0.28)',
  },
  red: {
    borderColor: '#ef4444',
    background: 'linear-gradient(135deg, #f87171 0%, #ef4444 100%)',
    color: '#ffffff',
    shadow: 'rgba(239, 68, 68, 0.28)',
  },
};

function IconBase({ children }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export function RefreshIcon() {
  return (
    <IconBase>
      <path d="M20 11a8 8 0 1 0 2 5.5" />
      <path d="M20 4v7h-7" />
    </IconBase>
  );
}

export function FolderAddIcon() {
  return (
    <IconBase>
      <path d="M3.5 7.5h6l2 2H20a1.5 1.5 0 0 1 1.5 1.5v6A2.5 2.5 0 0 1 19 19.5H5A2.5 2.5 0 0 1 2.5 17V9A1.5 1.5 0 0 1 4 7.5Z" />
      <path d="M12 11.5v5" />
      <path d="M9.5 14h5" />
    </IconBase>
  );
}

export function RenameIcon() {
  return (
    <IconBase>
      <path d="M4 20h4.5l9.8-9.8a1.9 1.9 0 0 0 0-2.7l-1.8-1.8a1.9 1.9 0 0 0-2.7 0L4 15.5V20Z" />
      <path d="m12.5 7.5 4 4" />
    </IconBase>
  );
}

export function DeleteIcon() {
  return (
    <IconBase>
      <path d="M4.5 7.5h15" />
      <path d="M9 7.5V5.8A1.8 1.8 0 0 1 10.8 4h2.4A1.8 1.8 0 0 1 15 5.8v1.7" />
      <path d="M7 7.5 8 19a2 2 0 0 0 2 1.8h4a2 2 0 0 0 2-1.8l1-11.5" />
      <path d="M10 11v5" />
      <path d="M14 11v5" />
    </IconBase>
  );
}

export function ToolbarIconButton({
  label,
  icon,
  onClick,
  disabled = false,
  tone = 'neutral',
  testId,
}) {
  const palette = iconButtonPalette[tone] || iconButtonPalette.neutral;
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      data-testid={testId}
      onClick={onClick}
      disabled={disabled}
      style={{
        width: 46,
        height: 46,
        borderRadius: 14,
        border: `1px solid ${palette.borderColor}`,
        background: disabled ? '#e5e7eb' : palette.background,
        color: disabled ? '#94a3b8' : palette.color,
        boxShadow: disabled ? 'none' : `0 8px 18px ${palette.shadow}`,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'transform 120ms ease, box-shadow 120ms ease, opacity 120ms ease',
        opacity: disabled ? 0.75 : 1,
        padding: 0,
      }}
    >
      {icon}
    </button>
  );
}
