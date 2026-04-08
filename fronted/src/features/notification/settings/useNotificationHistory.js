import { useCallback, useEffect, useRef, useState } from 'react';
import { notificationApi } from '../api';
import { INITIAL_HISTORY_FILTERS } from './constants';

export default function useNotificationHistory() {
  const [historyLoading, setHistoryLoading] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [logsByJob, setLogsByJob] = useState({});
  const [expandedLogs, setExpandedLogs] = useState({});
  const [historyFilters, setHistoryFilters] = useState(INITIAL_HISTORY_FILTERS);
  const historyFiltersRef = useRef(INITIAL_HISTORY_FILTERS);

  useEffect(() => {
    historyFiltersRef.current = historyFilters;
  }, [historyFilters]);

  const loadHistory = useCallback(async (filters = historyFiltersRef.current) => {
    setHistoryLoading(true);
    try {
      const response = await notificationApi.listJobs({
        limit: 100,
        eventType: filters.eventType,
        channelType: filters.channelType,
        status: filters.status,
      });
      setJobs(response.items);
      return response.items;
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const setHistoryFilter = useCallback((field, value) => {
    setHistoryFilters((prev) => ({ ...prev, [field]: value }));
  }, []);

  const resetHistoryFilters = useCallback(async () => {
    setHistoryFilters(INITIAL_HISTORY_FILTERS);
    await loadHistory(INITIAL_HISTORY_FILTERS);
  }, [loadHistory]);

  const toggleLogs = useCallback(async (jobId) => {
    const key = String(jobId);
    if (expandedLogs[key]) {
      setExpandedLogs((prev) => ({ ...prev, [key]: false }));
      return;
    }
    if (!logsByJob[key]) {
      const items = await notificationApi.listJobLogs(jobId, 20);
      setLogsByJob((prev) => ({ ...prev, [key]: items }));
    }
    setExpandedLogs((prev) => ({ ...prev, [key]: true }));
  }, [expandedLogs, logsByJob]);

  const retryJob = useCallback((jobId) => notificationApi.retryJob(jobId), []);
  const resendJob = useCallback((jobId) => notificationApi.resendJob(jobId), []);
  const dispatchPending = useCallback((limit = 100) => notificationApi.dispatchPending(limit), []);

  return {
    historyLoading,
    jobs,
    logsByJob,
    expandedLogs,
    historyFilters,
    loadHistory,
    setHistoryFilter,
    resetHistoryFilters,
    toggleLogs,
    retryJob,
    resendJob,
    dispatchPending,
    historyFiltersRef,
  };
}
