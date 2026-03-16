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
    <div data-testid={`browser-dataset-${dataset.id}`} className="browser-med-dataset">
      <div data-testid={`browser-dataset-toggle-${dataset.id}`} onClick={() => toggleDataset(dataset.name)} className="browser-med-dataset-head">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ fontSize: '1rem', transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>{'>'}</div>
          <div>
            <div className="browser-med-dataset-name">{dataset.name}</div>
            <div className="browser-med-dataset-sub">
              {dataset.node_path && dataset.node_path !== '/'
                ? `${TEXT.root} -> ${dataset.node_path.split('/').filter(Boolean).join(' -> ')}`
                : TEXT.root}
            </div>
          </div>
        </div>
        <span className="browser-med-dataset-count">{loadingDocs ? '...' : datasetDocs.length}</span>
      </div>

      {isExpanded ? (
        <div style={{ padding: 14 }}>
          {loadingDocs ? <div className="medui-empty" style={{ padding: 20 }}>{TEXT.loadingDocs}</div> : null}
          {!loadingDocs && datasetError ? (
            <div className="browser-med-error" style={{ textAlign: 'center' }}>
              <div style={{ marginBottom: 10 }}>{`加载失败：${datasetError}`}</div>
              <button type="button" onClick={() => fetchDocumentsForDataset(dataset.name)} className="medui-btn medui-btn--neutral">
                {TEXT.retry}
              </button>
            </div>
          ) : null}
          {!loadingDocs && !datasetError && datasetDocs.length === 0 ? (
            <div className="medui-empty" style={{ padding: 20 }}>{TEXT.noDocs}</div>
          ) : null}

          {!loadingDocs && !datasetError && datasetDocs.length > 0 ? (
            <table className="browser-med-doc-table">
              <thead>
                <tr>
                  <th style={{ width: 40 }}>
                    <input
                      type="checkbox"
                      checked={isAllSelectedInDataset(dataset.name)}
                      onChange={() => handleSelectAllInDataset(dataset.name)}
                      data-testid={`browser-dataset-selectall-${dataset.id}`}
                    />
                  </th>
                  <th>{TEXT.docName}</th>
                  <th style={{ textAlign: 'right', width: 420 }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {datasetDocs.map((doc) => {
                  const viewDisabled = actionLoading[`${doc.id}-view`] || !canPreviewFilename(doc.name);
                  return (
                    <tr key={doc.id} data-testid={`browser-doc-row-${dataset.id}-${doc.id}`}>
                      <td>
                        <input
                          type="checkbox"
                          checked={isDocSelected(doc.id, dataset.name)}
                          onChange={() => handleSelectDoc(doc.id, dataset.name)}
                          data-testid={`browser-doc-select-${dataset.id}-${doc.id}`}
                        />
                      </td>
                      <td style={{ fontWeight: 600, color: '#173d60' }}>{doc.name}</td>
                      <td style={{ textAlign: 'right' }}>
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
