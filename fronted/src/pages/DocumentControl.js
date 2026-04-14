import React from 'react';
import useDocumentControlPage from '../features/documentControl/useDocumentControlPage';
import { mapUserFacingErrorMessage } from '../shared/errors/userFacingErrorMessages';

const panelStyle = {
  background: '#ffffff',
  border: '1px solid #d7dde5',
  borderRadius: 8,
  padding: 16,
  boxShadow: '0 10px 24px rgba(15, 23, 42, 0.06)',
};

const inputStyle = {
  width: '100%',
  padding: 10,
  border: '1px solid #c7d2de',
  borderRadius: 6,
  boxSizing: 'border-box',
};

const labelStyle = {
  display: 'block',
  marginBottom: 6,
  fontSize: 13,
  fontWeight: 600,
  color: '#334155',
};

const secondaryButtonStyle = {
  padding: '10px 14px',
  borderRadius: 6,
  border: '1px solid #b8c4d1',
  background: '#f8fafc',
  color: '#1e293b',
  cursor: 'pointer',
};

const primaryButtonStyle = {
  ...secondaryButtonStyle,
  border: '1px solid #0f766e',
  background: '#0f766e',
  color: '#ffffff',
};

const dangerButtonStyle = {
  ...secondaryButtonStyle,
  border: '1px solid #be123c',
  color: '#9f1239',
  background: '#fff1f2',
};

const STATUS_TRANSITIONS = {
  draft: ['in_review'],
  in_review: ['approved'],
  approved: ['effective'],
  effective: ['obsolete'],
};

const prettyStatus = (value) => String(value || '-').replaceAll('_', ' ');

const renderRevisionMeta = (revision) => {
  if (!revision) return '-';
  return `v${revision.revision_no} · ${prettyStatus(revision.status)} · ${revision.filename}`;
};

export default function DocumentControl() {
  const {
    loading,
    detailLoading,
    savingDocument,
    savingRevision,
    transitioningRevisionId,
    filters,
    documents,
    selectedDocumentId,
    selectedDocument,
    currentRevision,
    effectiveRevision,
    revisions,
    documentForm,
    revisionForm,
    error,
    success,
    setDocumentForm,
    setRevisionForm,
    handleFilterChange,
    handleSearch,
    handleSelectDocument,
    handleCreateDocument,
    handleCreateRevision,
    handleTransitionRevision,
  } = useDocumentControlPage({ mapErrorMessage: mapUserFacingErrorMessage });

  return (
    <div
      data-testid="document-control-page"
      style={{
        padding: 20,
        display: 'grid',
        gap: 16,
        background:
          'linear-gradient(180deg, rgba(240,249,255,1) 0%, rgba(248,250,252,1) 100%)',
      }}
    >
      <div style={{ ...panelStyle, display: 'grid', gap: 12 }}>
        <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>
          <label style={labelStyle}>
            Search
            <input
              data-testid="document-control-filter-query"
              style={inputStyle}
              value={filters.query}
              onChange={(event) => handleFilterChange('query', event.target.value)}
            />
          </label>
          <label style={labelStyle}>
            Doc Code
            <input
              data-testid="document-control-filter-doc-code"
              style={inputStyle}
              value={filters.docCode}
              onChange={(event) => handleFilterChange('docCode', event.target.value)}
            />
          </label>
          <label style={labelStyle}>
            Title
            <input
              data-testid="document-control-filter-title"
              style={inputStyle}
              value={filters.title}
              onChange={(event) => handleFilterChange('title', event.target.value)}
            />
          </label>
          <label style={labelStyle}>
            Status
            <select
              data-testid="document-control-filter-status"
              style={inputStyle}
              value={filters.status}
              onChange={(event) => handleFilterChange('status', event.target.value)}
            >
              <option value="">All</option>
              <option value="draft">draft</option>
              <option value="in_review">in_review</option>
              <option value="approved">approved</option>
              <option value="effective">effective</option>
              <option value="obsolete">obsolete</option>
            </select>
          </label>
        </div>
        <div>
          <button
            type="button"
            data-testid="document-control-search"
            onClick={handleSearch}
            style={primaryButtonStyle}
          >
            Search
          </button>
        </div>
      </div>

      {error ? (
        <div
          data-testid="document-control-error"
          style={{ ...panelStyle, borderColor: '#fecaca', background: '#fff1f2', color: '#9f1239' }}
        >
          {error}
        </div>
      ) : null}

      {success ? (
        <div
          data-testid="document-control-success"
          style={{ ...panelStyle, borderColor: '#bbf7d0', background: '#f0fdf4', color: '#166534' }}
        >
          {success}
        </div>
      ) : null}

      <div
        style={{
          display: 'grid',
          gap: 16,
          gridTemplateColumns: 'minmax(320px, 0.9fr) minmax(420px, 1.1fr)',
        }}
      >
        <div style={{ display: 'grid', gap: 16 }}>
          <section style={panelStyle}>
            <h2 style={{ marginTop: 0 }}>Controlled Documents</h2>
            {loading ? <div data-testid="document-control-loading">Loading...</div> : null}
            <div style={{ display: 'grid', gap: 8 }}>
              {documents.map((document) => (
                <button
                  key={document.controlled_document_id}
                  type="button"
                  data-testid={`document-control-row-${document.controlled_document_id}`}
                  onClick={() => handleSelectDocument(document.controlled_document_id)}
                  style={{
                    textAlign: 'left',
                    padding: 12,
                    borderRadius: 6,
                    border:
                      selectedDocumentId === document.controlled_document_id
                        ? '1px solid #0f766e'
                        : '1px solid #d7dde5',
                    background:
                      selectedDocumentId === document.controlled_document_id ? '#ecfeff' : '#ffffff',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontWeight: 700 }}>{document.doc_code}</div>
                  <div>{document.title}</div>
                  <div style={{ fontSize: 13, color: '#475569' }}>
                    {renderRevisionMeta(document.current_revision)}
                  </div>
                </button>
              ))}
              {!loading && documents.length === 0 ? (
                <div data-testid="document-control-empty">No controlled documents</div>
              ) : null}
            </div>
          </section>

          <section style={panelStyle}>
            <h2 style={{ marginTop: 0 }}>Create Controlled Document</h2>
            <div style={{ display: 'grid', gap: 10 }}>
              <label style={labelStyle}>
                Doc Code
                <input
                  data-testid="document-control-create-doc-code"
                  style={inputStyle}
                  value={documentForm.doc_code}
                  onChange={(event) =>
                    setDocumentForm((previous) => ({ ...previous, doc_code: event.target.value }))
                  }
                />
              </label>
              <label style={labelStyle}>
                Title
                <input
                  data-testid="document-control-create-title"
                  style={inputStyle}
                  value={documentForm.title}
                  onChange={(event) =>
                    setDocumentForm((previous) => ({ ...previous, title: event.target.value }))
                  }
                />
              </label>
              <label style={labelStyle}>
                Document Type
                <input
                  data-testid="document-control-create-document-type"
                  style={inputStyle}
                  value={documentForm.document_type}
                  onChange={(event) =>
                    setDocumentForm((previous) => ({
                      ...previous,
                      document_type: event.target.value,
                    }))
                  }
                />
              </label>
              <label style={labelStyle}>
                Target KB
                <input
                  data-testid="document-control-create-target-kb"
                  style={inputStyle}
                  value={documentForm.target_kb_id}
                  onChange={(event) =>
                    setDocumentForm((previous) => ({ ...previous, target_kb_id: event.target.value }))
                  }
                />
              </label>
              <label style={labelStyle}>
                Product *
                <input
                  data-testid="document-control-create-product-name"
                  style={inputStyle}
                  value={documentForm.product_name}
                  required
                  onChange={(event) =>
                    setDocumentForm((previous) => ({
                      ...previous,
                      product_name: event.target.value,
                    }))
                  }
                />
              </label>
              <label style={labelStyle}>
                Registration Ref *
                <input
                  data-testid="document-control-create-registration-ref"
                  style={inputStyle}
                  value={documentForm.registration_ref}
                  required
                  onChange={(event) =>
                    setDocumentForm((previous) => ({
                      ...previous,
                      registration_ref: event.target.value,
                    }))
                  }
                />
              </label>
              <label style={labelStyle}>
                Change Summary
                <textarea
                  data-testid="document-control-create-change-summary"
                  style={{ ...inputStyle, minHeight: 84 }}
                  value={documentForm.change_summary}
                  onChange={(event) =>
                    setDocumentForm((previous) => ({
                      ...previous,
                      change_summary: event.target.value,
                    }))
                  }
                />
              </label>
              <label style={labelStyle}>
                File
                <input
                  data-testid="document-control-create-file"
                  type="file"
                  style={inputStyle}
                  onChange={(event) =>
                    setDocumentForm((previous) => ({
                      ...previous,
                      file: event.target.files?.[0] || null,
                    }))
                  }
                />
              </label>
              <button
                type="button"
                data-testid="document-control-create-submit"
                disabled={savingDocument}
                onClick={handleCreateDocument}
                style={primaryButtonStyle}
              >
                {savingDocument ? 'Saving...' : 'Create document'}
              </button>
            </div>
          </section>
        </div>

        <div style={{ display: 'grid', gap: 16 }}>
          <section style={panelStyle}>
            <h2 style={{ marginTop: 0 }}>Document Detail</h2>
            {detailLoading ? <div data-testid="document-control-detail-loading">Loading detail...</div> : null}
            {!selectedDocument ? (
              <div data-testid="document-control-no-selection">Select a document to inspect revisions.</div>
            ) : (
              <div style={{ display: 'grid', gap: 10 }}>
                <div data-testid="document-control-detail-doc-code">
                  <strong>{selectedDocument.doc_code}</strong> · {selectedDocument.title}
                </div>
                <div>Type: {selectedDocument.document_type}</div>
                <div>Product: {selectedDocument.product_name || '-'}</div>
                <div>Registration: {selectedDocument.registration_ref || '-'}</div>
                <div>Target KB: {selectedDocument.target_kb_name || selectedDocument.target_kb_id}</div>
                <div data-testid="document-control-current-revision">
                  Current revision: {renderRevisionMeta(currentRevision)}
                </div>
                <div data-testid="document-control-effective-revision">
                  Effective revision: {renderRevisionMeta(effectiveRevision)}
                </div>
              </div>
            )}
          </section>

          <section style={panelStyle}>
            <h2 style={{ marginTop: 0 }}>Create Revision</h2>
            <div style={{ display: 'grid', gap: 10 }}>
              <label style={labelStyle}>
                Change Summary
                <textarea
                  data-testid="document-control-revision-change-summary"
                  style={{ ...inputStyle, minHeight: 84 }}
                  value={revisionForm.change_summary}
                  onChange={(event) =>
                    setRevisionForm((previous) => ({
                      ...previous,
                      change_summary: event.target.value,
                    }))
                  }
                />
              </label>
              <label style={labelStyle}>
                File
                <input
                  data-testid="document-control-revision-file"
                  type="file"
                  style={inputStyle}
                  onChange={(event) =>
                    setRevisionForm((previous) => ({
                      ...previous,
                      file: event.target.files?.[0] || null,
                    }))
                  }
                />
              </label>
              <button
                type="button"
                data-testid="document-control-revision-submit"
                disabled={savingRevision || !selectedDocumentId}
                onClick={handleCreateRevision}
                style={primaryButtonStyle}
              >
                {savingRevision ? 'Saving...' : 'Create revision'}
              </button>
            </div>
          </section>

          <section style={panelStyle}>
            <h2 style={{ marginTop: 0 }}>Revision History</h2>
            <div style={{ display: 'grid', gap: 10 }}>
              {revisions.map((revision) => (
                <div
                  key={revision.controlled_revision_id}
                  data-testid={`document-control-revision-${revision.controlled_revision_id}`}
                  style={{
                    border: '1px solid #d7dde5',
                    borderRadius: 6,
                    padding: 12,
                    display: 'grid',
                    gap: 8,
                  }}
                >
                  <div>
                    <strong>{renderRevisionMeta(revision)}</strong>
                  </div>
                  <div>Change summary: {revision.change_summary || '-'}</div>
                  <div>Path: {revision.file_path}</div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {(STATUS_TRANSITIONS[revision.status] || []).map((status) => (
                      <button
                        key={status}
                        type="button"
                        data-testid={`document-control-transition-${revision.controlled_revision_id}-${status}`}
                        disabled={transitioningRevisionId === revision.controlled_revision_id}
                        onClick={() =>
                          handleTransitionRevision(revision.controlled_revision_id, status)
                        }
                        style={status === 'obsolete' ? dangerButtonStyle : secondaryButtonStyle}
                      >
                        Move to {status}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
              {selectedDocument && revisions.length === 0 ? (
                <div data-testid="document-control-no-revisions">No revisions yet.</div>
              ) : null}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
