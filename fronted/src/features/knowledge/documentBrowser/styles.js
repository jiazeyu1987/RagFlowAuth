export function actionButtonStyle(kind, disabled) {
  const palette = {
    view: { background: '#eef2ff', color: '#4338ca', border: '#c7d2fe' },
    download: { background: '#eff6ff', color: '#1d4ed8', border: '#bfdbfe' },
    copy: { background: '#ecfeff', color: '#0e7490', border: '#a5f3fc' },
    move: { background: '#fefce8', color: '#a16207', border: '#fde68a' },
    delete: { background: '#fef2f2', color: '#dc2626', border: '#fecaca' },
  };
  const tone = palette[kind] || palette.view;
  return {
    padding: '7px 12px',
    borderRadius: 999,
    border: `1px solid ${tone.border}`,
    background: tone.background,
    color: tone.color,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.55 : 1,
    fontSize: '0.84rem',
    fontWeight: 700,
    lineHeight: 1,
    boxShadow: disabled ? 'none' : '0 1px 2px rgba(15, 23, 42, 0.06)',
  };
}

export function toolbarButtonStyle(kind, disabled = false) {
  const palette = {
    primary: { background: '#e0f2fe', color: '#075985', border: '#bae6fd' },
    neutral: { background: '#f3f4f6', color: '#374151', border: '#d1d5db' },
    success: { background: '#ecfdf5', color: '#047857', border: '#a7f3d0' },
    accent: { background: '#f5f3ff', color: '#6d28d9', border: '#ddd6fe' },
    danger: { background: '#fef2f2', color: '#dc2626', border: '#fecaca' },
  };
  const tone = palette[kind] || palette.neutral;
  return {
    padding: '9px 14px',
    borderRadius: 999,
    border: `1px solid ${tone.border}`,
    background: tone.background,
    color: tone.color,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.55 : 1,
    fontSize: '0.9rem',
    fontWeight: 700,
    lineHeight: 1,
    boxShadow: disabled ? 'none' : '0 1px 2px rgba(15, 23, 42, 0.06)',
    whiteSpace: 'nowrap',
  };
}
