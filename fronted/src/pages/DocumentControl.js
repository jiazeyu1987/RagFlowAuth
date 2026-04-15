import React from 'react';
import PermissionGuard from '../components/PermissionGuard';
import { useAuth } from '../hooks/useAuth';
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

const prettyStatus = (value) => String(value || '-').replaceAll('_', ' ');

const renderRevisionMeta = (revision) => {
  if (!revision) return '-';
  return `v${revision.revision_no} · ${prettyStatus(revision.status)} · ${revision.filename}`;
};

export default function DocumentControl() {
  const { user, loading: authLoading, isAuthorized } = useAuth();

  const enableTraining =
    !authLoading &&
    !!user &&
    isAuthorized({
      anyPermissions: [
        { resource: 'training_ack', action: 'acknowledge' },
        { resource: 'training_ack', action: 'assign' },
      ],
    });
  const enableDepartmentAcks =
    !authLoading &&
    !!user &&
    isAuthorized({
      anyPermissions: [
        { resource: 'document_control', action: 'review' },
        { resource: 'document_control', action: 'publish' },
      ],
    });
  const enableRetention = !authLoading && !!user && isAuthorized({ permissionKey: 'canReview' });

  const {
    loading,
    detailLoading,
    savingDocument,
    savingRevision,
    workflowAction,
    workflowActionRevisionId,
    approvalDetailLoading,
    approvalDetail,
    approvalDetailError,
    trainingLoading,
    trainingGateLoading,
    trainingGate,
    trainingGateError,
    trainingAssignments,
    trainingError,
    trainingGenerateLoading,
    generatedTrainingAssignments,
    distributionDepartmentsLoading,
    distributionDepartmentIds,
    distributionDepartmentsError,
    departmentAcksLoading,
    departmentAcks,
    departmentAcksError,
    retentionLoading,
    retentionRecord,
    retentionError,
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
    handleSubmitRevisionForApproval,
    handleApproveRevisionStep,
    handleRejectRevisionStep,
    handleRemindOverdueApprovalStep,
    handleAddSignRevisionStep,
    handleSetTrainingGate,
    handleGenerateTrainingAssignments,
    handleSetDistributionDepartments,
    handlePublishRevision,
    handleCompleteManualReleaseArchive,
    handleConfirmDepartmentAck,
    handleRemindOverdueDepartmentAcks,
    handleInitiateObsolete,
    handleApproveObsolete,
    handleConfirmDestruction,
  } = useDocumentControlPage({
    mapErrorMessage: mapUserFacingErrorMessage,
    features: {
      enableTraining,
      enableDepartmentAcks,
      enableRetention,
    },
  });

  const [approvalNote, setApprovalNote] = React.useState('');
  const [addSignApproverUserId, setAddSignApproverUserId] = React.useState('');
  const [trainingRequired, setTrainingRequired] = React.useState(false);
  const [trainingAssigneeUserIds, setTrainingAssigneeUserIds] = React.useState('');
  const [trainingDepartmentIdsInput, setTrainingDepartmentIdsInput] = React.useState('');
  const [trainingMinReadMinutes, setTrainingMinReadMinutes] = React.useState('15');
  const [distributionDepartmentIdsInput, setDistributionDepartmentIdsInput] = React.useState('');
  const [releaseMode, setReleaseMode] = React.useState('manual_by_doc_control');
  const [obsoleteReason, setObsoleteReason] = React.useState('');
  const [obsoleteRetentionUntilMs, setObsoleteRetentionUntilMs] = React.useState('');
  const [destructionNotes, setDestructionNotes] = React.useState('');

  const workflowRevisionId = String(currentRevision?.controlled_revision_id || '');
  const workflowDocumentId = String(selectedDocument?.controlled_document_id || '');
  const normalizedApprovalNote = approvalNote.trim() ? approvalNote.trim() : null;
  const requiredApprovalAction =
    String(currentRevision?.current_approval_step_name || '').trim().toLowerCase() === 'approve'
      ? 'approve'
      : 'review';

  const pendingApproversText = React.useMemo(() => {
    const steps = Array.isArray(approvalDetail?.steps) ? approvalDetail.steps : [];
    const activeStep = steps.find((step) => String(step?.status || '') === 'active') || null;
    const approvers = Array.isArray(activeStep?.approvers) ? activeStep.approvers : [];
    const pending = approvers.filter((item) => String(item?.status || '') === 'pending');
    if (pending.length === 0) return '-';
    return pending
      .map((item) => item.approver_full_name || item.approver_username || item.approver_user_id || '-')
      .join(', ');
  }, [approvalDetail]);

  React.useEffect(() => {
    setTrainingRequired(Boolean(trainingGate?.training_required));
    setTrainingDepartmentIdsInput(
      Array.isArray(trainingGate?.department_ids) ? trainingGate.department_ids.join(', ') : ''
    );
  }, [trainingGate]);

  const changeControlLoading = departmentAcksLoading;
  const changeControlError = departmentAcksError;
  const changeControlRequests = React.useMemo(() => {
    if (!workflowRevisionId) return [];
    const requiredDepartments = (distributionDepartmentIds || []).map((item) => String(item));
    const confirmations = (departmentAcks || [])
      .filter((item) => String(item?.status || '') === 'confirmed')
      .map((item) => ({ department_code: String(item.department_id) }));
    return [
      {
        request_id: `doc-control-${workflowRevisionId}`,
        status: String(currentRevision?.status || '-'),
        title: selectedDocument?.title || selectedDocument?.doc_code || '-',
        required_departments: requiredDepartments,
        confirmations,
      },
    ];
  }, [currentRevision?.status, departmentAcks, distributionDepartmentIds, selectedDocument?.doc_code, selectedDocument?.title, workflowRevisionId]);

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
              <option value="approval_in_progress">approval_in_progress</option>
              <option value="approval_rejected">approval_rejected</option>
              <option value="approved_pending_effective">approved_pending_effective</option>
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
                  accept=".pdf,application/pdf"
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

          <section style={panelStyle} data-testid="document-control-workspace">
            <h2 style={{ marginTop: 0 }}>Workflow Workspace</h2>
            {!selectedDocument ? (
              <div style={{ color: '#6b7280' }}>Select a document to view its workflow workspace.</div>
            ) : !currentRevision ? (
              <div style={{ color: '#6b7280' }}>No current revision available.</div>
            ) : (
              <div style={{ display: 'grid', gap: 12 }}>
                <div>
                  <strong>{renderRevisionMeta(currentRevision)}</strong>
                </div>
                <div data-testid="document-control-workspace-status">
                  Status: {prettyStatus(currentRevision.status)}
                </div>

                <div data-testid="document-control-workspace-approval-summary" style={{ display: 'grid', gap: 6 }}>
                  <div>Approval request: {currentRevision.approval_request_id || '-'}</div>
                  <div>
                    Approval round:{' '}
                    {Number.isFinite(currentRevision.approval_round) ? currentRevision.approval_round : '-'}
                  </div>
                  <div>
                    Current step: {currentRevision.current_approval_step_name || '-'}
                    {currentRevision.current_approval_step_no ? ` (#${currentRevision.current_approval_step_no})` : ''}
                  </div>
                  {currentRevision.approval_request_id ? (
                    approvalDetailLoading ? (
                      <div data-testid="document-control-approval-detail-loading" style={{ color: '#6b7280' }}>
                        Loading approval detail...
                      </div>
                    ) : approvalDetailError ? (
                      <div data-testid="document-control-approval-detail-error" style={{ color: '#9f1239' }}>
                        {approvalDetailError}
                      </div>
                    ) : approvalDetail ? (
                      <div data-testid="document-control-approval-pending-approvers">
                        Pending approvers: {pendingApproversText}
                      </div>
                    ) : (
                      <div data-testid="document-control-approval-detail-empty" style={{ color: '#6b7280' }}>
                        Approval detail unavailable.
                      </div>
                    )
                  ) : null}
                </div>

                <label style={labelStyle}>
                  Note
                  <textarea
                    data-testid="document-control-approval-note"
                    style={{ ...inputStyle, minHeight: 72 }}
                    value={approvalNote}
                    onChange={(event) => setApprovalNote(event.target.value)}
                  />
                </label>

                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {['draft', 'approval_rejected'].includes(String(currentRevision.status || '')) ? (
                    <PermissionGuard permission={{ resource: 'document_control', action: 'create' }} fallback={null}>
                      <button
                        type="button"
                        data-testid="document-control-approval-submit"
                        disabled={workflowAction === 'submit' && workflowActionRevisionId === workflowRevisionId}
                        onClick={() =>
                          handleSubmitRevisionForApproval(workflowRevisionId, { note: normalizedApprovalNote })
                        }
                        style={primaryButtonStyle}
                      >
                        {workflowAction === 'submit' && workflowActionRevisionId === workflowRevisionId
                          ? 'Submitting...'
                          : 'Submit for approval'}
                      </button>
                    </PermissionGuard>
                  ) : null}

                  {String(currentRevision.status || '') === 'approval_in_progress' ? (
                    <>
                      <PermissionGuard
                        permission={{ resource: 'document_control', action: requiredApprovalAction }}
                        fallback={null}
                      >
                        <button
                          type="button"
                          data-testid="document-control-approval-approve"
                          disabled={workflowAction === 'approve' && workflowActionRevisionId === workflowRevisionId}
                          onClick={() =>
                            handleApproveRevisionStep(workflowRevisionId, { note: normalizedApprovalNote })
                          }
                          style={primaryButtonStyle}
                        >
                          {workflowAction === 'approve' && workflowActionRevisionId === workflowRevisionId
                            ? 'Approving...'
                            : 'Approve step'}
                        </button>
                      </PermissionGuard>
                      <PermissionGuard
                        permission={{ resource: 'document_control', action: requiredApprovalAction }}
                        fallback={null}
                      >
                        <button
                          type="button"
                          data-testid="document-control-approval-reject"
                          disabled={workflowAction === 'reject' && workflowActionRevisionId === workflowRevisionId}
                          onClick={() =>
                            handleRejectRevisionStep(workflowRevisionId, { note: normalizedApprovalNote })
                          }
                          style={dangerButtonStyle}
                        >
                          {workflowAction === 'reject' && workflowActionRevisionId === workflowRevisionId
                            ? 'Rejecting...'
                            : 'Reject step'}
                        </button>
                      </PermissionGuard>
                      <PermissionGuard
                        permission={{ resource: 'document_control', action: 'review' }}
                        fallback={null}
                      >
                        <button
                          type="button"
                          data-testid="document-control-approval-remind-overdue"
                          disabled={workflowAction === 'approval_remind' && workflowActionRevisionId === workflowRevisionId}
                          onClick={() =>
                            handleRemindOverdueApprovalStep(workflowRevisionId, { note: normalizedApprovalNote })
                          }
                          style={secondaryButtonStyle}
                        >
                          {workflowAction === 'approval_remind' && workflowActionRevisionId === workflowRevisionId
                            ? 'Sending...'
                            : 'Remind overdue approval'}
                        </button>
                      </PermissionGuard>
                    </>
                  ) : null}
                </div>

                {String(currentRevision.status || '') === 'approval_in_progress' ? (
                  <div style={{ display: 'grid', gap: 8 }}>
                    <label style={labelStyle}>
                      Add-sign approver user id
                      <input
                        data-testid="document-control-add-sign-user-id"
                        style={inputStyle}
                        value={addSignApproverUserId}
                        onChange={(event) => setAddSignApproverUserId(event.target.value)}
                      />
                    </label>
                    <PermissionGuard
                      permission={{ resource: 'document_control', action: requiredApprovalAction }}
                      fallback={null}
                    >
                      <button
                        type="button"
                        data-testid="document-control-add-sign-submit"
                        disabled={workflowAction === 'add_sign' && workflowActionRevisionId === workflowRevisionId}
                        onClick={() =>
                          handleAddSignRevisionStep(workflowRevisionId, {
                            approverUserId: addSignApproverUserId,
                            note: normalizedApprovalNote,
                          })
                        }
                        style={secondaryButtonStyle}
                      >
                        {workflowAction === 'add_sign' && workflowActionRevisionId === workflowRevisionId
                          ? 'Adding...'
                          : 'Add sign'}
                      </button>
                    </PermissionGuard>
                  </div>
                ) : null}

                <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: 12, display: 'grid', gap: 10 }}>
                  <div style={{ fontWeight: 700, color: '#0f172a' }}>Training</div>
                  <PermissionGuard
                    anyPermissions={[
                      { resource: 'training_ack', action: 'acknowledge' },
                      { resource: 'training_ack', action: 'assign' },
                    ]}
                    fallback={<div style={{ color: '#6b7280' }}>Training data is not visible for the current account.</div>}
                  >
                    {trainingGateLoading ? (
                      <div style={{ color: '#6b7280' }}>Loading training gate...</div>
                    ) : trainingGateError ? (
                      <div style={{ color: '#9f1239' }}>{trainingGateError}</div>
                    ) : trainingGate ? (
                      <div data-testid="document-control-training-gate" style={{ color: '#475569', fontSize: 13 }}>
                        Gate: {trainingGate.gate_status} · blocking={String(Boolean(trainingGate.blocking))}
                      </div>
                    ) : (
                      <div style={{ color: '#6b7280' }}>Training gate is not configured yet.</div>
                    )}

                    <PermissionGuard permission={{ resource: 'training_ack', action: 'assign' }} fallback={null}>
                      <div style={{ display: 'grid', gap: 8, marginTop: 10 }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#334155' }}>
                          <input
                            data-testid="document-control-training-required"
                            type="checkbox"
                            checked={trainingRequired}
                            onChange={(event) => setTrainingRequired(event.target.checked)}
                          />
                          Training required before publish
                        </label>
                        <label style={labelStyle}>
                          Training department ids (comma-separated)
                          <input
                            data-testid="document-control-training-departments"
                            style={inputStyle}
                            value={trainingDepartmentIdsInput}
                            onChange={(event) => setTrainingDepartmentIdsInput(event.target.value)}
                          />
                        </label>
                        <button
                          type="button"
                          data-testid="document-control-training-gate-save"
                          disabled={workflowAction === 'training_gate' && workflowActionRevisionId === workflowRevisionId}
                          onClick={() => {
                            const departmentIds = trainingDepartmentIdsInput
                              .split(/[,\\s]+/g)
                              .map((item) => Number(item))
                              .filter((item) => Number.isInteger(item) && item > 0);
                            handleSetTrainingGate(workflowRevisionId, {
                              trainingRequired,
                              departmentIds,
                            });
                          }}
                          style={secondaryButtonStyle}
                        >
                          {workflowAction === 'training_gate' && workflowActionRevisionId === workflowRevisionId
                            ? 'Saving...'
                            : 'Save training gate'}
                        </button>
                      </div>
                    </PermissionGuard>

                    {trainingLoading ? (
                      <div style={{ color: '#6b7280' }}>Loading training assignments...</div>
                    ) : trainingError ? (
                      <div style={{ color: '#9f1239' }}>{trainingError}</div>
                    ) : trainingAssignments.length === 0 ? (
                      <div style={{ color: '#6b7280' }}>No training assignments found for this revision (current user).</div>
                    ) : (
                      <div style={{ display: 'grid', gap: 6 }}>
                        {trainingAssignments.map((assignment) => (
                          <div
                            key={assignment.assignment_id}
                            style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: 10 }}
                          >
                            <div>
                              <strong>{assignment.status}</strong>{' '}
                              {assignment.decision ? `· decision=${assignment.decision}` : ''}
                            </div>
                            <div style={{ color: '#475569', fontSize: 13 }}>
                              Read: {Math.floor((assignment.read_progress_ms || 0) / 60000)} /{' '}
                              {Math.floor((assignment.required_read_ms || 0) / 60000)} min
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    <PermissionGuard permission={{ resource: 'training_ack', action: 'assign' }} fallback={null}>
                      <div style={{ display: 'grid', gap: 8, marginTop: 10 }}>
                        <label style={labelStyle}>
                          Assignee user ids (comma-separated)
                          <input
                            data-testid="document-control-training-assignees"
                            style={inputStyle}
                            value={trainingAssigneeUserIds}
                            onChange={(event) => setTrainingAssigneeUserIds(event.target.value)}
                          />
                        </label>
                        <label style={labelStyle}>
                          Department ids for assignment generation (comma-separated)
                          <input
                            data-testid="document-control-training-generate-departments"
                            style={inputStyle}
                            value={trainingDepartmentIdsInput}
                            onChange={(event) => setTrainingDepartmentIdsInput(event.target.value)}
                          />
                        </label>
                        <label style={labelStyle}>
                          Min read minutes
                          <input
                            data-testid="document-control-training-min-read-minutes"
                            type="number"
                            min="1"
                            style={inputStyle}
                            value={trainingMinReadMinutes}
                            onChange={(event) => setTrainingMinReadMinutes(event.target.value)}
                          />
                        </label>
                        <button
                          type="button"
                          data-testid="document-control-training-generate"
                          disabled={trainingGenerateLoading || !workflowRevisionId}
                          onClick={() => {
                            const assignees = trainingAssigneeUserIds
                              .split(/[,\\s]+/g)
                              .map((item) => item.trim())
                              .filter((item) => item.length > 0);
                            const departmentIds = trainingDepartmentIdsInput
                              .split(/[,\\s]+/g)
                              .map((item) => Number(item))
                              .filter((item) => Number.isInteger(item) && item > 0);
                            const minutes = Number(trainingMinReadMinutes);
                            handleGenerateTrainingAssignments(workflowRevisionId, {
                              assigneeUserIds: assignees,
                              departmentIds,
                              minReadMinutes: minutes,
                              note: normalizedApprovalNote,
                            });
                          }}
                          style={secondaryButtonStyle}
                        >
                          {trainingGenerateLoading ? 'Generating...' : 'Generate training assignments'}
                        </button>
                        {Array.isArray(generatedTrainingAssignments) && generatedTrainingAssignments.length > 0 ? (
                          <div data-testid="document-control-training-generated" style={{ color: '#475569' }}>
                            Generated: {generatedTrainingAssignments.length}
                          </div>
                        ) : null}
                      </div>
                    </PermissionGuard>
                  </PermissionGuard>
                </div>

                <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: 12, display: 'grid', gap: 10 }}>
                  <div style={{ fontWeight: 700, color: '#0f172a' }}>Distribution / Publish Controls</div>
                  <label style={labelStyle}>
                    Distribution department ids (comma-separated)
                    <input
                      data-testid="document-control-distribution-departments"
                      style={inputStyle}
                      value={distributionDepartmentIdsInput}
                      onChange={(event) => setDistributionDepartmentIdsInput(event.target.value)}
                      placeholder={(distributionDepartmentIds || []).join(', ')}
                    />
                  </label>
                  <div style={{ color: '#475569', fontSize: 13 }}>
                    Current departments:{' '}
                    {distributionDepartmentsLoading
                      ? 'loading...'
                      : distributionDepartmentIds.length > 0
                        ? distributionDepartmentIds.join(', ')
                        : '-'}
                  </div>
                  {distributionDepartmentsError ? (
                    <div style={{ color: '#9f1239' }}>{distributionDepartmentsError}</div>
                  ) : null}
                  <PermissionGuard permission={{ resource: 'document_control', action: 'review' }} fallback={null}>
                    <button
                      type="button"
                      data-testid="document-control-distribution-save"
                      disabled={workflowAction === 'set_distribution' && workflowActionRevisionId === workflowDocumentId}
                      onClick={() => {
                        const departmentIds = distributionDepartmentIdsInput
                          .split(/[,\\s]+/g)
                          .map((item) => Number(item))
                          .filter((item) => Number.isInteger(item) && item > 0);
                        handleSetDistributionDepartments(workflowDocumentId, { departmentIds });
                      }}
                      style={secondaryButtonStyle}
                    >
                      {workflowAction === 'set_distribution' && workflowActionRevisionId === workflowDocumentId
                        ? 'Saving...'
                        : 'Save distribution departments'}
                    </button>
                  </PermissionGuard>

                  {String(currentRevision?.status || '') === 'approved_pending_effective' ? (
                    <div style={{ display: 'grid', gap: 8 }}>
                      <label style={labelStyle}>
                        Release mode
                        <select
                          data-testid="document-control-release-mode"
                          style={inputStyle}
                          value={releaseMode}
                          onChange={(event) => setReleaseMode(event.target.value)}
                        >
                          <option value="manual_by_doc_control">manual_by_doc_control</option>
                          <option value="automatic">automatic</option>
                        </select>
                      </label>
                      <PermissionGuard permission={{ resource: 'document_control', action: 'publish' }} fallback={null}>
                        <button
                          type="button"
                          data-testid="document-control-publish"
                          disabled={workflowAction === 'publish' && workflowActionRevisionId === workflowRevisionId}
                          onClick={() =>
                            handlePublishRevision(workflowRevisionId, {
                              releaseMode,
                              note: normalizedApprovalNote,
                            })
                          }
                          style={primaryButtonStyle}
                        >
                          {workflowAction === 'publish' && workflowActionRevisionId === workflowRevisionId
                            ? 'Publishing...'
                            : 'Publish revision'}
                        </button>
                      </PermissionGuard>
                    </div>
                  ) : null}

                  {String(currentRevision?.status || '') === 'effective' &&
                  String(currentRevision?.release_mode || '') === 'manual_by_doc_control' &&
                  !currentRevision?.release_manual_archive_completed_at_ms ? (
                    <PermissionGuard permission={{ resource: 'document_control', action: 'publish' }} fallback={null}>
                      <button
                        type="button"
                        data-testid="document-control-manual-release-complete"
                        disabled={workflowAction === 'manual_release_complete' && workflowActionRevisionId === workflowRevisionId}
                        onClick={() =>
                          handleCompleteManualReleaseArchive(workflowRevisionId, {
                            note: normalizedApprovalNote,
                          })
                        }
                        style={secondaryButtonStyle}
                      >
                        {workflowAction === 'manual_release_complete' && workflowActionRevisionId === workflowRevisionId
                          ? 'Completing...'
                          : 'Complete manual archive release'}
                      </button>
                    </PermissionGuard>
                  ) : null}
                </div>

                <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: 12, display: 'grid', gap: 10 }}>
                  <div style={{ fontWeight: 700, color: '#0f172a' }}>Release / Department Acknowledgment</div>
                  <PermissionGuard
                    permission={{ resource: 'change_control', action: 'evaluate' }}
                    fallback={<div style={{ color: '#6b7280' }}>Change-control data is not visible for the current account.</div>}
                  >
                    {changeControlLoading ? (
                      <div style={{ color: '#6b7280' }}>Loading change-control requests...</div>
                    ) : changeControlError ? (
                      <div style={{ color: '#9f1239' }}>{changeControlError}</div>
                    ) : changeControlRequests.length === 0 ? (
                      <div style={{ color: '#6b7280' }}>No related change-control requests.</div>
                    ) : (
                      <div style={{ display: 'grid', gap: 8 }}>
                        {changeControlRequests.map((req) => {
                          const required = Array.isArray(req.required_departments) ? req.required_departments : [];
                          const confirmations = Array.isArray(req.confirmations) ? req.confirmations : [];
                          const confirmed = new Set(
                            confirmations.map((c) => String(c.department_code || '').trim()).filter(Boolean)
                          );
                          const pending = required.filter((dept) => !confirmed.has(String(dept || '').trim()));
                          return (
                            <div
                              key={req.request_id}
                              style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: 10 }}
                            >
                              <div>
                                <strong>{req.request_id}</strong> · {req.status}
                              </div>
                              <div style={{ color: '#475569', fontSize: 13 }}>{req.title || '-'}</div>
                              <div style={{ color: '#475569', fontSize: 13 }}>
                                Departments: {confirmed.size}/{required.length}
                                {pending.length > 0 ? ` (pending: ${pending.join(', ')})` : ''}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </PermissionGuard>
                  {departmentAcks.length > 0 ? (
                    <div style={{ display: 'grid', gap: 8 }}>
                      {departmentAcks.map((ack) =>
                        ack.status !== 'confirmed' ? (
                          <PermissionGuard
                            key={ack.ack_id}
                            permission={{ resource: 'document_control', action: 'review' }}
                            fallback={null}
                          >
                            <button
                              type="button"
                              data-testid={`document-control-department-ack-confirm-${ack.department_id}`}
                              disabled={
                                workflowAction === 'department_ack_confirm' &&
                                workflowActionRevisionId === `${workflowRevisionId}:${ack.department_id}`
                              }
                              onClick={() =>
                                handleConfirmDepartmentAck(workflowRevisionId, ack.department_id, {
                                  notes: normalizedApprovalNote,
                                })
                              }
                              style={secondaryButtonStyle}
                            >
                              Confirm acknowledgment for Dept {ack.department_id}
                            </button>
                          </PermissionGuard>
                        ) : null
                      )}
                      <PermissionGuard permission={{ resource: 'document_control', action: 'publish' }} fallback={null}>
                        <button
                          type="button"
                          data-testid="document-control-department-ack-remind"
                          disabled={workflowAction === 'department_ack_remind' && workflowActionRevisionId === workflowRevisionId}
                          onClick={() =>
                            handleRemindOverdueDepartmentAcks(workflowRevisionId, { note: normalizedApprovalNote })
                          }
                          style={secondaryButtonStyle}
                        >
                          {workflowAction === 'department_ack_remind' && workflowActionRevisionId === workflowRevisionId
                            ? 'Sending...'
                            : 'Remind overdue acknowledgments'}
                        </button>
                      </PermissionGuard>
                    </div>
                  ) : null}
                </div>

                <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: 12, display: 'grid', gap: 10 }}>
                  <div style={{ fontWeight: 700, color: '#0f172a' }}>Obsolete / Retention</div>
                  <PermissionGuard
                    permissionKey="canReview"
                    fallback={<div style={{ color: '#6b7280' }}>Retention data is not visible for the current account.</div>}
                  >
                    {String(currentRevision.status || '') === 'effective' ? (
                      <div style={{ display: 'grid', gap: 8 }}>
                        <label style={labelStyle}>
                          Obsolete reason
                          <input
                            data-testid="document-control-obsolete-reason"
                            style={inputStyle}
                            value={obsoleteReason}
                            onChange={(event) => setObsoleteReason(event.target.value)}
                          />
                        </label>
                        <label style={labelStyle}>
                          Retention until ms
                          <input
                            data-testid="document-control-obsolete-retention-until-ms"
                            style={inputStyle}
                            value={obsoleteRetentionUntilMs}
                            onChange={(event) => setObsoleteRetentionUntilMs(event.target.value)}
                          />
                        </label>
                        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                          <PermissionGuard permission={{ resource: 'document_control', action: 'obsolete' }} fallback={null}>
                            <button
                              type="button"
                              data-testid="document-control-obsolete-initiate"
                              disabled={workflowAction === 'obsolete_initiate' && workflowActionRevisionId === workflowRevisionId}
                              onClick={() =>
                                handleInitiateObsolete(workflowRevisionId, {
                                  retirementReason: obsoleteReason,
                                  retentionUntilMs: Number(obsoleteRetentionUntilMs),
                                  note: normalizedApprovalNote,
                                })
                              }
                              style={dangerButtonStyle}
                            >
                              Initiate obsolete
                            </button>
                          </PermissionGuard>
                          {currentRevision?.obsolete_requested_at_ms && !currentRevision?.obsolete_approved_at_ms ? (
                            <PermissionGuard permission={{ resource: 'document_control', action: 'obsolete' }} fallback={null}>
                              <button
                                type="button"
                                data-testid="document-control-obsolete-approve"
                                disabled={workflowAction === 'obsolete_approve' && workflowActionRevisionId === workflowRevisionId}
                                onClick={() =>
                                  handleApproveObsolete(workflowRevisionId, {
                                    note: normalizedApprovalNote,
                                  })
                                }
                                style={secondaryButtonStyle}
                              >
                                Approve obsolete
                              </button>
                            </PermissionGuard>
                          ) : null}
                        </div>
                      </div>
                    ) : null}
                    {String(currentRevision.status || '') !== 'obsolete' ? (
                      <div style={{ color: '#6b7280' }}>Retention applies once a revision is obsolete.</div>
                    ) : retentionLoading ? (
                      <div style={{ color: '#6b7280' }}>Loading retention record...</div>
                    ) : retentionError ? (
                      <div style={{ color: '#9f1239' }}>{retentionError}</div>
                    ) : retentionRecord ? (
                      <div data-testid="document-control-retention-record" style={{ display: 'grid', gap: 6 }}>
                        <div>Doc ID: {retentionRecord.doc_id}</div>
                        <div>Filename: {retentionRecord.filename}</div>
                        <div>Retention until: {retentionRecord.retention_until_ms || '-'}</div>
                        <div>Reason: {retentionRecord.retirement_reason || '-'}</div>
                      </div>
                    ) : (
                      <div style={{ color: '#6b7280' }}>No retired record found for this revision.</div>
                    )}
                    {String(currentRevision.status || '') === 'obsolete' ? (
                      <div style={{ display: 'grid', gap: 8 }}>
                        <label style={labelStyle}>
                          Destruction confirmation notes
                          <textarea
                            data-testid="document-control-destruction-notes"
                            style={{ ...inputStyle, minHeight: 72 }}
                            value={destructionNotes}
                            onChange={(event) => setDestructionNotes(event.target.value)}
                          />
                        </label>
                        <PermissionGuard permission={{ resource: 'document_control', action: 'obsolete' }} fallback={null}>
                          <button
                            type="button"
                            data-testid="document-control-destruction-confirm"
                            disabled={workflowAction === 'destruction_confirm' && workflowActionRevisionId === workflowRevisionId}
                            onClick={() =>
                              handleConfirmDestruction(workflowRevisionId, {
                                destructionNotes,
                              })
                            }
                            style={dangerButtonStyle}
                          >
                            Confirm destruction
                          </button>
                        </PermissionGuard>
                      </div>
                    ) : null}
                  </PermissionGuard>
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
                  accept=".pdf,application/pdf"
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
                  {revision.approval_request_id ? (
                    <div style={{ color: '#475569' }}>
                      Approval request: {revision.approval_request_id} · Step:{' '}
                      {revision.current_approval_step_name || '-'}
                    </div>
                  ) : null}
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
