import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const MOBILE_BREAKPOINT = 768;

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

function openUrl(url) {
  window.open(url, '_blank', 'noopener,noreferrer');
}

export default function NMPATool() {
  const navigate = useNavigate();
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div style={{ width: '100%', boxSizing: 'border-box' }} data-testid="nmpa-tool-page">
      <div style={{ ...CARD, padding: '16px', marginBottom: '14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: isMobile ? 'stretch' : 'center', flexWrap: 'wrap', flexDirection: isMobile ? 'column' : 'row' }}>
          <div style={{ fontSize: '1.1rem', fontWeight: 900, color: '#111827' }}>NMPA 工具</div>
          <button type="button" onClick={() => navigate('/tools')} style={buttonStyle(isMobile)}>返回实用工具</button>
        </div>
        <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.9rem', lineHeight: 1.6 }}>国家药监局器审中心快捷入口。</div>
      </div>

      <div style={{ ...CARD, padding: '16px' }}>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', flexDirection: isMobile ? 'column' : 'row' }}>
          <button type="button" onClick={() => openUrl('https://www.cmde.org.cn/index.html')} style={primaryButtonStyle(isMobile)} data-testid="nmpa-home-btn">主页</button>
          <button type="button" onClick={() => openUrl('https://www.cmde.org.cn/flfg/zdyz/flmlbzh/flmlylqx/index.html')} style={buttonStyle(isMobile)} data-testid="nmpa-catalog-btn">分类目录</button>
        </div>
      </div>
    </div>
  );
}
