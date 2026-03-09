import React from 'react';
import { canPreviewFilename, TEXT } from '../constants';
import { actionButtonStyle } from '../styles';

export default function DatasetPanel({
  dataset,
  documents,
  documentErrors,
  expandedDatasets,
  toggleDataset,
  fetchDocumentsForDataset,
  isAllSelectedInDataset,
  handleSelectAllInDataset,
  isDocSelected,
  handleSelectDoc,
  handleView,
  handleDownload,
  handleDelete,
  handleCopy,
  handleMove,
  actionLoading,
  canDownload,
  canUpload,
  canDelete,
}) {
  const datasetDocs = documents[dataset.name] || [];
  const datasetError = documentErrors[dataset.name] || '';
  const isExpanded = expandedDatasets.has(dataset.name);
  const loadingDocs = !Object.prototype.hasOwnProperty.call(documents, dataset.name) && !datasetError;

  return (
    <div
      data-testid={`browser-dataset-${dataset.id}`}
      style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden' }}
    >
      <div
        data-testid={`browser-dataset-toggle-${dataset.id}`}
        onClick={() => toggleDataset(dataset.name)}
        style={{
          padding: '14px 16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
          background: '#f9fafb',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ fontSize: '1rem', transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>{'>'}</div>
          <div>
            <div style={{ fontWeight: 700, color: '#111827' }}>{dataset.name}</div>
            <div style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: 2 }}>
              {dataset.node_path && dataset.node_path !== '/' ? `${TEXT.root} -> ${dataset.node_path.split('/').filter(Boolean).join(' -> ')}` : TEXT.root}
            </div>
          </div>
        </div>
        <span style={{ padding: '4px 8px', background: '#dbeafe', color: '#1e40af', borderRadius: 4, fontSize: '0.85rem' }}>
          {loadingDocs ? '...' : datasetDocs.length}
        </span>
      </div>

      {isExpanded ? (
        <div style={{ padding: 16 }}>
          {loadingDocs ? <div style={{ color: '#6b7280', textAlign: 'center', padding: 20 }}>{TEXT.loadingDocs}</div> : null}
          {!loadingDocs && datasetError ? (
            <div style={{ color: '#dc2626', textAlign: 'center', padding: 20 }}>
              <div style={{ marginBottom: 10 }}>Load failed: {datasetError}</div>
              <button type="button" onClick={() => fetchDocumentsForDataset(dataset.name)}>{TEXT.retry}</button>
            </div>
          ) : null}
          {!loadingDocs && !datasetError && datasetDocs.length === 0 ? (
            <div style={{ color: '#6b7280', textAlign: 'center', padding: 20 }}>{TEXT.noDocs}</div>
          ) : null}

          {!loadingDocs && !datasetError && datasetDocs.length > 0 ? (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ width: 40, textAlign: 'left', padding: '12px 8px' }}>
                    <input
                      type="checkbox"
                      checked={isAllSelectedInDataset(dataset.name)}
                      onChange={() => handleSelectAllInDataset(dataset.name)}
                      data-testid={`browser-dataset-selectall-${dataset.id}`}
                    />
                  </th>
                  <th style={{ textAlign: 'left', padding: '12px 8px', color: '#6b7280' }}>{TEXT.docName}</th>
                  <th style={{ textAlign: 'right', padding: '12px 8px', color: '#6b7280', width: 420 }}>{'\u64cd\u4f5c'}</th>
                </tr>
              </thead>
              <tbody>
                {datasetDocs.map((doc) => {
                  const viewDisabled = actionLoading[`${doc.id}-view`] || !canPreviewFilename(doc.name);
                  return (
                    <tr key={doc.id} data-testid={`browser-doc-row-${dataset.id}-${doc.id}`} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '12px 8px' }}>
                        <input
                          type="checkbox"
                          checked={isDocSelected(doc.id, dataset.name)}
                          onChange={() => handleSelectDoc(doc.id, dataset.name)}
                          data-testid={`browser-doc-select-${dataset.id}-${doc.id}`}
                        />
                      </td>
                      <td style={{ padding: '12px 8px', fontWeight: 500, color: '#111827' }}>{doc.name}</td>
                      <td style={{ padding: '12px 8px', textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                          <button
                            type="button"
                            onClick={() => handleView(doc.id, dataset.name)}
                            data-testid={`browser-doc-view-${dataset.id}-${doc.id}`}
                            disabled={viewDisabled}
                            title={!canPreviewFilename(doc.name) ? TEXT.viewUnsupported : ''}
                            style={actionButtonStyle('view', viewDisabled)}
                          >
                            {actionLoading[`${doc.id}-view`] ? TEXT.viewing : TEXT.view}
                          </button>

                          {canDownload() ? (
                            <button
                              type="button"
                              onClick={() => handleDownload(doc.id, dataset.name)}
                              data-testid={`browser-doc-download-${dataset.id}-${doc.id}`}
                              disabled={actionLoading[`${doc.id}-download`]}
                              style={actionButtonStyle('download', actionLoading[`${doc.id}-download`])}
                            >
                              {actionLoading[`${doc.id}-download`] ? TEXT.downloading : TEXT.download}
                            </button>
                          ) : null}

                          {canUpload() ? (
                            <button
                              type="button"
                              onClick={() => handleCopy(doc.id, dataset.name)}
                              data-testid={`browser-doc-copy-${dataset.id}-${doc.id}`}
                              disabled={actionLoading[`${doc.id}-copy`]}
                              style={actionButtonStyle('copy', actionLoading[`${doc.id}-copy`])}
                            >
                              {TEXT.copyTo}
                            </button>
                          ) : null}

                          {canUpload() && canDelete() ? (
                            <button
                              type="button"
                              onClick={() => handleMove(doc.id, dataset.name)}
                              data-testid={`browser-doc-move-${dataset.id}-${doc.id}`}
                              disabled={actionLoading[`${doc.id}-move`]}
                              style={actionButtonStyle('move', actionLoading[`${doc.id}-move`])}
                            >
                              {TEXT.moveTo}
                            </button>
                          ) : null}

                          {canDelete() ? (
                            <button
                              type="button"
                              onClick={() => handleDelete(doc.id, dataset.name)}
                              data-testid={`browser-doc-delete-${dataset.id}-${doc.id}`}
                              disabled={actionLoading[`${doc.id}-delete`]}
                              style={actionButtonStyle('delete', actionLoading[`${doc.id}-delete`])}
                            >
                              {TEXT.delete}
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
