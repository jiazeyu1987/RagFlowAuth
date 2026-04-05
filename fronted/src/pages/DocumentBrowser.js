import React, { useEffect, useState } from 'react';
import { documentsApi } from '../features/documents/api';
import { toolbarButtonStyle } from '../features/knowledge/documentBrowser/styles';
import { TEXT } from '../features/knowledge/documentBrowser/constants';
import BatchTransferProgress from '../features/knowledge/documentBrowser/components/BatchTransferProgress';
import DatasetPanel from '../features/knowledge/documentBrowser/components/DatasetPanel';
import FolderTree from '../features/knowledge/documentBrowser/components/FolderTree';
import TransferDialog from '../features/knowledge/documentBrowser/components/TransferDialog';
import useDocumentBrowserPage from '../features/knowledge/documentBrowser/useDocumentBrowserPage';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';

const MOBILE_BREAKPOINT = 768;

export default function DocumentBrowser() {
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

  const {
    canDownload,
    datasetsWithFolders,
    visibleDatasets,
    visibleNodeIds,
    indexes,
    currentFolderId,
    expandedFolderIds,
    folderBreadcrumb,
    datasetsInCurrentFolder,
    transferTargetOptions,
    datasetFilterKeyword,
    recentDatasetKeywords,
    documents,
    documentErrors,
    loading,
    error,
    expandedDatasets,
    actionLoading,
    previewOpen,
    previewTarget,
    transferDialog,
    batchTransferProgress,
    selectedCount,
    setDatasetFilterKeyword,
    setPreviewOpen,
    setPreviewTarget,
    setTransferDialog,
    setBatchTransferProgress,
    quickDatasets,
    openQuickDataset,
    toggleDataset,
    fetchDocumentsForDataset,
    isAllSelectedInDataset,
    handleSelectAllInDataset,
    isDocSelected,
    handleSelectDoc,
    handleView,
    handleDownload,
    handleDelete,
    openSingleTransferDialog,
    canDelete,
    canUpload,
    handleTransferConfirm,
    commitKeyword,
    openFolder,
    toggleFolderExpand,
  } = useDocumentBrowserPage();

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: 400,
          color: '#6b7280',
        }}
      >
        {TEXT.loading}
      </div>
    );
  }

  return (
    <div data-testid="browser-page">
      <div style={{ marginBottom: 24 }}>
        <div
          style={{
            background: '#fff',
            border: '1px solid #e5e7eb',
            borderRadius: 12,
            padding: isMobile ? 14 : 18,
          }}
        >
          <div
            data-testid="browser-quick-datasets"
            style={{
              display: 'grid',
              gridTemplateColumns: isMobile ? 'repeat(2, minmax(0, 1fr))' : 'repeat(5, minmax(0, 1fr))',
              gap: 12,
            }}
          >
            {quickDatasets.map((dataset) => (
              <button
                key={dataset.id || dataset.name}
                type="button"
                onClick={() => openQuickDataset(dataset)}
                data-testid={`browser-quick-dataset-${String(dataset.id || dataset.name).replace(/[^a-zA-Z0-9_-]/g, '_')}`}
                style={{
                  border: '1px solid #dbeafe',
                  background: 'linear-gradient(180deg, #eff6ff 0%, #ffffff 100%)',
                  borderRadius: 12,
                  padding: '12px 14px',
                  textAlign: 'left',
                  cursor: 'pointer',
                  minHeight: 84,
                }}
              >
                <div style={{ fontWeight: 700, color: '#1f2937', marginBottom: 6, wordBreak: 'break-all' }}>
                  {dataset.name}
                </div>
                <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: 8, wordBreak: 'break-all' }}>
                  {dataset.node_path && dataset.node_path !== '/' ? `${TEXT.root} > ${dataset.node_path.split('/').filter(Boolean).join(' > ')}` : TEXT.root}
                </div>
                <div style={{ fontSize: '0.78rem', color: '#2563eb', fontWeight: 700 }}>
                  打开知识库
                </div>
              </button>
            ))}
            {quickDatasets.length === 0 ? (
              <div
                style={{
                  gridColumn: '1 / -1',
                  padding: '20px 0',
                  textAlign: 'center',
                  color: '#6b7280',
                }}
              >
                {TEXT.shortcutEmpty}
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div style={{ background: '#fff', padding: isMobile ? 14 : 16, borderRadius: 8, border: '1px solid #e5e7eb', marginBottom: 16 }}>
        <div style={{ marginBottom: 6, color: '#6b7280', fontSize: '0.85rem' }}>{TEXT.filter}</div>
        <div style={{ display: 'flex', gap: 12, alignItems: isMobile ? 'stretch' : 'center', flexDirection: isMobile ? 'column' : 'row' }}>
          <input
            value={datasetFilterKeyword}
            onChange={(event) => setDatasetFilterKeyword(event.target.value)}
            onBlur={() => commitKeyword(datasetFilterKeyword)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') commitKeyword(datasetFilterKeyword);
            }}
            placeholder={TEXT.filterPlaceholder}
            data-testid="browser-dataset-filter"
            list="browser-dataset-filter-recent"
            style={{ flex: 1, width: '100%', padding: '10px 12px', borderRadius: 6, border: '1px solid #d1d5db', boxSizing: 'border-box' }}
          />
          <button onClick={() => setDatasetFilterKeyword('')} data-testid="browser-dataset-filter-clear" style={{ ...toolbarButtonStyle('neutral'), width: isMobile ? '100%' : 'auto' }}>
            {TEXT.clear}
          </button>
        </div>
        <datalist id="browser-dataset-filter-recent">
          {recentDatasetKeywords.map((value) => (
            <option key={value} value={value} />
          ))}
        </datalist>
        {recentDatasetKeywords.length ? (
          <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>{TEXT.recent}</div>
            {recentDatasetKeywords.map((value) => (
              <button key={value} onClick={() => setDatasetFilterKeyword(value)} style={toolbarButtonStyle('neutral')}>
                {value}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      {error ? (
        <div style={{ background: '#fee2e2', color: '#991b1b', padding: '12px 16px', borderRadius: 4, marginBottom: 20 }} data-testid="browser-error">
          {error}
        </div>
      ) : null}

      <BatchTransferProgress progress={batchTransferProgress} onClose={() => setBatchTransferProgress(null)} />

      {!datasetsWithFolders.length ? (
        <div style={{ background: '#fff', padding: 48, borderRadius: 8, textAlign: 'center', color: '#6b7280' }}>
          {TEXT.noKb}
        </div>
      ) : null}

      {datasetsWithFolders.length && !visibleDatasets.length ? (
        <div style={{ background: '#fff', padding: 48, borderRadius: 8, textAlign: 'center', color: '#6b7280', border: '1px solid #e5e7eb' }}>
          <div style={{ fontWeight: 700, color: '#374151', marginBottom: 6 }}>{TEXT.noMatch}</div>
          <div>{TEXT.noMatchDesc}</div>
        </div>
      ) : null}

      {datasetsWithFolders.length && visibleDatasets.length ? (
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '260px minmax(0, 1fr)', gap: 16, alignItems: 'start' }}>
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, position: isMobile ? 'relative' : 'sticky', top: isMobile ? 'auto' : 12 }}>
            <FolderTree
              indexes={indexes}
              currentFolderId={currentFolderId}
              expandedFolderIds={expandedFolderIds}
              onToggleExpand={toggleFolderExpand}
              onOpenFolder={openFolder}
              visibleNodeIds={visibleNodeIds}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 16 }}>
              <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 8 }}>{TEXT.currentFolder}</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                {folderBreadcrumb.map((item, idx) => (
                  <React.Fragment key={item.id || `root-${idx}`}>
                    <button
                      type="button"
                      onClick={() => openFolder(item.id)}
                      style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: currentFolderId === item.id ? '#1d4ed8' : '#374151', fontWeight: currentFolderId === item.id ? 700 : 500, padding: 0 }}
                    >
                      {item.name}
                    </button>
                    {idx < folderBreadcrumb.length - 1 ? <span style={{ color: '#9ca3af' }}>{'>'}</span> : null}
                  </React.Fragment>
                ))}
              </div>
            </div>

            {datasetsInCurrentFolder.length ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {datasetsInCurrentFolder.map((dataset) => (
                  <DatasetPanel
                    key={dataset.id}
                    dataset={dataset}
                    documents={documents}
                    documentErrors={documentErrors}
                    expandedDatasets={expandedDatasets}
                    toggleDataset={toggleDataset}
                    fetchDocumentsForDataset={fetchDocumentsForDataset}
                    isAllSelectedInDataset={isAllSelectedInDataset}
                    handleSelectAllInDataset={handleSelectAllInDataset}
                    isDocSelected={isDocSelected}
                    handleSelectDoc={handleSelectDoc}
                    handleView={handleView}
                    handleDownload={handleDownload}
                    handleDelete={handleDelete}
                    handleCopy={(docId, datasetName) => openSingleTransferDialog(docId, datasetName, 'copy')}
                    handleMove={(docId, datasetName) => openSingleTransferDialog(docId, datasetName, 'move')}
                    actionLoading={actionLoading}
                    canDownload={canDownload}
                    canUpload={canUpload}
                    canDelete={canDelete}
                  />
                ))}
              </div>
            ) : (
              <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 48, textAlign: 'center', color: '#6b7280' }}>
                {TEXT.emptyFolder}
              </div>
            )}
          </div>
        </div>
      ) : null}

      <DocumentPreviewModal
        open={previewOpen}
        target={previewTarget}
        onClose={() => {
          setPreviewOpen(false);
          setPreviewTarget(null);
        }}
        canDownloadFiles={typeof canDownload === 'function' ? !!canDownload() : false}
        documentApi={documentsApi}
      />
      <TransferDialog
        transferDialog={transferDialog}
        selectedCount={selectedCount}
        transferTargetOptions={transferTargetOptions}
        onClose={() => setTransferDialog(null)}
        onConfirm={handleTransferConfirm}
        onChangeTarget={(targetDatasetName) =>
          setTransferDialog((previous) => ({ ...previous, targetDatasetName }))
        }
      />
    </div>
  );
}
