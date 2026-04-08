import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { parseView } from './approvalCenterHelpers';

export default function useApprovalCenterQueryState() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [view, setView] = useState(() => parseView(searchParams.get('view')));
  const [statusFilter, setStatusFilter] = useState(() => searchParams.get('status') || 'all');
  const [selectedRequestId, setSelectedRequestId] = useState(
    () => searchParams.get('request_id') || ''
  );
  const selectedRequestIdRef = useRef(selectedRequestId);

  useEffect(() => {
    selectedRequestIdRef.current = selectedRequestId;
  }, [selectedRequestId]);

  const updateQuery = useCallback(
    (nextView, nextStatus, nextRequestId) => {
      const params = new URLSearchParams();
      if (nextView && nextView !== 'todo') {
        params.set('view', nextView);
      }
      if (nextStatus && nextStatus !== 'all') {
        params.set('status', nextStatus);
      }
      if (nextRequestId) {
        params.set('request_id', nextRequestId);
      }
      setSearchParams(params);
    },
    [setSearchParams]
  );

  useEffect(() => {
    const nextView = parseView(searchParams.get('view'));
    if (nextView !== view) {
      setView(nextView);
    }

    const nextStatus = searchParams.get('status') || 'all';
    if (nextStatus !== statusFilter) {
      setStatusFilter(nextStatus);
    }

    const nextRequestId = searchParams.get('request_id') || '';
    if (nextRequestId !== selectedRequestId) {
      setSelectedRequestId(nextRequestId);
    }
  }, [searchParams, selectedRequestId, statusFilter, view]);

  const handleChangeView = useCallback(
    (nextView) => {
      const cleanView = parseView(nextView);
      setView(cleanView);
      setSelectedRequestId('');
      updateQuery(cleanView, statusFilter, '');
    },
    [statusFilter, updateQuery]
  );

  const handleChangeStatus = useCallback(
    (nextStatus) => {
      const cleanStatus = String(nextStatus || 'all');
      setStatusFilter(cleanStatus);
      setSelectedRequestId('');
      updateQuery(view, cleanStatus, '');
    },
    [updateQuery, view]
  );

  const handleSelectRequest = useCallback(
    (requestId) => {
      const nextRequestId = String(requestId || '');
      setSelectedRequestId(nextRequestId);
      updateQuery(view, statusFilter, nextRequestId);
    },
    [statusFilter, updateQuery, view]
  );

  return {
    view,
    statusFilter,
    selectedRequestId,
    selectedRequestIdRef,
    setSelectedRequestId,
    updateQuery,
    handleChangeView,
    handleChangeStatus,
    handleSelectRequest,
  };
}
