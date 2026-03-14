import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authClient from '../api/authClient';
import ResearchWorkbenchShell from '../features/researchWorkbench/components/ResearchWorkbenchShell';

const STATUS_META = {
  pending: { label: 'Pending', text: '#075985', background: '#e0f2fe' },
  running: { label: 'Running', text: '#1d4ed8', background: '#dbeafe' },
  paused: { label: 'Paused', text: '#334155', background: '#e2e8f0' },
  pausing: { label: 'Pausing', text: '#334155', background: '#e2e8f0' },
  canceling: { label: 'Canceling', text: '#92400e', background: '#fef3c7' },
  canceled: { label: 'Canceled', text: '#92400e', background: '#fde68a' },
  completed: { label: 'Completed', text: '#065f46', background: '#d1fae5' },
  failed: { label: 'Failed', text: '#991b1b', background: '#fee2e2' },
};

const KIND_LABEL = {
  paper_download: 'Paper Collection',
  patent_download: 'Patent Collection',
};

const ACTION_FLAG = {
  pause: 'can_pause',
  resume: 'can_resume',
  cancel: 'can_cancel',
  retry: 'can_retry',
};

const FAILURE_META = {
  none: { label: '-', color: '#6b7280' },
  source: { label: 'Source', color: '#b45309' },
  network: { label: 'Network', color: '#1d4ed8' },
  partial: { label: 'Partial', color: '#b45309' },
  task: { label: 'Task', color: '#991b1b' },
  unknown: { label: 'Unknown', color: '#991b1b' },
};

function toSafeTestId(value) {
  return String(value || '')
    .trim()
    .replace(/[^a-zA-Z0-9_-]/g, '_')
    .replace(/_+/g, '_');
}

function toNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function formatPercent(value) {
  const pct = Math.max(0, Math.min(100, toNumber(value, 0)));
  return `${Math.round(pct)}%`;
}

function formatRate(value) {
  const normalized = Math.max(0, toNumber(value, 0));
  return `${(normalized * 100).toFixed(2)}%`;
}

function formatTime(ms) {
  const timestamp = toNumber(ms, 0);
  if (timestamp <= 0) return '-';
  return new Date(timestamp).toLocaleString('zh-CN');
}

function taskTimestamp(task) {
  return Math.max(
    toNumber(task?.updated_at_ms, 0),
    toNumber(task?.finished_at_ms, 0),
    toNumber(task?.started_at_ms, 0),
    toNumber(task?.created_at_ms, 0)
  );
}

function truncateText(value, maxLength = 120) {
  const text = String(value || '').trim();
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 3)}...`;
}

function statusMeta(status) {
  const key = String(status || '').trim().toLowerCase();
  return STATUS_META[key] || { label: key || '-', text: '#374151', background: '#f3f4f6' };
}

function classifyFailure(task) {
  const status = String(task?.status || '').trim().toLowerCase();
  const errorText = String(task?.error || '').trim();
  const sourceErrorsObj = task?.source_errors && typeof task.source_errors === 'object'
    ? task.source_errors
    : {};
  const sourceErrors = Object.entries(sourceErrorsObj)
    .filter(([, detail]) => String(detail || '').trim())
    .map(([source]) => source);
  const failedItems = toNumber(task?.failed_items, 0);

  if (sourceErrors.length > 0) {
    return {
      type: 'source',
      label: `Source (${sourceErrors.length})`,
      detail: `${sourceErrors.join(', ')}${errorText ? ` | ${errorText}` : ''}`,
    };
  }
  if (/timeout|timed out|network|connect|dns|socket/i.test(errorText)) {
    return {
      type: 'network',
      label: 'Network',
      detail: errorText,
    };
  }
  if (failedItems > 0) {
    return {
      type: 'partial',
      label: `Partial (${failedItems})`,
      detail: errorText || `failed_items=${failedItems}`,
    };
  }
  if (status === 'failed' && errorText) {
    return {
      type: 'task',
      label: 'Task',
      detail: errorText,
    };
  }
  if (status === 'failed') {
    return {
      type: 'unknown',
      label: 'Unknown',
      detail: 'No explicit error text',
    };
  }
  return {
    type: 'none',
    label: '-',
    detail: '',
  };
}

function escapeCsv(value) {
  const text = String(value ?? '');
  if (!text.includes(',') && !text.includes('"') && !text.includes('\n')) {
    return text;
  }
  return `"${text.replace(/"/g, '""')}"`;
}

function downloadCsv(rows, filename) {
  const csv = rows.map((row) => row.map((cell) => escapeCsv(cell)).join(',')).join('\n');
  const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' });
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export default function CollectionWorkbench() {
  const navigate = useNavigate();

  const [tasks, setTasks] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [busyActionMap, setBusyActionMap] = useState({});
  const [batchBusy, setBatchBusy] = useState(false);
  const [batchIngestBusy, setBatchIngestBusy] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [kindFilter, setKindFilter] = useState('all');
  const [keywordFilter, setKeywordFilter] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedTaskIds, setSelectedTaskIds] = useState([]);
  const [selectedTaskId, setSelectedTaskId] = useState('');
  const [lastUpdatedAt, setLastUpdatedAt] = useState(0);
  const [logs, setLogs] = useState([]);
  const [startKeywordText, setStartKeywordText] = useState('mental health');
  const [startBusyKind, setStartBusyKind] = useState('');
  const [researchUiLayoutEnabled, setResearchUiLayoutEnabled] = useState(true);

  const appendLog = useCallback((level, message, meta = {}) => {
    const entry = {
      id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      level: String(level || 'info').trim().toLowerCase(),
      message: String(message || ''),
      meta,
      at: Date.now(),
    };
    setLogs((previous) => {
      const next = [...previous, entry];
      if (next.length <= 120) return next;
      return next.slice(next.length - 120);
    });
  }, []);

  useEffect(() => {
    let active = true;
    const loadFeatureFlags = async () => {
      try {
        const flags = await authClient.getRuntimeFeatureFlags();
        if (!active) return;
        setResearchUiLayoutEnabled(flags?.research_ui_layout_enabled !== false);
      } catch (_err) {
        if (!active) return;
        setResearchUiLayoutEnabled(true);
      }
    };
    loadFeatureFlags();
    return () => {
      active = false;
    };
  }, []);

  const loadData = useCallback(
    async ({ silent = false } = {}) => {
      if (!silent) {
        setLoading(true);
      }
      setError('');
      try {
        const [taskPayload, metricPayload] = await Promise.all([
          authClient.listCollectionTasks({
            status: statusFilter === 'all' ? '' : statusFilter,
            limit: 200,
          }),
          authClient.getCollectionTaskMetrics(),
        ]);

        const nextTasks = Array.isArray(taskPayload?.tasks) ? taskPayload.tasks.slice() : [];
        nextTasks.sort((a, b) => taskTimestamp(b) - taskTimestamp(a));
        setTasks(nextTasks);
        setMetrics(metricPayload || null);
        setLastUpdatedAt(Date.now());

        const availableIds = new Set(nextTasks.map((task) => String(task?.task_id || '')));
        setSelectedTaskIds((previous) => previous.filter((id) => availableIds.has(id)));
        setSelectedTaskId((previous) => {
          if (previous && availableIds.has(previous)) return previous;
          return nextTasks[0]?.task_id ? String(nextTasks[0].task_id) : '';
        });
      } catch (loadError) {
        const detail = loadError?.message || 'Failed to load collection tasks';
        setError(detail);
        appendLog('error', detail, { stage: 'loadData' });
      } finally {
        if (!silent) {
          setLoading(false);
        }
      }
    },
    [appendLog, statusFilter]
  );

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (!autoRefresh) return undefined;
    const timer = window.setInterval(() => {
      loadData({ silent: true });
    }, 6000);
    return () => window.clearInterval(timer);
  }, [autoRefresh, loadData]);

  const visibleTasks = useMemo(() => {
    const keyword = String(keywordFilter || '').trim().toLowerCase();
    return tasks.filter((task) => {
      const kind = String(task?.task_kind || '').trim().toLowerCase();
      if (kindFilter !== 'all' && kind !== kindFilter) {
        return false;
      }
      if (!keyword) {
        return true;
      }
      const sourceNames = Object.keys(task?.source_errors || {});
      const fields = [
        task?.task_id,
        task?.task_kind,
        task?.status,
        task?.keyword_text,
        task?.error,
        sourceNames.join(','),
      ]
        .map((value) => String(value || '').toLowerCase())
        .join(' | ');
      return fields.includes(keyword);
    });
  }, [kindFilter, keywordFilter, tasks]);

  const selectedTaskMap = useMemo(() => {
    const map = new Map();
    visibleTasks.forEach((task) => {
      map.set(String(task?.task_id || ''), task);
    });
    return map;
  }, [visibleTasks]);

  const selectedTasks = useMemo(() => {
    const items = [];
    selectedTaskIds.forEach((id) => {
      const task = selectedTaskMap.get(id);
      if (task) items.push(task);
    });
    return items;
  }, [selectedTaskIds, selectedTaskMap]);

  const focusedTask = useMemo(() => {
    if (!selectedTaskId) return null;
    return visibleTasks.find((task) => String(task?.task_id || '') === selectedTaskId) || null;
  }, [selectedTaskId, visibleTasks]);

  const toggleTaskSelected = useCallback((taskId) => {
    const normalized = String(taskId || '').trim();
    if (!normalized) return;
    setSelectedTaskIds((previous) => {
      if (previous.includes(normalized)) {
        return previous.filter((item) => item !== normalized);
      }
      return [...previous, normalized];
    });
  }, []);

  const toggleSelectAllVisible = useCallback(() => {
    const visibleIds = visibleTasks.map((task) => String(task?.task_id || '')).filter(Boolean);
    setSelectedTaskIds((previous) => {
      const allSelected = visibleIds.length > 0 && visibleIds.every((id) => previous.includes(id));
      if (allSelected) {
        return previous.filter((id) => !visibleIds.includes(id));
      }
      const next = new Set(previous);
      visibleIds.forEach((id) => next.add(id));
      return Array.from(next);
    });
  }, [visibleTasks]);

  const isActionBusy = useCallback(
    (taskId, action) => !!busyActionMap[`${action}:${String(taskId || '')}`],
    [busyActionMap]
  );

  const executeTaskAction = useCallback(
    async (task, action) => {
      const taskId = String(task?.task_id || '').trim();
      if (!taskId) return false;

      const flagName = ACTION_FLAG[action];
      if (!flagName || !task?.[flagName]) {
        appendLog('warn', `Task ${taskId} does not support action ${action}`);
        return false;
      }

      const busyKey = `${action}:${taskId}`;
      setBusyActionMap((previous) => ({ ...previous, [busyKey]: true }));
      try {
        if (action === 'pause') {
          await authClient.pauseCollectionTask(taskId);
        } else if (action === 'resume') {
          await authClient.resumeCollectionTask(taskId);
        } else if (action === 'cancel') {
          await authClient.cancelCollectionTask(taskId);
        } else if (action === 'retry') {
          await authClient.retryCollectionTask(taskId);
        } else {
          throw new Error(`Unsupported action: ${action}`);
        }
        appendLog('success', `${action.toUpperCase()} -> ${taskId}`);
        return true;
      } catch (actionError) {
        const detail = actionError?.message || `Failed to ${action} task ${taskId}`;
        setError(detail);
        appendLog('error', detail, { action, taskId });
        return false;
      } finally {
        setBusyActionMap((previous) => {
          const next = { ...previous };
          delete next[busyKey];
          return next;
        });
      }
    },
    [appendLog]
  );

  const runSingleAction = useCallback(
    async (task, action) => {
      const ok = await executeTaskAction(task, action);
      if (ok) {
        setInfo(`Action ${action} applied: ${task?.task_id}`);
        await loadData({ silent: true });
      }
    },
    [executeTaskAction, loadData]
  );

  const runBatchAction = useCallback(
    async (action) => {
      const flagName = ACTION_FLAG[action];
      if (!flagName) return;

      const candidates = selectedTasks.filter((task) => !!task?.[flagName]);
      if (candidates.length <= 0) {
        setError(`No selected task can run action: ${action}`);
        return;
      }

      setBatchBusy(true);
      setError('');
      setInfo('');
      let successCount = 0;
      let failureCount = 0;

      for (const task of candidates) {
        const ok = await executeTaskAction(task, action);
        if (ok) {
          successCount += 1;
        } else {
          failureCount += 1;
        }
      }

      setBatchBusy(false);
      setInfo(`Batch ${action}: success ${successCount}, failed ${failureCount}`);
      appendLog('info', `Batch ${action} done`, { successCount, failureCount });
      await loadData({ silent: true });
    },
    [appendLog, executeTaskAction, loadData, selectedTasks]
  );

  const runBatchIngest = useCallback(async () => {
    const candidates = selectedTasks.filter((task) => {
      const kind = String(task?.task_kind || '').trim().toLowerCase();
      return kind === 'paper_download' || kind === 'patent_download';
    });
    if (candidates.length <= 0) {
      setError('No selected task supports batch ingest');
      return;
    }

    setBatchIngestBusy(true);
    setError('');
    setInfo('');
    let successCount = 0;
    let failureCount = 0;

    for (const task of candidates) {
      const taskId = String(task?.task_id || '').trim();
      const taskKind = String(task?.task_kind || '').trim();
      try {
        const payload = await authClient.addCollectionTaskToLocalKb(taskId, taskKind);
        successCount += 1;
        appendLog('success', `INGEST -> ${taskId}`, {
          taskKind,
          success: toNumber(payload?.success, 0),
          failed: toNumber(payload?.failed, 0),
        });
      } catch (ingestError) {
        failureCount += 1;
        appendLog('error', ingestError?.message || `Failed to ingest task ${taskId}`, { taskKind, taskId });
      }
    }

    setBatchIngestBusy(false);
    setInfo(`Batch ingest done: success ${successCount}, failed ${failureCount}`);
    await loadData({ silent: true });
  }, [appendLog, loadData, selectedTasks]);

  const startCollectionTask = useCallback(
    async (kind) => {
      const normalizedKind = String(kind || '').trim().toLowerCase();
      const keywordText = String(startKeywordText || '').trim();
      if (!keywordText) {
        setError('Keyword is required to start collection.');
        return;
      }

      setStartBusyKind(normalizedKind);
      setError('');
      setInfo('');
      try {
        let payload = null;
        if (normalizedKind === 'paper') {
          payload = await authClient.startPaperCollectionTask({
            keywordText,
            useAnd: true,
            autoAnalyze: false,
            sources: {
              arxiv: { enabled: true, limit: 20 },
              pubmed: { enabled: false, limit: 20 },
              europe_pmc: { enabled: false, limit: 20 },
              openalex: { enabled: false, limit: 20 },
            },
          });
        } else if (normalizedKind === 'patent') {
          payload = await authClient.startPatentCollectionTask({
            keywordText,
            useAnd: true,
            autoAnalyze: false,
            sources: {
              uspto: { enabled: false, limit: 20 },
              google_patents: { enabled: true, limit: 20 },
            },
          });
        } else {
          throw new Error(`Unsupported start kind: ${normalizedKind}`);
        }

        const sessionId = String(payload?.session?.session_id || '');
        appendLog('success', `START ${normalizedKind.toUpperCase()} -> ${sessionId || '(session created)'}`);
        setInfo(`Collection started (${normalizedKind})${sessionId ? `: ${sessionId}` : ''}`);
        await loadData({ silent: true });
      } catch (startError) {
        const detail = startError?.message || `Failed to start ${normalizedKind} collection`;
        setError(detail);
        appendLog('error', detail, { stage: 'startCollectionTask', kind: normalizedKind });
      } finally {
        setStartBusyKind('');
      }
    },
    [appendLog, loadData, startKeywordText]
  );

  const exportTasks = useCallback(() => {
    const rows = [
      [
        'task_id',
        'task_kind',
        'status',
        'progress_percent',
        'total_items',
        'downloaded_items',
        'failed_items',
        'failure_class',
        'error',
        'created_at',
        'updated_at',
      ],
    ];

    const target = selectedTasks.length > 0 ? selectedTasks : visibleTasks;
    target.forEach((task) => {
      const failure = classifyFailure(task);
      rows.push([
        String(task?.task_id || ''),
        String(task?.task_kind || ''),
        String(task?.status || ''),
        String(toNumber(task?.progress_percent, 0)),
        String(toNumber(task?.total_items, 0)),
        String(toNumber(task?.downloaded_items, 0)),
        String(toNumber(task?.failed_items, 0)),
        failure.label,
        String(task?.error || ''),
        formatTime(task?.created_at_ms),
        formatTime(task?.updated_at_ms || task?.finished_at_ms),
      ]);
    });

    const now = new Date();
    const stamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`;
    downloadCsv(rows, `collection_tasks_${stamp}.csv`);
    appendLog('info', `Exported ${target.length} rows to CSV`);
  }, [appendLog, selectedTasks, visibleTasks]);

  const summaryCards = useMemo(() => {
    const statusCounts = metrics?.status_counts || {};
    return [
      { title: 'Total', value: toNumber(metrics?.total_tasks, 0), tone: '#1f2937' },
      { title: 'Backlog', value: toNumber(metrics?.backlog_tasks, 0), tone: '#1d4ed8' },
      { title: 'Failed', value: toNumber(metrics?.failed_tasks, 0), tone: '#991b1b' },
      { title: 'Failure Rate', value: formatRate(metrics?.failure_rate), tone: '#b45309' },
      { title: 'Running', value: toNumber(statusCounts.running, 0), tone: '#1d4ed8' },
      { title: 'Completed', value: toNumber(statusCounts.completed, 0), tone: '#065f46' },
    ];
  }, [metrics]);

  const allVisibleSelected = useMemo(() => {
    if (visibleTasks.length <= 0) return false;
    return visibleTasks.every((task) => selectedTaskIds.includes(String(task?.task_id || '')));
  }, [selectedTaskIds, visibleTasks]);

  const leftPane = (
    <>
      <div style={{ display: 'grid', gap: '8px' }}>
        <button
          type="button"
          onClick={() => navigate('/tools')}
          style={{
            padding: '8px 10px',
            borderRadius: '8px',
            border: '1px solid #d1d5db',
            background: '#fff',
            cursor: 'pointer',
            fontWeight: 700,
          }}
        >
          Back To Tools
        </button>
        <button
          type="button"
          onClick={() => loadData()}
          data-testid="collection-refresh"
          style={{
            padding: '8px 10px',
            borderRadius: '8px',
            border: '1px solid #d1d5db',
            background: '#fff',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: 700,
          }}
          disabled={loading}
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div style={{ display: 'grid', gap: '6px' }}>
        <div style={{ fontWeight: 700, color: '#111827' }}>Quick Start</div>
        <textarea
          value={startKeywordText}
          onChange={(event) => setStartKeywordText(event.target.value)}
          rows={3}
          placeholder="Keywords (comma/newline separated)"
          style={{ padding: '8px', borderRadius: '8px', border: '1px solid #d1d5db', resize: 'vertical' }}
        />
        <button
          type="button"
          data-testid="collection-start-paper"
          onClick={() => startCollectionTask('paper')}
          disabled={startBusyKind === 'paper'}
          style={{
            padding: '8px 10px',
            borderRadius: '8px',
            border: 'none',
            background: '#2563eb',
            color: '#fff',
            cursor: startBusyKind === 'paper' ? 'not-allowed' : 'pointer',
          }}
        >
          {startBusyKind === 'paper' ? 'Starting...' : 'Start Paper Collection'}
        </button>
        <button
          type="button"
          data-testid="collection-start-patent"
          onClick={() => startCollectionTask('patent')}
          disabled={startBusyKind === 'patent'}
          style={{
            padding: '8px 10px',
            borderRadius: '8px',
            border: 'none',
            background: '#0f766e',
            color: '#fff',
            cursor: startBusyKind === 'patent' ? 'not-allowed' : 'pointer',
          }}
        >
          {startBusyKind === 'patent' ? 'Starting...' : 'Start Patent Collection'}
        </button>
      </div>

      <div style={{ display: 'grid', gap: '6px' }}>
        <div style={{ fontWeight: 700, color: '#111827' }}>Filters</div>
        <label style={{ display: 'grid', gap: '4px' }}>
          <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>Status</span>
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            style={{ padding: '7px 8px', borderRadius: '8px', border: '1px solid #d1d5db' }}
          >
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="running">Running</option>
            <option value="paused">Paused</option>
            <option value="canceling">Canceling</option>
            <option value="canceled">Canceled</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </label>
        <label style={{ display: 'grid', gap: '4px' }}>
          <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>Kind</span>
          <select
            value={kindFilter}
            onChange={(event) => setKindFilter(event.target.value)}
            style={{ padding: '7px 8px', borderRadius: '8px', border: '1px solid #d1d5db' }}
          >
            <option value="all">All</option>
            <option value="paper_download">Paper Collection</option>
            <option value="patent_download">Patent Collection</option>
          </select>
        </label>
        <label style={{ display: 'grid', gap: '4px' }}>
          <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>Keyword</span>
          <input
            value={keywordFilter}
            onChange={(event) => setKeywordFilter(event.target.value)}
            placeholder="task_id / error / source"
            style={{ padding: '7px 8px', borderRadius: '8px', border: '1px solid #d1d5db' }}
          />
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: '#374151' }}>
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(event) => setAutoRefresh(event.target.checked)}
          />
          Auto refresh every 6s
        </label>
      </div>

      <div style={{ display: 'grid', gap: '6px' }}>
        <div style={{ fontWeight: 700, color: '#111827' }}>Batch Operations</div>
        <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>
          Selected: <span style={{ color: '#111827', fontWeight: 700 }}>{selectedTasks.length}</span>
        </div>
        <button
          type="button"
          data-testid="collection-batch-cancel"
          onClick={() => runBatchAction('cancel')}
          disabled={batchBusy || selectedTasks.length <= 0}
          style={{
            padding: '8px 10px',
            borderRadius: '8px',
            border: 'none',
            background: '#dc2626',
            color: '#fff',
            cursor: batchBusy || selectedTasks.length <= 0 ? 'not-allowed' : 'pointer',
          }}
        >
          Batch Cancel
        </button>
        <button
          type="button"
          data-testid="collection-batch-retry"
          onClick={() => runBatchAction('retry')}
          disabled={batchBusy || selectedTasks.length <= 0}
          style={{
            padding: '8px 10px',
            borderRadius: '8px',
            border: 'none',
            background: '#2563eb',
            color: '#fff',
            cursor: batchBusy || selectedTasks.length <= 0 ? 'not-allowed' : 'pointer',
          }}
        >
          Batch Retry
        </button>
        <button
          type="button"
          data-testid="collection-batch-ingest"
          onClick={runBatchIngest}
          disabled={batchIngestBusy || selectedTasks.length <= 0}
          style={{
            padding: '8px 10px',
            borderRadius: '8px',
            border: 'none',
            background: '#059669',
            color: '#fff',
            cursor: batchIngestBusy || selectedTasks.length <= 0 ? 'not-allowed' : 'pointer',
          }}
        >
          {batchIngestBusy ? 'Ingesting...' : 'Batch Ingest'}
        </button>
        <button
          type="button"
          data-testid="collection-batch-export"
          onClick={exportTasks}
          disabled={visibleTasks.length <= 0}
          style={{
            padding: '8px 10px',
            borderRadius: '8px',
            border: '1px solid #d1d5db',
            background: '#fff',
            cursor: visibleTasks.length <= 0 ? 'not-allowed' : 'pointer',
          }}
        >
          Export CSV
        </button>
      </div>
    </>
  );

  const centerPane = (
    <>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
          gap: '8px',
        }}
      >
        {summaryCards.map((card) => (
          <div
            key={card.title}
            style={{
              border: '1px solid #e5e7eb',
              borderRadius: '10px',
              padding: '8px 10px',
              background: '#f8fafc',
              minHeight: '68px',
              display: 'grid',
              alignContent: 'center',
              gap: '4px',
            }}
          >
            <div style={{ fontSize: '0.82rem', color: '#6b7280' }}>{card.title}</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: card.tone }}>{card.value}</div>
          </div>
        ))}
      </div>

      {error && (
        <div style={{ background: '#fee2e2', border: '1px solid #fecaca', color: '#991b1b', borderRadius: '8px', padding: '8px 10px' }}>
          {error}
        </div>
      )}
      {info && (
        <div style={{ background: '#ecfdf5', border: '1px solid #a7f3d0', color: '#065f46', borderRadius: '8px', padding: '8px 10px' }}>
          {info}
        </div>
      )}

      <div
        style={{
          border: '1px solid #e5e7eb',
          borderRadius: '10px',
          overflow: 'auto',
          maxHeight: '520px',
        }}
        data-testid="collection-task-table"
      >
        <table
          style={{
            width: '100%',
            borderCollapse: 'separate',
            borderSpacing: 0,
            fontSize: '0.82rem',
            minWidth: '1120px',
          }}
        >
          <thead>
            <tr style={{ background: '#f8fafc' }}>
              <th
                style={{
                  position: 'sticky',
                  left: 0,
                  zIndex: 5,
                  background: '#f8fafc',
                  width: '44px',
                  minWidth: '44px',
                  padding: '6px',
                  borderBottom: '1px solid #e5e7eb',
                }}
              >
                <input
                  type="checkbox"
                  checked={allVisibleSelected}
                  onChange={toggleSelectAllVisible}
                  aria-label="select all visible tasks"
                />
              </th>
              <th
                style={{
                  position: 'sticky',
                  left: '44px',
                  zIndex: 5,
                  background: '#f8fafc',
                  minWidth: '220px',
                  padding: '6px 8px',
                  textAlign: 'left',
                  borderBottom: '1px solid #e5e7eb',
                }}
              >
                Task ID
              </th>
              <th style={{ minWidth: '120px', padding: '6px 8px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>Kind</th>
              <th style={{ minWidth: '100px', padding: '6px 8px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>Status</th>
              <th style={{ minWidth: '140px', padding: '6px 8px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>Progress</th>
              <th style={{ minWidth: '120px', padding: '6px 8px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>Result</th>
              <th style={{ minWidth: '140px', padding: '6px 8px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>Failure Class</th>
              <th style={{ minWidth: '220px', padding: '6px 8px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>Error</th>
              <th style={{ minWidth: '160px', padding: '6px 8px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>Updated</th>
              <th style={{ minWidth: '240px', padding: '6px 8px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {visibleTasks.map((task) => {
              const taskId = String(task?.task_id || '');
              const selected = selectedTaskIds.includes(taskId);
              const focused = selectedTaskId === taskId;
              const status = statusMeta(task?.status);
              const failure = classifyFailure(task);
              const failureStyle = FAILURE_META[failure.type] || FAILURE_META.unknown;
              const progress = Math.max(0, Math.min(100, toNumber(task?.progress_percent, 0)));
              const rowBackground = focused ? '#eff6ff' : selected ? '#f8fafc' : '#ffffff';
              const safeTaskId = toSafeTestId(taskId);

              return (
                <tr
                  key={taskId}
                  data-testid={`collection-task-row-${safeTaskId}`}
                  style={{ background: rowBackground }}
                >
                  <td
                    style={{
                      position: 'sticky',
                      left: 0,
                      zIndex: 4,
                      background: rowBackground,
                      borderTop: '1px solid #f1f5f9',
                      padding: '6px',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={() => toggleTaskSelected(taskId)}
                      aria-label={`select task ${taskId}`}
                    />
                  </td>
                  <td
                    style={{
                      position: 'sticky',
                      left: '44px',
                      zIndex: 4,
                      background: rowBackground,
                      borderTop: '1px solid #f1f5f9',
                      padding: '6px 8px',
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => setSelectedTaskId(taskId)}
                      style={{
                        border: 'none',
                        background: 'transparent',
                        color: '#1d4ed8',
                        cursor: 'pointer',
                        padding: 0,
                        textAlign: 'left',
                        fontFamily: 'monospace',
                        fontSize: '0.8rem',
                      }}
                    >
                      {taskId}
                    </button>
                  </td>
                  <td style={{ borderTop: '1px solid #f1f5f9', padding: '6px 8px' }}>
                    {KIND_LABEL[String(task?.task_kind || '').toLowerCase()] || String(task?.task_kind || '-')}
                  </td>
                  <td style={{ borderTop: '1px solid #f1f5f9', padding: '6px 8px' }}>
                    <span
                      style={{
                        padding: '2px 8px',
                        borderRadius: '999px',
                        color: status.text,
                        background: status.background,
                        fontWeight: 700,
                      }}
                    >
                      {status.label}
                    </span>
                  </td>
                  <td style={{ borderTop: '1px solid #f1f5f9', padding: '6px 8px' }}>
                    <div style={{ display: 'grid', gap: '4px' }}>
                      <div style={{ height: '7px', borderRadius: '999px', background: '#e5e7eb', overflow: 'hidden' }}>
                        <div style={{ width: `${progress}%`, height: '100%', background: '#2563eb' }} />
                      </div>
                      <div style={{ color: '#6b7280' }}>{formatPercent(progress)}</div>
                    </div>
                  </td>
                  <td style={{ borderTop: '1px solid #f1f5f9', padding: '6px 8px' }}>
                    {toNumber(task?.downloaded_items, 0)} / {toNumber(task?.total_items, 0)}
                    {toNumber(task?.failed_items, 0) > 0 && (
                      <span style={{ color: '#991b1b' }}> (failed {toNumber(task?.failed_items, 0)})</span>
                    )}
                  </td>
                  <td style={{ borderTop: '1px solid #f1f5f9', padding: '6px 8px', color: failureStyle.color, fontWeight: 700 }}>
                    {failure.label}
                  </td>
                  <td style={{ borderTop: '1px solid #f1f5f9', padding: '6px 8px', color: '#4b5563' }}>
                    {truncateText(failure.detail || task?.error || '-', 100) || '-'}
                  </td>
                  <td style={{ borderTop: '1px solid #f1f5f9', padding: '6px 8px', color: '#4b5563' }}>
                    {formatTime(task?.updated_at_ms || task?.finished_at_ms || task?.created_at_ms)}
                  </td>
                  <td style={{ borderTop: '1px solid #f1f5f9', padding: '6px 8px', whiteSpace: 'nowrap' }}>
                    {['pause', 'resume', 'cancel', 'retry'].map((action) => {
                      const flagName = ACTION_FLAG[action];
                      const allowed = !!task?.[flagName];
                      const busy = isActionBusy(taskId, action);
                      const colorMap = {
                        pause: '#64748b',
                        resume: '#0f766e',
                        cancel: '#dc2626',
                        retry: '#2563eb',
                      };
                      return (
                        <button
                          key={`${taskId}_${action}`}
                          type="button"
                          data-testid={`collection-task-${action}-${safeTaskId}`}
                          onClick={() => runSingleAction(task, action)}
                          disabled={!allowed || busy}
                          style={{
                            padding: '4px 7px',
                            marginRight: '4px',
                            borderRadius: '6px',
                            border: 'none',
                            background: colorMap[action],
                            color: '#fff',
                            opacity: !allowed || busy ? 0.45 : 1,
                            cursor: !allowed || busy ? 'not-allowed' : 'pointer',
                          }}
                        >
                          {busy ? `${action}...` : action}
                        </button>
                      );
                    })}
                  </td>
                </tr>
              );
            })}
            {visibleTasks.length <= 0 && (
              <tr>
                <td colSpan={10} style={{ padding: '20px', color: '#9ca3af', textAlign: 'center' }}>
                  No tasks matched current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div style={{ color: '#6b7280', fontSize: '0.82rem' }}>
        Last Updated: {lastUpdatedAt ? formatTime(lastUpdatedAt) : '-'} | Visible: {visibleTasks.length} | Selected: {selectedTasks.length}
      </div>
    </>
  );

  const rightPane = (
    <>
      <div style={{ fontWeight: 700, color: '#111827' }}>Evidence & Parameters</div>
      {!focusedTask && (
        <div style={{ color: '#9ca3af', fontSize: '0.88rem' }}>
          Select one task row to inspect details.
        </div>
      )}
      {focusedTask && (
        <div style={{ display: 'grid', gap: '10px', fontSize: '0.86rem' }}>
          <div style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '8px' }}>
            <div style={{ color: '#6b7280' }}>Task</div>
            <div style={{ fontFamily: 'monospace', color: '#111827' }}>{focusedTask.task_id}</div>
            <div style={{ marginTop: '4px', color: '#4b5563' }}>
              Kind: {KIND_LABEL[String(focusedTask.task_kind || '').toLowerCase()] || focusedTask.task_kind}
            </div>
            <div style={{ marginTop: '4px', color: '#4b5563' }}>
              Status: {statusMeta(focusedTask.status).label}
            </div>
            <div style={{ marginTop: '4px', color: '#4b5563' }}>
              Retry Count: {toNumber(focusedTask.retry_count, 0)}
            </div>
          </div>

          <div style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '8px' }}>
            <div style={{ color: '#6b7280', marginBottom: '4px' }}>Collection Inputs</div>
            <div style={{ color: '#111827' }}>
              Keyword: {String(focusedTask.keyword_text || '').trim() || '-'}
            </div>
            <div style={{ color: '#4b5563', marginTop: '4px' }}>
              Created: {formatTime(focusedTask.created_at_ms)}
            </div>
            <div style={{ color: '#4b5563', marginTop: '4px' }}>
              Updated: {formatTime(focusedTask.updated_at_ms || focusedTask.finished_at_ms)}
            </div>
          </div>

          <div style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '8px' }}>
            <div style={{ color: '#6b7280', marginBottom: '4px' }}>Source Errors</div>
            {Object.keys(focusedTask.source_errors || {}).length <= 0 && (
              <div style={{ color: '#9ca3af' }}>No source-level error</div>
            )}
            {Object.entries(focusedTask.source_errors || {}).map(([source, detail]) => (
              <div key={source} style={{ marginTop: '5px' }}>
                <div style={{ color: '#b45309', fontWeight: 700 }}>{source}</div>
                <div style={{ color: '#4b5563', fontSize: '0.82rem' }}>{String(detail || '-')}</div>
              </div>
            ))}
          </div>

          <div style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '8px' }}>
            <div style={{ color: '#6b7280', marginBottom: '4px' }}>Quota / Runtime</div>
            <div style={{ color: '#4b5563' }}>
              Global: {toNumber(focusedTask?.quota?.global_limit, 0)} | Kind: {toNumber(focusedTask?.quota?.task_kind_limit, 0)} | User: {toNumber(focusedTask?.quota?.per_user_limit, 0)}
            </div>
            <div style={{ color: '#4b5563', marginTop: '4px' }}>
              Max Concurrency: {toNumber(focusedTask?.max_concurrency, 0)}
            </div>
            <div style={{ color: '#4b5563', marginTop: '4px' }}>
              Queue Position: {focusedTask?.queue_position ?? '-'}
            </div>
            <div style={{ color: '#4b5563', marginTop: '4px' }}>
              Quota Blocked Reason: {String(focusedTask?.quota_blocked_reason || '-')}
            </div>
          </div>
        </div>
      )}
    </>
  );

  const bottomPane = (
    <div style={{ display: 'grid', gap: '6px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontWeight: 700, color: '#f8fafc' }}>Task Log Stream</div>
        <button
          type="button"
          onClick={() => setLogs([])}
          style={{
            padding: '4px 8px',
            borderRadius: '6px',
            border: '1px solid #334155',
            background: '#1e293b',
            color: '#e2e8f0',
            cursor: 'pointer',
          }}
        >
          Clear
        </button>
      </div>
      {!logs.length && <div style={{ color: '#94a3b8', fontSize: '0.84rem' }}>No task logs yet.</div>}
      {logs.map((entry) => {
        const tone =
          entry.level === 'error'
            ? '#fca5a5'
            : entry.level === 'warn'
              ? '#fcd34d'
              : entry.level === 'success'
                ? '#86efac'
                : '#bfdbfe';
        return (
          <div key={entry.id} style={{ fontSize: '0.82rem', color: tone, fontFamily: 'monospace' }}>
            [{formatTime(entry.at)}] [{entry.level.toUpperCase()}] {entry.message}
          </div>
        );
      })}
    </div>
  );

  const legacyLayout = (
    <div data-testid="collection-workbench-legacy-layout" style={{ display: 'grid', gap: '12px' }}>
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '12px', display: 'grid', gap: '10px' }}>
        {leftPane}
      </section>
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '12px', display: 'grid', gap: '10px' }}>
        {centerPane}
      </section>
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '12px', display: 'grid', gap: '10px' }}>
        {rightPane}
      </section>
      <section style={{ background: '#0f172a', borderRadius: '10px', padding: '12px' }}>
        {bottomPane}
      </section>
    </div>
  );

  return (
    <div data-testid="collection-workbench-page">
      {researchUiLayoutEnabled ? (
        <ResearchWorkbenchShell
          leftPane={leftPane}
          centerPane={centerPane}
          rightPane={rightPane}
          bottomPane={bottomPane}
          testId="collection-workbench-shell"
        />
      ) : (
        legacyLayout
      )}
    </div>
  );
}
