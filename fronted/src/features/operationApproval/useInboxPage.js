import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { mapUserFacingErrorMessage } from '../../shared/errors/userFacingErrorMessages';
import operationApprovalApi from './api';
import { publishInboxUnreadCount } from '../notification/inboxUnreadSync';

const DEFAULT_LOAD_ERROR = '加载站内信失败';
const DEFAULT_UPDATE_ERROR = '更新站内信状态失败';
const DEFAULT_MARK_ALL_ERROR = '全部标记已读失败';

const resolveApprovalLink = (item) => {
  if (item?.link_path) return item.link_path;
  const requestId = String(item?.payload?.request_id || '').trim();
  return requestId ? `/approvals?request_id=${encodeURIComponent(requestId)}` : '/approvals';
};

export default function useInboxPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [items, setItems] = useState([]);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [busyId, setBusyId] = useState('');
  const [markAllBusy, setMarkAllBusy] = useState(false);
  const unreadCountRef = useRef(0);

  useEffect(() => {
    unreadCountRef.current = Number(unreadCount || 0);
  }, [unreadCount]);

  const syncUnreadCount = useCallback((valueOrUpdater) => {
    const base = Number(unreadCountRef.current || 0);
    const rawValue =
      typeof valueOrUpdater === 'function' ? valueOrUpdater(base) : valueOrUpdater;
    const numeric = Number(rawValue);
    const normalized = Number.isFinite(numeric) && numeric > 0 ? numeric : 0;
    unreadCountRef.current = normalized;
    setUnreadCount(normalized);
    publishInboxUnreadCount(normalized);
    return normalized;
  }, []);

  const loadData = useCallback(async (nextUnreadOnly = unreadOnly) => {
    setLoading(true);
    setError('');
    try {
      const response = await operationApprovalApi.listInbox({
        unreadOnly: nextUnreadOnly,
        limit: 100,
      });
      setItems(response.items);
      syncUnreadCount(response.unreadCount);
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, DEFAULT_LOAD_ERROR));
      setItems([]);
      syncUnreadCount(0);
    } finally {
      setLoading(false);
    }
  }, [syncUnreadCount, unreadOnly]);

  useEffect(() => {
    loadData(unreadOnly);
  }, [loadData, unreadOnly]);

  const handleMarkRead = useCallback(async (item) => {
    const inboxId = String(item?.inbox_id || '');
    if (!inboxId) return;

    setBusyId(inboxId);
    setError('');
    try {
      await operationApprovalApi.markInboxRead(inboxId);
      if (String(item?.status || '') === 'unread') {
        setItems((previous) => {
          if (unreadOnly) {
            return previous.filter((entry) => String(entry?.inbox_id || '') !== inboxId);
          }
          return previous.map((entry) => (
            String(entry?.inbox_id || '') === inboxId
              ? { ...entry, status: 'read' }
              : entry
          ));
        });
        syncUnreadCount((previous) => Math.max(0, Number(previous || 0) - 1));
      }
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, DEFAULT_UPDATE_ERROR));
    } finally {
      setBusyId('');
    }
  }, [syncUnreadCount, unreadOnly]);

  const handleOpen = useCallback(async (item) => {
    if (String(item?.status || '') === 'unread') {
      await handleMarkRead(item);
    }
    navigate(resolveApprovalLink(item));
  }, [handleMarkRead, navigate]);

  const handleMarkAllRead = useCallback(async () => {
    setMarkAllBusy(true);
    setError('');
    try {
      await operationApprovalApi.markAllInboxRead();
      setItems((previous) => (
        unreadOnly
          ? []
          : previous.map((entry) => ({ ...entry, status: 'read' }))
      ));
      syncUnreadCount(0);
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, DEFAULT_MARK_ALL_ERROR));
    } finally {
      setMarkAllBusy(false);
    }
  }, [syncUnreadCount, unreadOnly]);

  const toggleUnreadOnly = useCallback(() => {
    setUnreadOnly((previous) => !previous);
  }, []);

  return {
    loading,
    error,
    items,
    unreadOnly,
    unreadCount,
    busyId,
    markAllBusy,
    toggleUnreadOnly,
    handleMarkRead,
    handleOpen,
    handleMarkAllRead,
  };
}
