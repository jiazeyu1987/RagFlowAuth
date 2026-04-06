import React from 'react';

import useNmpaToolPage from '../features/drugAdmin/useNmpaToolPage';

const CARD = {
  background: '#ffffff',
  border: '1px solid #e5e7eb',
  borderRadius: '14px',
  boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
};

const buttonStyle = (isMobile) => ({
  padding: '8px 12px',
  borderRadius: '10px',
  border: '1px solid #d1d5db',
  background: '#ffffff',
  color: '#111827',
  cursor: 'pointer',
  fontWeight: 700,
  width: isMobile ? '100%' : 'auto',
});

const primaryButtonStyle = (isMobile) => ({
  ...buttonStyle(isMobile),
  border: '1px solid #bfdbfe',
  background: '#eff6ff',
  color: '#1d4ed8',
});

export default function NMPATool() {
  const { isMobile, handleBack, handleOpenHome, handleOpenCatalog } = useNmpaToolPage();

  return (
    <div style={{ width: '100%', boxSizing: 'border-box' }} data-testid="nmpa-tool-page">
      <div style={{ ...CARD, padding: '16px', marginBottom: '14px' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: '10px',
            alignItems: isMobile ? 'stretch' : 'center',
            flexWrap: 'wrap',
            flexDirection: isMobile ? 'column' : 'row',
          }}
        >
          <div style={{ fontSize: '1.1rem', fontWeight: 900, color: '#111827' }}>NMPA 工具</div>
          <button
            type="button"
            data-testid="nmpa-back-btn"
            onClick={handleBack}
            style={buttonStyle(isMobile)}
          >
            返回实用工具
          </button>
        </div>
        <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.9rem', lineHeight: 1.6 }}>
          国家药监局器审中心快捷入口。
        </div>
      </div>

      <div style={{ ...CARD, padding: '16px' }}>
        <div
          style={{
            display: 'flex',
            gap: '10px',
            flexWrap: 'wrap',
            flexDirection: isMobile ? 'column' : 'row',
          }}
        >
          <button
            type="button"
            onClick={handleOpenHome}
            style={primaryButtonStyle(isMobile)}
            data-testid="nmpa-home-btn"
          >
            主页
          </button>
          <button
            type="button"
            onClick={handleOpenCatalog}
            style={buttonStyle(isMobile)}
            data-testid="nmpa-catalog-btn"
          >
            分类目录
          </button>
        </div>
      </div>
    </div>
  );
}
