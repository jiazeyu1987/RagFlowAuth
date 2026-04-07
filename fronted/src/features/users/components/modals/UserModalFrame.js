import React from 'react';
import useMobileBreakpoint from '../../../../shared/hooks/useMobileBreakpoint';

const MOBILE_BREAKPOINT = 768;

export default function UserModalFrame({
  open,
  testId,
  title,
  titleMarginBottom = '24px',
  maxWidth = '500px',
  desktopPadding = '32px',
  mobilePadding = '20px 16px',
  children,
}) {
  const isMobile = useMobileBreakpoint(MOBILE_BREAKPOINT);

  if (!open) return null;

  return (
    <div
      data-testid={testId}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: isMobile ? 'stretch' : 'center',
        padding: isMobile ? '16px 12px' : '24px',
        zIndex: 1000,
      }}
    >
      <div
        style={{
          backgroundColor: 'white',
          padding: isMobile ? mobilePadding : desktopPadding,
          borderRadius: '8px',
          width: '100%',
          maxWidth,
          maxHeight: isMobile ? '100%' : '90vh',
          overflowY: 'auto',
          margin: isMobile ? 'auto 0' : 0,
        }}
      >
        <h3 style={{ margin: `0 0 ${titleMarginBottom} 0` }}>{title}</h3>
        {typeof children === 'function' ? children({ isMobile }) : children}
      </div>
    </div>
  );
}
