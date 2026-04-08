import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import NasBrowserHeader from '../features/knowledge/nasBrowser/components/NasBrowserHeader';
import NasBrowserImportDialog from '../features/knowledge/nasBrowser/components/NasBrowserImportDialog';
import NasBrowserItemsTable from '../features/knowledge/nasBrowser/components/NasBrowserItemsTable';
import NasBrowserPathBar from '../features/knowledge/nasBrowser/components/NasBrowserPathBar';
import NasBrowserProgressPanel from '../features/knowledge/nasBrowser/components/NasBrowserProgressPanel';
import { PAGE_STYLE } from '../features/knowledge/nasBrowser/utils';
import useNasBrowserPage from '../features/knowledge/nasBrowser/useNasBrowserPage';

const MOBILE_BREAKPOINT = 768;

export default function NasBrowser() {
  const navigate = useNavigate();
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

  const {
    admin,
    loading,
    error,
    currentPath,
    parentPath,
    items,
    datasets,
    importDialogOpen,
    importTarget,
    selectedKb,
    importLoading,
    folderImportProgress,
    breadcrumbs,
    skippedDetails,
    failedDetails,
    setSelectedKb,
    loadPath,
    openImportDialog,
    closeImportDialog,
    handleImport,
    closeProgressPanel,
    formatImportReason,
  } = useNasBrowserPage();

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  if (!admin) {
    return <div style={{ color: '#991b1b' }}>仅管理员可访问 NAS 云盘。</div>;
  }

  return (
    <div style={PAGE_STYLE} data-testid="nas-browser-page">
      <NasBrowserHeader
        isMobile={isMobile}
        currentPath={currentPath}
        onBackToTools={() => navigate('/tools')}
        loadPath={loadPath}
      />

      <NasBrowserPathBar
        isMobile={isMobile}
        breadcrumbs={breadcrumbs}
        currentPath={currentPath}
        parentPath={parentPath}
        loadPath={loadPath}
      />

      <NasBrowserProgressPanel
        isMobile={isMobile}
        folderImportProgress={folderImportProgress}
        skippedDetails={skippedDetails}
        failedDetails={failedDetails}
        closeProgressPanel={closeProgressPanel}
        formatImportReason={formatImportReason}
      />

      {error && (
        <div
          style={{
            marginTop: '16px',
            padding: '12px 16px',
            borderRadius: '12px',
            background: '#fef2f2',
            color: '#b91c1c',
            border: '1px solid #fecaca',
          }}
        >
          {error}
        </div>
      )}

      <NasBrowserItemsTable
        isMobile={isMobile}
        loading={loading}
        items={items}
        loadPath={loadPath}
        openImportDialog={openImportDialog}
      />

      <NasBrowserImportDialog
        isMobile={isMobile}
        importDialogOpen={importDialogOpen}
        importTarget={importTarget}
        datasets={datasets}
        selectedKb={selectedKb}
        setSelectedKb={setSelectedKb}
        importLoading={importLoading}
        closeImportDialog={closeImportDialog}
        handleImport={handleImport}
      />
    </div>
  );
}
