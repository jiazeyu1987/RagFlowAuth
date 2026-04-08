import { useCallback, useEffect, useState } from 'react';
import operationApprovalApi from './api';
import { mapApprovalCenterErrorMessage } from './approvalCenterHelpers';

export default function useApprovalCenterData({
  view,
  statusFilter,
  selectedRequestId,
  selectedRequestIdRef,
  setSelectedRequestId,
  updateQuery,
}) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [errorCode, setErrorCode] = useState('');
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const applyError = useCallback((requestError, fallbackMessage) => {
    const nextErrorCode = String(requestError?.message || '').trim();
    setErrorCode(nextErrorCode);
    setError(mapApprovalCenterErrorMessage(nextErrorCode || fallbackMessage));
  }, []);

  const clearError = useCallback(() => {
    setError('');
    setErrorCode('');
  }, []);

  const refreshList = useCallback(
    async (nextView = view, nextStatus = statusFilter) => {
      setLoading(true);
      clearError();
      try {
        const nextItems = await operationApprovalApi.listRequests({
          view: nextView,
          status: nextStatus,
          limit: 100,
        });
        setItems(nextItems);

        const currentSelectedRequestId = String(selectedRequestIdRef.current || '');
        const stillExists = nextItems.some(
          (item) => String(item?.request_id || '') === currentSelectedRequestId
        );
        const nextRequestId = stillExists
          ? currentSelectedRequestId
          : String(nextItems[0]?.request_id || '');

        setSelectedRequestId(nextRequestId);
        updateQuery(nextView, nextStatus, nextRequestId);
        if (!nextRequestId) {
          setDetail(null);
        }
      } catch (requestError) {
        setItems([]);
        setDetail(null);
        setSelectedRequestId('');
        applyError(requestError, '加载审批申请失败');
      } finally {
        setLoading(false);
      }
    },
    [applyError, clearError, selectedRequestIdRef, setSelectedRequestId, statusFilter, updateQuery, view]
  );

  const refreshDetail = useCallback(
    async (requestId) => {
      const nextRequestId = String(requestId || '');
      if (!nextRequestId) {
        setDetail(null);
        return;
      }

      setDetailLoading(true);
      clearError();
      try {
        setDetail(await operationApprovalApi.getRequest(nextRequestId));
      } catch (requestError) {
        setDetail(null);
        applyError(requestError, '加载审批详情失败');
      } finally {
        setDetailLoading(false);
      }
    },
    [applyError, clearError]
  );

  useEffect(() => {
    refreshList(view, statusFilter);
  }, [refreshList, statusFilter, view]);

  useEffect(() => {
    refreshDetail(selectedRequestId);
  }, [refreshDetail, selectedRequestId]);

  return {
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
  };
}
