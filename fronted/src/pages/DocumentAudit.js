import React, { useEffect, useState } from 'react';
import useDocumentAuditPage from '../features/audit/useDocumentAuditPage';
import { MOBILE_BREAKPOINT } from '../features/audit/documentAuditView';
import DocumentAuditFilters from '../features/audit/components/DocumentAuditFilters';
import DocumentAuditDocumentsTable from '../features/audit/components/DocumentAuditDocumentsTable';
import DocumentAuditDeletionsTable from '../features/audit/components/DocumentAuditDeletionsTable';
import DocumentAuditDownloadsTable from '../features/audit/components/DocumentAuditDownloadsTable';
import DocumentAuditVersionsModal from '../features/audit/components/DocumentAuditVersionsModal';

const renderActiveTable = ({
  activeTab,
  filteredDocuments,
  filteredDeletions,
  filteredDownloads,
  filterKb,
  filterStatus,
  resolveDisplayName,
  openVersionsDialog,
}) => {
  if (activeTab === 'documents') {
    return (
      <DocumentAuditDocumentsTable
        documents={filteredDocuments}
        filterKb={filterKb}
        filterStatus={filterStatus}
        resolveDisplayName={resolveDisplayName}
        onOpenVersionsDialog={openVersionsDialog}
      />
    );
  }

  if (activeTab === 'deletions') {
    return (
      <DocumentAuditDeletionsTable
        deletions={filteredDeletions}
        filterKb={filterKb}
        resolveDisplayName={resolveDisplayName}
      />
    );
  }

  return (
    <DocumentAuditDownloadsTable
      downloads={filteredDownloads}
      filterKb={filterKb}
      resolveDisplayName={resolveDisplayName}
    />
  );
};

const DocumentAudit = () => {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const {
    documents,
    deletions,
    downloads,
    loading,
    error,
    activeTab,
    filterKb,
    filterStatus,
    versionsDialog,
    knowledgeBases,
    filteredDocuments,
    filteredDeletions,
    filteredDownloads,
    setActiveTab,
    setFilterKb,
    setFilterStatus,
    resetFilters,
    resolveDisplayName,
    closeVersionsDialog,
    openVersionsDialog,
  } = useDocumentAuditPage();

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  if (loading) {
    return <div style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>加载中...</div>;
  }

  return (
    <div data-testid="audit-page">
      <div style={{ marginBottom: '24px' }}>
        <div
          style={{
            marginBottom: '16px',
            borderBottom: '1px solid #e5e7eb',
            display: 'flex',
            flexWrap: 'wrap',
            gap: isMobile ? '8px' : 0,
          }}
        >
          <button
            type="button"
            onClick={() => setActiveTab('documents')}
            data-testid="audit-tab-documents"
            style={{
              padding: '10px 20px',
              backgroundColor: activeTab === 'documents' ? '#3b82f6' : 'transparent',
              color: activeTab === 'documents' ? 'white' : '#6b7280',
              border: 'none',
              borderBottom:
                activeTab === 'documents' ? '2px solid #3b82f6' : '2px solid transparent',
              cursor: 'pointer',
              fontSize: '0.95rem',
              fontWeight: activeTab === 'documents' ? '600' : '400',
              marginRight: isMobile ? 0 : '8px',
            }}
          >
            {`文档列表 (${documents.length})`}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('deletions')}
            data-testid="audit-tab-deletions"
            style={{
              padding: '10px 20px',
              backgroundColor: activeTab === 'deletions' ? '#ef4444' : 'transparent',
              color: activeTab === 'deletions' ? 'white' : '#6b7280',
              border: 'none',
              borderBottom:
                activeTab === 'deletions' ? '2px solid #ef4444' : '2px solid transparent',
              cursor: 'pointer',
              fontSize: '0.95rem',
              fontWeight: activeTab === 'deletions' ? '600' : '400',
              marginRight: isMobile ? 0 : '8px',
            }}
          >
            {`删除记录 (${deletions.length})`}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('downloads')}
            data-testid="audit-tab-downloads"
            style={{
              padding: '10px 20px',
              backgroundColor: activeTab === 'downloads' ? '#10b981' : 'transparent',
              color: activeTab === 'downloads' ? 'white' : '#6b7280',
              border: 'none',
              borderBottom:
                activeTab === 'downloads' ? '2px solid #10b981' : '2px solid transparent',
              cursor: 'pointer',
              fontSize: '0.95rem',
              fontWeight: activeTab === 'downloads' ? '600' : '400',
            }}
          >
            {`下载记录 (${downloads.length})`}
          </button>
        </div>

        <DocumentAuditFilters
          isMobile={isMobile}
          activeTab={activeTab}
          knowledgeBases={knowledgeBases}
          filterKb={filterKb}
          filterStatus={filterStatus}
          filteredDocumentsCount={filteredDocuments.length}
          filteredDeletionsCount={filteredDeletions.length}
          filteredDownloadsCount={filteredDownloads.length}
          onFilterKbChange={setFilterKb}
          onFilterStatusChange={setFilterStatus}
          onResetFilters={resetFilters}
        />
      </div>

      {error ? (
        <div style={{ marginBottom: '16px', color: '#dc2626', fontSize: '0.95rem' }}>{error}</div>
      ) : null}

      {renderActiveTable({
        activeTab,
        filteredDocuments,
        filteredDeletions,
        filteredDownloads,
        filterKb,
        filterStatus,
        resolveDisplayName,
        openVersionsDialog,
      })}

      <DocumentAuditVersionsModal
        versionsDialog={versionsDialog}
        onClose={closeVersionsDialog}
        resolveDisplayName={resolveDisplayName}
      />
    </div>
  );
};

export default DocumentAudit;

