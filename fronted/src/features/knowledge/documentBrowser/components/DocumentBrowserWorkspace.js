import React from 'react';

import { TEXT } from '../constants';
import DatasetPanel from './DatasetPanel';
import FolderTree from './FolderTree';

export default function DocumentBrowserWorkspace({
  actionLoading,
  canDelete,
  canDownload,
  canUpload,
  currentFolderId,
  datasetsInCurrentFolder,
  datasetsWithFolders,
  documentErrors,
  documents,
  expandedDatasets,
  expandedFolderIds,
  fetchDocumentsForDataset,
  folderBreadcrumb,
  indexes,
  isAllSelectedInDataset,
  isDocSelected,
  isMobile,
  handleDelete,
  handleDownload,
  handleSelectAllInDataset,
  handleSelectDoc,
  handleView,
  onMoveDoc,
  onCopyDoc,
  openFolder,
  toggleDataset,
  toggleFolderExpand,
  visibleDatasets,
  visibleNodeIds,
}) {
  if (!datasetsWithFolders.length) {
    return (
      <div
        style={{
          background: '#fff',
          padding: 48,
          borderRadius: 8,
          textAlign: 'center',
          color: '#6b7280',
        }}
      >
        {TEXT.noKb}
      </div>
    );
  }

  if (!visibleDatasets.length) {
    return (
      <div
        style={{
          background: '#fff',
          padding: 48,
          borderRadius: 8,
          textAlign: 'center',
          color: '#6b7280',
          border: '1px solid #e5e7eb',
        }}
      >
        <div style={{ fontWeight: 700, color: '#374151', marginBottom: 6 }}>{TEXT.noMatch}</div>
        <div>{TEXT.noMatchDesc}</div>
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : '260px minmax(0, 1fr)',
        gap: 16,
        alignItems: 'start',
      }}
    >
      <div
        style={{
          background: '#fff',
          border: '1px solid #e5e7eb',
          borderRadius: 8,
          padding: 12,
          position: isMobile ? 'relative' : 'sticky',
          top: isMobile ? 'auto' : 12,
        }}
      >
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
        <div
          style={{
            background: '#fff',
            border: '1px solid #e5e7eb',
            borderRadius: 8,
            padding: 16,
          }}
        >
          <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 8 }}>
            {TEXT.currentFolder}
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            {folderBreadcrumb.map((item, idx) => (
              <React.Fragment key={item.id || `root-${idx}`}>
                <button
                  type="button"
                  onClick={() => openFolder(item.id)}
                  style={{
                    border: 'none',
                    background: 'transparent',
                    cursor: 'pointer',
                    color: currentFolderId === item.id ? '#1d4ed8' : '#374151',
                    fontWeight: currentFolderId === item.id ? 700 : 500,
                    padding: 0,
                  }}
                >
                  {item.name}
                </button>
                {idx < folderBreadcrumb.length - 1 ? (
                  <span style={{ color: '#9ca3af' }}>{'>'}</span>
                ) : null}
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
                handleCopy={onCopyDoc}
                handleMove={onMoveDoc}
                actionLoading={actionLoading}
                canDownload={canDownload}
                canUpload={canUpload}
                canDelete={canDelete}
              />
            ))}
          </div>
        ) : (
          <div
            style={{
              background: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: 8,
              padding: 48,
              textAlign: 'center',
              color: '#6b7280',
            }}
          >
            {TEXT.emptyFolder}
          </div>
        )}
      </div>
    </div>
  );
}
