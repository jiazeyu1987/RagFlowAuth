import React, { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import DocumentAudit from './DocumentAudit';
import DocumentReview from './DocumentReview';

const tabButtonStyle = (active) => ({
  padding: '8px 14px',
  borderRadius: '999px',
  border: `1px solid ${active ? '#3b82f6' : '#d1d5db'}`,
  background: active ? '#eff6ff' : 'white',
  color: active ? '#1d4ed8' : '#374151',
  cursor: 'pointer',
  fontWeight: active ? 600 : 500,
});

const DocumentReviewAudit = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const activeTab = useMemo(() => {
    const t = (searchParams.get('tab') || '').toLowerCase();
    return t === 'records' ? 'records' : 'approve';
  }, [searchParams]);

  const setTab = (tab) => {
    setSearchParams(tab === 'records' ? { tab: 'records' } : {});
  };

  return (
    <div data-testid="documents-page">
      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '14px' }}>
        <button type="button" data-testid="documents-tab-approve" onClick={() => setTab('approve')} style={tabButtonStyle(activeTab === 'approve')}>
          审批
        </button>
        <button type="button" data-testid="documents-tab-records" onClick={() => setTab('records')} style={tabButtonStyle(activeTab === 'records')}>
          记录
        </button>
      </div>

      {activeTab === 'approve' ? <DocumentReview embedded /> : <DocumentAudit embedded />}
    </div>
  );
};

export default DocumentReviewAudit;
