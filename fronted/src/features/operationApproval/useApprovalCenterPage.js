import { useMemo } from 'react';
import {
  TRAINING_COMPLIANCE_ERROR_CODES,
  buildTrainingCompliancePath,
  canWithdraw,
  getVisibleEvents,
  getVisibleSummaryEntries,
  isCurrentPendingApprover,
} from './approvalCenterHelpers';
import useApprovalCenterActions from './useApprovalCenterActions';
import useApprovalCenterData from './useApprovalCenterData';
import useApprovalCenterQueryState from './useApprovalCenterQueryState';
import { useSignaturePrompt } from './useSignaturePrompt';
import { useAuth } from '../../hooks/useAuth';
import { getDisplayName } from '../../shared/users/displayName';

export default function useApprovalCenterPage({ getOperationLabel }) {
  const { user } = useAuth();
  const queryState = useApprovalCenterQueryState();
  const {
    view,
    statusFilter,
    selectedRequestId,
    handleChangeView,
    handleChangeStatus,
    handleSelectRequest,
  } = queryState;
  const {
    items,
    loading,
    error,
    errorCode,
    detail,
    detailLoading,
    refreshList,
    refreshDetail,
    setError,
    setErrorCode,
  } = useApprovalCenterData(queryState);
  const {
    closeSignaturePrompt,
    promptSignature,
    signatureError,
    signaturePrompt,
    signatureSubmitting,
    submitSignaturePrompt,
  } = useSignaturePrompt();
  const {
    actionLoading,
    handleSignedAction,
    handleWithdraw,
  } = useApprovalCenterActions({
    detail,
    getOperationLabel,
    promptSignature,
    refreshDetail,
    refreshList,
    setError,
    setErrorCode,
    statusFilter,
    view,
  });

  const currentPendingApprover = useMemo(
    () => isCurrentPendingApprover(detail, user?.user_id),
    [detail, user?.user_id]
  );
  const withdrawable = useMemo(() => canWithdraw(detail, user), [detail, user]);
  const visibleSummaryEntries = useMemo(
    () => getVisibleSummaryEntries(detail?.summary),
    [detail?.summary]
  );
  const visibleEvents = useMemo(() => getVisibleEvents(detail?.events), [detail?.events]);
  const showTrainingHelp = TRAINING_COMPLIANCE_ERROR_CODES.has(String(errorCode || '').trim());
  const currentUserLabel = getDisplayName(user);
  const trainingRecordPath = buildTrainingCompliancePath({
    tab: 'records',
    userId: user?.user_id,
  });
  const trainingCertificationPath = buildTrainingCompliancePath({
    tab: 'certifications',
    userId: user?.user_id,
  });

  return {
    user,
    view,
    statusFilter,
    items,
    loading,
    error,
    errorCode,
    selectedRequestId,
    detail,
    detailLoading,
    actionLoading,
    currentPendingApprover,
    withdrawable,
    visibleSummaryEntries,
    visibleEvents,
    showTrainingHelp,
    currentUserLabel,
    trainingRecordPath,
    trainingCertificationPath,
    closeSignaturePrompt,
    signatureError,
    signaturePrompt,
    signatureSubmitting,
    submitSignaturePrompt,
    refreshList,
    handleChangeView,
    handleChangeStatus,
    handleSelectRequest,
    handleSignedAction,
    handleWithdraw,
  };
}
