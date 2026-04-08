export const pageContainerStyle = {
  maxWidth: '1400px',
};

export const pageHeaderStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: '12px',
  alignItems: 'center',
  flexWrap: 'wrap',
};

export const pageSubtitleStyle = {
  color: '#6b7280',
  marginTop: '6px',
};

export const bannerErrorStyle = {
  marginTop: '12px',
  padding: '10px 12px',
  background: '#fef2f2',
  color: '#991b1b',
  borderRadius: '10px',
};

export const bannerSuccessStyle = {
  marginTop: '12px',
  padding: '10px 12px',
  background: '#ecfdf5',
  color: '#166534',
  borderRadius: '10px',
};

export const cardStyle = {
  background: 'white',
  border: '1px solid #e5e7eb',
  borderRadius: '12px',
  padding: '16px',
  marginTop: '16px',
};

export const tableWrapperStyle = {
  overflowX: 'auto',
};

export const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
};

export const cellStyle = {
  borderBottom: '1px solid #e5e7eb',
  textAlign: 'left',
  padding: '8px',
  verticalAlign: 'top',
  fontSize: '0.9rem',
};

export const inputStyle = {
  padding: '8px 10px',
  borderRadius: '8px',
  border: '1px solid #d1d5db',
  width: '100%',
  background: '#ffffff',
};

export const textareaStyle = {
  ...inputStyle,
  resize: 'vertical',
};

export const buttonStyle = {
  border: '1px solid #d1d5db',
  borderRadius: '8px',
  background: '#ffffff',
  color: '#111827',
  cursor: 'pointer',
  padding: '8px 12px',
};

export const primaryButtonStyle = {
  ...buttonStyle,
  border: 'none',
  background: '#2563eb',
  color: '#ffffff',
};

export const tabListStyle = {
  display: 'flex',
  gap: '8px',
  marginTop: '16px',
  flexWrap: 'wrap',
};

export const sectionGridStyle = {
  display: 'grid',
  gap: '12px',
};

export const labelStyle = {
  display: 'grid',
  gap: '6px',
};

export const twoColumnGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: '12px',
};

export const userLookupContainerStyle = {
  position: 'relative',
};

export const userSearchDropdownStyle = {
  position: 'absolute',
  zIndex: 10,
  top: 'calc(100% + 6px)',
  left: 0,
  right: 0,
  background: '#ffffff',
  border: '1px solid #d1d5db',
  borderRadius: '10px',
  boxShadow: '0 12px 30px rgba(15, 23, 42, 0.12)',
  overflow: 'hidden',
};

export const userSearchMessageStyle = {
  padding: '10px 12px',
  color: '#6b7280',
  fontSize: '0.9rem',
};

export const userSearchErrorStyle = {
  ...userSearchMessageStyle,
  color: '#991b1b',
};

export const userSearchOptionStyle = {
  width: '100%',
  textAlign: 'left',
  border: 'none',
  background: '#ffffff',
  padding: '10px 12px',
  cursor: 'pointer',
  borderTop: '1px solid #f3f4f6',
};

export const userSearchMetaStyle = {
  color: '#6b7280',
  fontSize: '0.8rem',
  marginTop: '2px',
};

export const selectedUserTextStyle = {
  color: '#6b7280',
  fontSize: '0.85rem',
};

export const helperTextStyle = {
  color: '#9ca3af',
  fontSize: '0.8rem',
};
