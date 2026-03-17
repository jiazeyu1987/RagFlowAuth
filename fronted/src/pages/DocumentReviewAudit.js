import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import DocumentAudit from './DocumentAudit';
import DocumentReview from './DocumentReview';

const MOBILE_BREAKPOINT = 768;

const tabButtonStyle = (active, isMobile) => ({
  padding: '8px 14px',
  borderRadius: '999px',
  border: `1px solid ${active ? '#3b82f6' : '#d1d5db'}`,
  background: active ? '#eff6ff' : 'white',
  color: active ? '#1d4ed8' : '#374151',
  cursor: 'pointer',
  fontWeight: active ? 600 : 500,
  width: isMobile ? '100%' : 'auto',
});

const DocumentReviewAudit = () => {
  const [searchParams, setSearchParams] = useSearchParams();
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

  const activeTab = useMemo(() => {
    const tab = (searchParams.get('tab') || '').toLowerCase();
    return tab === 'records' ? 'records' : 'approve';
  }, [searchParams]);

  const setTab = (tab) => {
    setSearchParams(tab === 'records' ? { tab: 'records' } : {});
  };

  return (
    <div data-testid="documents-page">
      <div
        style={{
          display: 'flex',
          gap: '10px',
          alignItems: 'center',
          marginBottom: '14px',
          flexWrap: 'wrap',
          flexDirection: isMobile ? 'column' : 'row',
        }}
      >
        <button
          type="button"
          data-testid="documents-tab-approve"
          onClick={() => setTab('approve')}
          style={tabButtonStyle(activeTab === 'approve', isMobile)}
        >
          审核
        </button>
        <button
          type="button"
          data-testid="documents-tab-records"
          onClick={() => setTab('records')}
          style={tabButtonStyle(activeTab === 'records', isMobile)}
        >
          审核记录
        </button>
      </div>

      {activeTab === 'approve' ? <DocumentReview embedded /> : <DocumentAudit embedded />}
    </div>
  );
};

export default DocumentReviewAudit;
