import { useCallback, useState } from 'react';
import operationApprovalApi from './api';
import {
  buildSignaturePrompt,
  mapApprovalCenterErrorMessage,
} from './approvalCenterHelpers';

export default function useApprovalCenterActions({
  detail,
  getOperationLabel,
  promptSignature,
  refreshDetail,
  refreshList,
  setError,
  setErrorCode,
  statusFilter,
  view,
}) {
  const [actionLoading, setActionLoading] = useState('');

  const clearError = useCallback(() => {
    setError('');
    setErrorCode('');
  }, [setError, setErrorCode]);

  const applyError = useCallback(
    (requestError, fallbackMessage) => {
      const nextErrorCode = String(requestError?.message || '').trim();
      setErrorCode(nextErrorCode);
      setError(mapApprovalCenterErrorMessage(nextErrorCode || fallbackMessage));
    },
    [setError, setErrorCode]
  );

  const handleSignedAction = useCallback(
    async (action) => {
      if (!detail?.request_id) {
        return;
      }

      const signaturePayload = await promptSignature(
        buildSignaturePrompt(action, detail, getOperationLabel)
      );
      if (!signaturePayload) {
        return;
      }

      setActionLoading(action);
      clearError();
      try {
        if (action === 'approve') {
          await operationApprovalApi.approveRequest(detail.request_id, {
            ...signaturePayload,
            notes: signaturePayload.signature_reason,
          });
        } else {
          await operationApprovalApi.rejectRequest(detail.request_id, {
            ...signaturePayload,
            notes: signaturePayload.signature_reason,
          });
        }
        await refreshList(view, statusFilter);
        await refreshDetail(detail.request_id);
      } catch (requestError) {
        applyError(
          requestError,
          `处理${action === 'approve' ? '通过' : '驳回'}失败`
        );
      } finally {
        setActionLoading('');
      }
    },
    [
      applyError,
      clearError,
      detail,
      getOperationLabel,
      promptSignature,
      refreshDetail,
      refreshList,
      statusFilter,
      view,
    ]
  );

  const handleWithdraw = useCallback(async () => {
    if (!detail?.request_id) {
      return;
    }

    const reason = window.prompt('请输入撤回原因（可留空）', '') ?? '';
    setActionLoading('withdraw');
    clearError();
    try {
      await operationApprovalApi.withdrawRequest(detail.request_id, {
        reason: String(reason || '').trim() || null,
      });
      await refreshList(view, statusFilter);
      await refreshDetail(detail.request_id);
    } catch (requestError) {
      applyError(requestError, '撤回申请失败');
    } finally {
      setActionLoading('');
    }
  }, [applyError, clearError, detail, refreshDetail, refreshList, statusFilter, view]);

  return {
    actionLoading,
    handleSignedAction,
    handleWithdraw,
  };
}
