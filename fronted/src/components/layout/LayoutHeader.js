import React from 'react';

const LayoutHeader = ({
  currentTitle,
  headerPadding,
  isMobile,
  onOpenSidebar,
}) => (
  <header
    style={{
      backgroundColor: 'white',
      padding: headerPadding,
      borderBottom: '1px solid #e5e7eb',
      boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
    }}
  >
    {isMobile ? (
      <button
        type="button"
        onClick={onOpenSidebar}
        data-testid="layout-mobile-menu-toggle"
        style={{
          border: '1px solid #d1d5db',
          backgroundColor: 'white',
          color: '#111827',
          borderRadius: '10px',
          padding: '8px 10px',
          fontSize: '1rem',
          lineHeight: 1,
          cursor: 'pointer',
          flexShrink: 0,
        }}
        aria-label="Open sidebar"
      >
        \u2630
      </button>
    ) : null}
    <h1
      style={{ margin: 0, fontSize: isMobile ? '1.2rem' : '1.5rem', color: '#111827', wordBreak: 'break-word' }}
      data-testid="layout-header-title"
    >
      {currentTitle}
    </h1>
  </header>
);

export default LayoutHeader;
