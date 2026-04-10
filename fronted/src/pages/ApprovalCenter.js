import React from 'react';
import SignatureConfirmModal from '../features/operationApproval/components/SignatureConfirmModal';
import ApprovalCenterAlert from '../features/operationApproval/components/ApprovalCenterAlert';
import ApprovalRequestDetailPanel from '../features/operationApproval/components/ApprovalRequestDetailPanel';
import ApprovalRequestListPanel from '../features/operationApproval/components/ApprovalRequestListPanel';
import documentsApi from '../features/documents/api';
import {
  getOperationLabel,
} from '../features/operationApproval/approvalCenterConfig';
import useApprovalCenterPage from '../features/operationApproval/useApprovalCenterPage';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';

export default function ApprovalCenter() {
  const {
    user,
    view,
    statusFilter,
    items,
    loading,
    error,
    selectedRequestId,
    detail,
    detailLoading,
    actionLoading,
    currentPendingApprover,
    withdrawable,
    visibleSummaryEntries,
    previewableSummaryKeys,
    visibleEvents,
    summaryPreviewTarget,
    showTrainingHelp,
    currentUserLabel,
    trainingRecordPath,
    trainingCertificationPath,
    closeSignaturePrompt,
    closeSummaryPreview,
    signatureError,
    signaturePrompt,
    signatureSubmitting,
    submitSignaturePrompt,
    refreshList,
    handleChangeView,
    handleChangeStatus,
    handlePreviewSummaryEntry,
    handleSelectRequest,
    handleSignedAction,
    handleWithdraw,
  } = useApprovalCenterPage({
    getOperationLabel,
  });

  return (
    <div style={{ display: 'grid', gap: '16px' }} data-testid="approval-center-page">
      <SignatureConfirmModal
        prompt={signaturePrompt}
        submitting={signatureSubmitting}
        error={signatureError}
        onClose={closeSignaturePrompt}
        onSubmit={submitSignaturePrompt}
      />
      <DocumentPreviewModal
        open={Boolean(summaryPreviewTarget)}
        target={summaryPreviewTarget}
        onClose={closeSummaryPreview}
        canDownloadFiles={false}
        documentApi={documentsApi}
      />

      <ApprovalCenterAlert
        error={error}
        showTrainingHelp={showTrainingHelp}
        currentUserLabel={currentUserLabel}
        userRole={user?.role}
        trainingRecordPath={trainingRecordPath}
        trainingCertificationPath={trainingCertificationPath}
      />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(320px, 420px) minmax(0, 1fr)',
          gap: '16px',
        }}
      >
        <ApprovalRequestListPanel
          view={view}
          statusFilter={statusFilter}
          items={items}
          loading={loading}
          selectedRequestId={selectedRequestId}
          refreshList={refreshList}
          handleChangeView={handleChangeView}
          handleChangeStatus={handleChangeStatus}
          handleSelectRequest={handleSelectRequest}
        />

        <ApprovalRequestDetailPanel
          selectedRequestId={selectedRequestId}
          detail={detail}
          detailLoading={detailLoading}
          actionLoading={actionLoading}
          currentPendingApprover={currentPendingApprover}
          withdrawable={withdrawable}
          visibleSummaryEntries={visibleSummaryEntries}
          previewableSummaryKeys={previewableSummaryKeys}
          visibleEvents={visibleEvents}
          handlePreviewSummaryEntry={handlePreviewSummaryEntry}
          handleSignedAction={handleSignedAction}
          handleWithdraw={handleWithdraw}
        />
      </div>
    </div>
  );
}
