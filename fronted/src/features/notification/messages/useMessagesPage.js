import { useCallback, useEffect, useRef, useState } from 'react';
import { notificationApi } from '../api';
import { publishInboxUnreadCount } from '../inboxUnreadSync';

export default function useMessagesPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [busyMap, setBusyMap] = useState({});
  const [markAllBusy, setMarkAllBusy] = useState(false);
  const unreadCountRef = useRef(0);

  useEffect(() => {
    unreadCountRef.current = Number(unreadCount || 0);
  }, [unreadCount]);

  const syncUnreadCount = useCallback((valueOrUpdater) => {
    const base = Number(unreadCountRef.current || 0);
    const rawValue = typeof valueOrUpdater === 'function' ? valueOrUpdater(base) : valueOrUpdater;
    const normalized = Number.isFinite(Number(rawValue)) && Number(rawValue) > 0 ? Number(rawValue) : 0;
    unreadCountRef.current = normalized;
    setUnreadCount(normalized);
    publishInboxUnreadCount(normalized);
    return normalized;
  }, []);

  const loadData = useCallback(async (opts = {}) => {
    const onlyUnread = Object.prototype.hasOwnProperty.call(opts, 'unreadOnly') ? !!opts.unreadOnly : unreadOnly;
    setError('');
    setLoading(true);
    try {
      const res = await notificationApi.listMyMessages({ limit: 100, offset: 0, unreadOnly: onlyUnread });
      setItems(Array.isArray(res.items) ? res.items : []);
      setTotal(Number(res.total || 0));
      syncUnreadCount(Number(res.unread_count || 0));
    } catch (e) {
      setError(e.message || '加载站内信失败');
    } finally {
      setLoading(false);
    }
  }, [syncUnreadCount, unreadOnly]);

  useEffect(() => {
    loadData({ unreadOnly });
  }, [loadData, unreadOnly]);

  const setRowBusy = useCallback((jobId, busy) => {
    setBusyMap((prev) => ({ ...prev, [String(jobId)]: !!busy }));
  }, []);

  const handleToggleUnreadOnly = useCallback(() => {
    setUnreadOnly((value) => !value);
  }, []);

  const handleToggleRead = useCallback(async (item) => {
    const jobId = item.job_id;
    const nextRead = !item.read_at_ms;
    setError('');
    setRowBusy(jobId, true);
    try {
      await notificationApi.updateMyMessageReadState(jobId, nextRead);
      setItems((prev) => {
        if (unreadOnly && nextRead) {
          return prev.filter((entry) => entry.job_id !== jobId);
        }
        return prev.map((entry) => (
          entry.job_id === jobId
            ? { ...entry, read_at_ms: nextRead ? Date.now() : null }
            : entry
        ));
      });
      syncUnreadCount((prev) => Math.max(0, Number(prev || 0) + (nextRead ? -1 : 1)));
      if (unreadOnly && nextRead) {
        setTotal((prev) => Math.max(0, Number(prev || 0) - 1));
      }
    } catch (e) {
      setError(e.message || '更新读取状态失败');
    } finally {
      setRowBusy(jobId, false);
    }
  }, [setRowBusy, syncUnreadCount, unreadOnly]);

  const handleMarkAllRead = useCallback(async () => {
    setError('');
    setMarkAllBusy(true);
    try {
      await notificationApi.markAllMyMessagesRead();
      setItems((prev) => (
        unreadOnly
          ? []
          : prev.map((entry) => ({ ...entry, read_at_ms: entry.read_at_ms || Date.now() }))
      ));
      syncUnreadCount(0);
      if (unreadOnly) {
        setTotal(0);
      }
    } catch (e) {
      setError(e.message || '全部标记已读失败');
    } finally {
      setMarkAllBusy(false);
    }
  }, [syncUnreadCount, unreadOnly]);

  return {
    loading,
    error,
    items,
    total,
    unreadCount,
    unreadOnly,
    busyMap,
    markAllBusy,
    handleToggleUnreadOnly,
    handleToggleRead,
    handleMarkAllRead,
  };
}
