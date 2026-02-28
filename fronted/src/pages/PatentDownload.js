import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import patentDownloadManager from '../features/patentDownload/PatentDownloadManager';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';

const DEFAULT_SOURCES = {
  uspto: { enabled: false, limit: 15 },
  google_patents: { enabled: true, limit: 30 },
};
const LAST_CONFIG_KEY = 'patent_download_last_config_v1';

const LOCAL_KB_REF = '[本地专利]';

const sourceLabelMap = {
  uspto: 'USPTO（美国专利商标局）',
  google_patents: 'Google Patents',
};

const boxStyle = {
  background: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: '12px',
  padding: '14px',
  boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
};

const sectionTitleStyle = {
  margin: '0 0 8px 0',
  fontSize: '1.03rem',
  fontWeight: 900,
  color: '#111827',
};

const labelStyle = {
  display: 'block',
  marginBottom: '6px',
  color: '#374151',
  fontWeight: 700,
  fontSize: '0.9rem',
};

const tagStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '4px 10px',
  borderRadius: '999px',
  border: '1px solid #bbf7d0',
  background: '#f0fdf4',
  color: '#166534',
  fontSize: '0.85rem',
  fontWeight: 700,
};

const clampLimit = (value) => {
  const n = Number(value);
  if (!Number.isFinite(n)) return 10;
  return Math.min(1000, Math.max(1, Math.floor(n)));
};

const humanizeSourceError = (msg) => {
  const text = String(msg || '');
  if (!text) return '-';
  if (text.toLowerCase().includes('method chat not supported yet')) return '自动分析失败：当前通用LLM不支持 chat 调用，请更换可对话聊天体';
  if (text === 'no_results') return '未检索到结果';
  if (text === 'source_not_implemented') return '数据源未实现';
  if (text.startsWith('auto_analyze_failed:')) return `自动分析失败：${text.slice('auto_analyze_failed:'.length).trim()}`;
  if (text.startsWith('download_failed:')) return `下载失败：${text.slice('download_failed:'.length).trim()}`;
  if (text.startsWith('source_failed:')) return `源异常：${text.slice('source_failed:'.length).trim()}`;
  return text;
};
const reasonLabelMap = {
  missing_pdf_url: '无可下载PDF',
  download_failed: '下载失败',
};

const statusChip = (item) => {
  if (item?.added_doc_id) return { text: '已添加', color: '#065f46', bg: '#d1fae5', border: '#a7f3d0' };
  if (item?.status === 'downloaded_cached') return { text: '已下载(历史)', color: '#374151', bg: '#f3f4f6', border: '#e5e7eb' };
  if (item?.status === 'downloaded') return { text: '已下载', color: '#1e3a8a', bg: '#dbeafe', border: '#bfdbfe' };
  return { text: '失败', color: '#991b1b', bg: '#fee2e2', border: '#fecaca' };
};

const stripHtml = (value) => String(value || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
const isAnalysisErrorText = (value) => {
  const text = String(value || '').trim();
  if (!text) return false;
  const lower = text.toLowerCase();
  return (
    text.startsWith('自动分析失败：') ||
    lower.startsWith('**error**') ||
    lower.startsWith('error:') ||
    lower.includes('method chat not supported yet') ||
    lower.includes('llm_error_response')
  );
};
const humanizeAnalysisErrorText = (value) => {
  const text = String(value || '').trim();
  if (!text) return '';
  if (text.toLowerCase().includes('method chat not supported yet')) {
    return '自动分析失败：当前通用LLM不支持 chat 调用，请更换可对话聊天体';
  }
  return text;
};

export default function PatentDownload() {
  const navigate = useNavigate();
  const [keywordText, setKeywordText] = useState('');
  const [useAnd, setUseAnd] = useState(true);
  const [autoAnalyze, setAutoAnalyze] = useState(false);
  const [sources, setSources] = useState(DEFAULT_SOURCES);
  const [sessionPayload, setSessionPayload] = useState(null);
  const [sourceErrors, setSourceErrors] = useState({});
  const [sourceStats, setSourceStats] = useState({});
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [addingItemId, setAddingItemId] = useState(null);
  const [deletingItemId, setDeletingItemId] = useState(null);
  const [addingAll, setAddingAll] = useState(false);
  const [deletingSession, setDeletingSession] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [resultTab, setResultTab] = useState('current');
  const [historyKeywords, setHistoryKeywords] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [selectedHistoryKey, setSelectedHistoryKey] = useState('');
  const [historyPayload, setHistoryPayload] = useState(null);
  const [historyItemsLoading, setHistoryItemsLoading] = useState(false);
  const [deletingHistoryKey, setDeletingHistoryKey] = useState('');
  const [addingHistoryKey, setAddingHistoryKey] = useState('');
  const [configReady, setConfigReady] = useState(false);

  const parsedKeywords = useMemo(() => patentDownloadManager.parseKeywords(keywordText), [keywordText]);
  const sessionId = sessionPayload?.session?.session_id || '';
  const sessionStatus = sessionPayload?.session?.status || '';
  const items = useMemo(() => (Array.isArray(sessionPayload?.items) ? sessionPayload.items : []), [sessionPayload?.items]);
  const historyItems = useMemo(() => (Array.isArray(historyPayload?.items) ? historyPayload.items : []), [historyPayload?.items]);
  const frontendLogs = useMemo(() => {
    const lines = [];
    Object.entries(sourceErrors || {}).forEach(([k, msg]) => {
      lines.push(`${sourceLabelMap[k] || k}: ${humanizeSourceError(msg)}`);
    });
    Object.entries(sourceStats || {}).forEach(([k, st]) => {
      const skippedKeyword = Number(st?.skipped_keyword || 0);
      const skippedDuplicate = Number(st?.skipped_duplicate || 0);
      const skippedStopped = Number(st?.skipped_stopped || 0);
      if (skippedKeyword > 0 || skippedDuplicate > 0 || skippedStopped > 0) {
        lines.push(
          `${sourceLabelMap[k] || k}: 未下载原因 - 关键词过滤 ${skippedKeyword}，重复去重 ${skippedDuplicate}，停止未处理 ${skippedStopped}`
        );
      }
      const fr = st?.failed_reasons && typeof st.failed_reasons === 'object' ? st.failed_reasons : {};
      Object.entries(fr).forEach(([reason, cnt]) => {
        const n = Number(cnt || 0);
        if (n <= 0) return;
        lines.push(`${sourceLabelMap[k] || k}: 失败原因 - ${reasonLabelMap[reason] || reason} ${n}`);
      });
    });
    if (autoAnalyze) {
      items.forEach((item) => {
        const text = String(item?.analysis_text || '').trim();
        if (!isAnalysisErrorText(text)) return;
        const title = stripHtml(item?.title || item?.filename || `patent_${item?.item_id || '-'}`);
        lines.push(`${title}: ${humanizeAnalysisErrorText(text)}`);
      });
    }
    return Array.from(new Set(lines));
  }, [sourceErrors, sourceStats, items, autoAnalyze]);

  const updateSource = (key, patch) => {
    setSources((prev) => ({ ...prev, [key]: { ...(prev[key] || {}), ...patch } }));
  };

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(LAST_CONFIG_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object') {
        if (typeof parsed.keywordText === 'string') setKeywordText(parsed.keywordText);
        if (typeof parsed.useAnd === 'boolean') setUseAnd(parsed.useAnd);
        if (typeof parsed.autoAnalyze === 'boolean') setAutoAnalyze(parsed.autoAnalyze);
        if (parsed.sources && typeof parsed.sources === 'object') {
          const nextSources = {};
          Object.keys(sourceLabelMap).forEach((key) => {
            const cfg = parsed.sources[key] || {};
            nextSources[key] = {
              enabled: Boolean(cfg.enabled),
              limit: clampLimit(cfg.limit),
            };
          });
          setSources(nextSources);
        }
      }
    } catch (_) {
      // ignore bad cache
    } finally {
      setConfigReady(true);
    }
  }, []);

  useEffect(() => {
    if (!configReady) return;
    try {
      window.localStorage.setItem(
        LAST_CONFIG_KEY,
        JSON.stringify({
          keywordText,
          useAnd,
          autoAnalyze,
          sources,
        })
      );
    } catch (_) {
      // ignore storage errors
    }
  }, [keywordText, useAnd, autoAnalyze, sources, configReady]);

  const refreshSession = async (id = sessionId) => {
    if (!id) return null;
    const data = await patentDownloadManager.getSession(id);
    setSessionPayload(data);
    setSourceErrors(data?.source_errors || {});
    setSourceStats(data?.source_stats || {});
    return data;
  };

  const loadHistoryKeywords = async () => {
    setHistoryLoading(true);
    setHistoryError('');
    try {
      const res = await patentDownloadManager.listHistoryKeywords();
      const rawList = Array.isArray(res?.history) ? res.history : [];
      let list = rawList;
      const needEnrich = rawList.some(
        (row) =>
          typeof row?.downloaded_count !== 'number' ||
          typeof row?.analyzed_count !== 'number' ||
          typeof row?.added_count !== 'number'
      );
      if (needEnrich) {
        const settled = await Promise.all(
          rawList.map(async (row) => {
            const key = String(row?.history_key || '');
            if (!key) return row;
            try {
              const payload = await patentDownloadManager.getHistoryByKeyword(key);
              const items = Array.isArray(payload?.items) ? payload.items : [];
              const downloadedCount = items.filter((it) =>
                ['downloaded', 'downloaded_cached'].includes(String(it?.status || ''))
              ).length;
              const analyzedCount = items.filter(
                (it) => String(it?.analysis_text || '').trim() && !isAnalysisErrorText(it?.analysis_text)
              ).length;
              const addedCount = items.filter((it) => Boolean(it?.added_doc_id)).length;
              return {
                ...row,
                downloaded_count: downloadedCount,
                analyzed_count: analyzedCount,
                added_count: addedCount,
              };
            } catch (_) {
              return {
                ...row,
                downloaded_count: Number(row?.downloaded_count || 0),
                analyzed_count: Number(row?.analyzed_count || 0),
                added_count: Number(row?.added_count || 0),
              };
            }
          })
        );
        list = settled;
      }
      setHistoryKeywords(list);
      if (!selectedHistoryKey && list.length) setSelectedHistoryKey(String(list[0].history_key || ''));
      if (selectedHistoryKey && !list.some((x) => String(x.history_key || '') === String(selectedHistoryKey))) {
        setSelectedHistoryKey(list.length ? String(list[0].history_key || '') : '');
      }
      return list;
    } catch (e) {
      setHistoryError(e?.message || '获取历史关键词失败');
      setHistoryKeywords([]);
      return [];
    } finally {
      setHistoryLoading(false);
    }
  };

  const loadHistoryItems = async (historyKey = selectedHistoryKey) => {
    if (!historyKey) {
      setHistoryPayload(null);
      return;
    }
    setHistoryItemsLoading(true);
    setHistoryError('');
    try {
      const payload = await patentDownloadManager.getHistoryByKeyword(historyKey);
      setHistoryPayload(payload);
    } catch (e) {
      setHistoryError(e?.message || '获取历史专利列表失败');
      setHistoryPayload(null);
    } finally {
      setHistoryItemsLoading(false);
    }
  };

  const runDownload = async () => {
    setLoading(true);
    setError('');
    setInfo('');
    try {
      const data = await patentDownloadManager.createSession({
        keywordText,
        useAnd,
        autoAnalyze,
        sources,
      });
      setSessionPayload({
        session: data?.session || null,
        items: Array.isArray(data?.items) ? data.items : [],
        summary: data?.summary || null,
      });
      setSourceErrors(data?.source_errors || {});
      setSourceStats(data?.source_stats || {});
      setInfo('已开始下载，结果会逐条显示。');
      setResultTab('current');
      loadHistoryKeywords();
    } catch (e) {
      setError(e?.message || '下载失败');
      setSessionPayload(null);
      setSourceErrors({});
      setSourceStats({});
    } finally {
      setLoading(false);
    }
  };

  const stopDownload = async () => {
    if (!sessionId) return;
    setStopping(true);
    setError('');
    try {
      const res = await patentDownloadManager.stopSession(sessionId);
      if (res?.status === 'stopped') {
        setInfo('已停止下载。');
      } else {
        setInfo('已发送停止请求，当前条目处理完成后将停止。');
      }
      await refreshSession(sessionId);
    } catch (e) {
      setError(e?.message || '停止下载失败');
    } finally {
      setStopping(false);
    }
  };

  useEffect(() => {
    loadHistoryKeywords();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedHistoryKey) return;
    loadHistoryItems(selectedHistoryKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedHistoryKey]);

  useEffect(() => {
    if (!sessionId || !['running', 'stopping'].includes(String(sessionStatus || ''))) return undefined;
    let alive = true;
    const tick = async () => {
      try {
        const data = await patentDownloadManager.getSession(sessionId);
        if (!alive) return;
        setSessionPayload(data);
        setSourceErrors(data?.source_errors || {});
        setSourceStats(data?.source_stats || {});
        const status = data?.session?.status || '';
        const total = Number(data?.summary?.total || 0);
        const downloaded = Number(data?.summary?.downloaded || 0);
        if (status === 'completed') {
          if (total <= 0) {
            setError('未从所选数据源检索到可下载结果，请调整关键词/AND OR/数据源后重试。');
            setInfo('');
          } else if (downloaded <= 0) {
            setError('检索到结果但全部下载失败，请查看数据源错误信息。');
            setInfo('');
          } else {
            setError('');
            setInfo(`下载完成：成功 ${downloaded} / 总计 ${total}`);
          }
        } else if (status === 'stopped') {
          setError('');
          setInfo(`下载已停止：成功 ${downloaded} / 总计 ${total}`);
        } else if (status === 'stopping') {
          setInfo('停止中：当前条目处理完成后停止...');
        } else if (status === 'failed') {
          setError(data?.session?.error || '下载任务失败');
          setInfo('');
        }
      } catch (e) {
        if (!alive) return;
        setError(e?.message || '获取下载进度失败');
      }
    };
    tick();
    const timer = window.setInterval(tick, 1200);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [sessionId, sessionStatus]);

  const resolveItemSessionId = (item) => String(item?.session_id || sessionId || '');

  const openPreview = (item) => {
    const sid = resolveItemSessionId(item);
    if (!sid || !item?.item_id || !item?.has_file) return;
    const target = patentDownloadManager.toPreviewTarget(sid, item);
    if (!target) return;
    setPreviewTarget(target);
    setPreviewOpen(true);
  };

  const addOne = async (item) => {
    const sid = resolveItemSessionId(item);
    if (!sid || !item?.item_id) return;
    setError('');
    setInfo('');
    setAddingItemId(item.item_id);
    try {
      await patentDownloadManager.addItemToLocalKb(sid, item.item_id, LOCAL_KB_REF);
      if (sid === sessionId) await refreshSession(sessionId);
      await loadHistoryItems();
      setInfo('已添加到 [本地专利]');
    } catch (e) {
      setError(e?.message || '添加失败');
    } finally {
      setAddingItemId(null);
    }
  };

  const deleteOne = async (item) => {
    const sid = resolveItemSessionId(item);
    if (!sid || !item?.item_id) return;
    const ok = window.confirm('确认删除该下载结果吗？如果已添加到知识库，也会从 [本地专利] 删除。');
    if (!ok) return;
    setError('');
    setInfo('');
    setDeletingItemId(item.item_id);
    try {
      await patentDownloadManager.deleteItem(sid, item.item_id, { deleteLocalKb: true });
      if (sid === sessionId) await refreshSession(sessionId);
      await loadHistoryKeywords();
      await loadHistoryItems();
      setInfo('已删除该条下载结果。');
    } catch (e) {
      setError(e?.message || '删除失败');
    } finally {
      setDeletingItemId(null);
    }
  };

  const addAll = async () => {
    if (!sessionId) return;
    setError('');
    setInfo('');
    setAddingAll(true);
    try {
      const res = await patentDownloadManager.addAllToLocalKb(sessionId, LOCAL_KB_REF);
      if (res?.session) setSessionPayload(res.session);
      else await refreshSession(sessionId);
      setInfo(`批量添加完成：成功 ${res?.success || 0}，失败 ${res?.failed || 0}`);
    } catch (e) {
      setError(e?.message || '批量添加失败');
    } finally {
      setAddingAll(false);
    }
  };

  const removeSession = async () => {
    if (!sessionId) return;
    const ok = window.confirm('确认删除本次下载结果及由本页添加到 [本地专利] 的文件吗？');
    if (!ok) return;
    setDeletingSession(true);
    setError('');
    setInfo('');
    try {
      const res = await patentDownloadManager.deleteSession(sessionId, { deleteLocalKb: true });
      setSessionPayload(null);
      setInfo(`已删除：条目 ${res?.deleted_items || 0}，本地专利 ${res?.deleted_docs || 0}`);
      await loadHistoryKeywords();
      await loadHistoryItems();
    } catch (e) {
      setError(e?.message || '删除失败');
    } finally {
      setDeletingSession(false);
    }
  };

  const deleteHistoryKeyword = async (row) => {
    const key = String(row?.history_key || '');
    if (!key) return;
    const ok = window.confirm(`确认删除历史关键词“${row?.keyword_display || ''}”对应的全部本地PDF吗？`);
    if (!ok) return;
    setDeletingHistoryKey(key);
    setError('');
    setInfo('');
    try {
      const res = await patentDownloadManager.deleteHistoryKeyword(key);
      setInfo(`已删除历史关键词：会话 ${res?.deleted_sessions || 0}，条目 ${res?.deleted_items || 0}，本地文件 ${res?.deleted_files || 0}`);
      const nextList = await loadHistoryKeywords();
      const nextKey = nextList.length ? String(nextList[0].history_key || '') : '';
      setSelectedHistoryKey(nextKey);
      if (nextKey) await loadHistoryItems(nextKey);
      else setHistoryPayload(null);
      if (sessionId) await refreshSession(sessionId);
    } catch (e) {
      setError(e?.message || '删除历史关键词失败');
    } finally {
      setDeletingHistoryKey('');
    }
  };

  const addHistoryKeywordToKb = async (row) => {
    const key = String(row?.history_key || '');
    if (!key) return;
    setAddingHistoryKey(key);
    setError('');
    setInfo('');
    try {
      const res = await patentDownloadManager.addHistoryToLocalKb(key, LOCAL_KB_REF);
      setInfo(`历史关键词批量添加完成：成功 ${res?.success || 0}，失败 ${res?.failed || 0}`);
      await loadHistoryKeywords();
      if (selectedHistoryKey === key) await loadHistoryItems(key);
      if (sessionId) await refreshSession(sessionId);
    } catch (e) {
      setError(e?.message || '历史关键词批量添加失败');
    } finally {
      setAddingHistoryKey('');
    }
  };

  const refreshHistoryPanel = async () => {
    setError('');
    setInfo('');
    try {
      const list = await loadHistoryKeywords();
      const activeKey = selectedHistoryKey || (list.length ? String(list[0].history_key || '') : '');
      if (activeKey) {
        setSelectedHistoryKey(activeKey);
        await loadHistoryItems(activeKey);
      } else {
        setHistoryPayload(null);
      }
      setInfo('历史记录已刷新');
    } catch (e) {
      setError(e?.message || '刷新历史记录失败');
    }
  };

  const renderPatentItems = (list) => {
    if (!list.length) {
      return <div style={{ color: '#9ca3af', fontSize: '0.9rem' }}>暂无专利列表</div>;
    }
    return (
      <div style={{ display: 'grid', gap: '8px', maxHeight: '70vh', overflow: 'auto', paddingRight: '4px' }}>
        {list.map((item) => {
          const chip = statusChip(item);
          const addDisabled =
            !['downloaded', 'downloaded_cached'].includes(String(item?.status || '')) ||
            Boolean(item?.added_doc_id) ||
            addingItemId === item.item_id;
          const deleting = deletingItemId === item.item_id;
          const canView = Boolean(item?.has_file);
          return (
            <div
              key={`${item.session_id || 's'}-${item.item_id}`}
              style={{
                border: '1px solid #e5e7eb',
                background: '#fff',
                borderRadius: '10px',
                padding: '10px',
                display: 'grid',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'flex-start' }}>
                <div style={{ fontWeight: 800, color: '#111827', lineHeight: 1.35 }}>
                  {stripHtml(item.title || item.filename || `patent_${item.item_id}`)}
                </div>
                <span
                  style={{
                    whiteSpace: 'nowrap',
                    border: `1px solid ${chip.border}`,
                    background: chip.bg,
                    color: chip.color,
                    fontSize: '0.8rem',
                    borderRadius: '999px',
                    padding: '2px 8px',
                    fontWeight: 700,
                  }}
                >
                  {chip.text}
                </span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', color: '#6b7280', fontSize: '0.82rem' }}>
                <span>{sourceLabelMap[item.source] || item.source}</span>
                <span>{item.publication_number || '-'}</span>
                <span>{item.publication_date || '-'}</span>
                <span>申请人：{item.assignee || '-'}</span>
                <span>发明人：{item.inventor || '-'}</span>
                <span>专利ID：{item.patent_id || '-'}</span>
                {item.error ? <span style={{ color: '#b91c1c' }}>{item.error}</span> : null}
              </div>
              {item.detail_url ? (
                <div style={{ fontSize: '0.82rem' }}>
                  <a href={item.detail_url} target="_blank" rel="noreferrer" style={{ color: '#2563eb', textDecoration: 'none' }}>
                    原始链接
                  </a>
                </div>
              ) : null}
              {item.analysis_text && !isAnalysisErrorText(item.analysis_text) ? (
                <div style={{ fontSize: '0.83rem', color: '#1f2937', lineHeight: 1.5, background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '8px' }}>
                  <strong>保护要点：</strong> {item.analysis_text}
                </div>
              ) : null}
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={() => openPreview(item)}
                  disabled={!canView}
                  style={{
                    padding: '7px 10px',
                    borderRadius: '8px',
                    border: '1px solid #0ea5e9',
                    background: canView ? '#0ea5e9' : '#bae6fd',
                    color: '#fff',
                    cursor: canView ? 'pointer' : 'not-allowed',
                    fontWeight: 700,
                  }}
                >
                  查看
                </button>
                <button
                  type="button"
                  onClick={() => addOne(item)}
                  disabled={addDisabled}
                  style={{
                    padding: '7px 10px',
                    borderRadius: '8px',
                    border: '1px solid #16a34a',
                    background: '#16a34a',
                    color: '#fff',
                    cursor: addDisabled ? 'not-allowed' : 'pointer',
                    opacity: addDisabled ? 0.55 : 1,
                    fontWeight: 700,
                  }}
                >
                  {item?.added_doc_id ? '已添加' : addingItemId === item.item_id ? '添加中...' : '添加知识库'}
                </button>
                <button
                  type="button"
                  onClick={() => deleteOne(item)}
                  disabled={deleting}
                  style={{
                    padding: '7px 10px',
                    borderRadius: '8px',
                    border: '1px solid #ef4444',
                    background: deleting ? '#fecaca' : '#ef4444',
                    color: '#fff',
                    cursor: deleting ? 'not-allowed' : 'pointer',
                    fontWeight: 700,
                  }}
                >
                  {deleting ? '删除中...' : '删除'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div style={{ display: 'grid', gap: '12px' }} data-testid="patent-download-page">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <button
          type="button"
          onClick={() => navigate('/tools')}
          style={{
            padding: '8px 12px',
            borderRadius: '10px',
            border: '1px solid #e5e7eb',
            background: '#fff',
            cursor: 'pointer',
            fontWeight: 700,
          }}
        >
          返回实用工具
        </button>
        <div style={{ color: '#6b7280', fontSize: '0.88rem' }}>
          目标知识库: <span style={{ color: '#111827', fontWeight: 800 }}>{LOCAL_KB_REF}</span>
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(340px, 1fr) minmax(680px, 2fr)',
          gap: '12px',
          alignItems: 'start',
        }}
      >
        <div style={{ display: 'grid', gap: '12px' }}>
          <section style={boxStyle}>
            <h2 style={sectionTitleStyle}>关键词设置</h2>
            <label style={labelStyle}>关键词（支持逗号、分号、换行分隔）</label>
            <textarea
              value={keywordText}
              onChange={(e) => setKeywordText(e.target.value)}
              rows={6}
              placeholder={'3D打印\n导板'}
              style={{
                width: '100%',
                resize: 'vertical',
                borderRadius: '10px',
                border: '1px solid #d1d5db',
                padding: '10px 12px',
                outline: 'none',
                lineHeight: 1.55,
                fontSize: '0.92rem',
                boxSizing: 'border-box',
              }}
            />
            <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input id="patent-use-and" type="checkbox" checked={useAnd} onChange={(e) => setUseAnd(Boolean(e.target.checked))} />
              <label htmlFor="patent-use-and" style={{ color: '#111827', fontWeight: 700 }}>
                关键词使用 AND（不勾选则使用 OR）
              </label>
            </div>
            <div style={{ marginTop: '10px' }}>
              <div style={{ color: '#6b7280', fontSize: '0.85rem', marginBottom: '6px' }}>已解析关键词</div>
              {parsedKeywords.length ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {parsedKeywords.map((kw) => (
                    <span key={kw} style={tagStyle}>
                      {kw}
                    </span>
                  ))}
                </div>
              ) : (
                <div style={{ color: '#9ca3af', fontSize: '0.85rem' }}>暂无</div>
              )}
            </div>
          </section>

          <section style={boxStyle}>
            <h2 style={sectionTitleStyle}>专利下载配置</h2>
            <div style={{ display: 'grid', gap: '8px' }}>
              {Object.keys(sourceLabelMap).map((key) => {
                const cfg = sources[key] || { enabled: false, limit: 10 };
                return (
                  <div
                    key={key}
                    style={{
                      border: '1px solid #e5e7eb',
                      borderRadius: '10px',
                      padding: '10px',
                      display: 'grid',
                      gridTemplateColumns: '1fr auto',
                      alignItems: 'center',
                      gap: '10px',
                    }}
                  >
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, color: '#111827' }}>
                      <input
                        type="checkbox"
                        checked={Boolean(cfg.enabled)}
                        onChange={(e) => updateSource(key, { enabled: Boolean(e.target.checked) })}
                      />
                      {sourceLabelMap[key]}
                    </label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ color: '#6b7280', fontSize: '0.85rem' }}>上限</span>
                      <input
                        type="number"
                        min={1}
                        max={1000}
                        value={cfg.limit}
                        onChange={(e) => updateSource(key, { limit: clampLimit(e.target.value) })}
                        style={{ width: '90px', border: '1px solid #d1d5db', borderRadius: '8px', padding: '6px 8px' }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <div style={{ marginTop: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <label
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 10px',
                  border: '1px solid #e5e7eb',
                  borderRadius: '10px',
                  color: '#111827',
                  fontWeight: 700,
                  background: '#fff',
                }}
              >
                <input type="checkbox" checked={autoAnalyze} onChange={(e) => setAutoAnalyze(Boolean(e.target.checked))} />
                自动分析
              </label>
              <button
                type="button"
                onClick={runDownload}
                disabled={loading}
                style={{
                  padding: '10px 14px',
                  borderRadius: '10px',
                  border: '1px solid #2563eb',
                  background: loading ? '#93c5fd' : '#2563eb',
                  color: '#fff',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  fontWeight: 800,
                }}
              >
                {loading ? '下载中...' : '一键下载'}
              </button>
            </div>

            {Object.keys(sourceStats || {}).length > 0 && (
              <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.82rem' }}>
                {Object.entries(sourceStats).map(([k, st]) => (
                  <div key={k}>
                    <div>
                      {sourceLabelMap[k] || k}: 候选 {st?.candidates || 0}，下载成功 {st?.downloaded || 0}，历史复用 {st?.reused || 0}，失败 {st?.failed || 0}
                    </div>
                    {st?.query ? (
                      <div style={{ marginTop: '2px' }}>
                        {k === 'uspto' ? 'USPTO 英文描述' : '搜索描述'}: {st.query}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
            {error && <div style={{ marginTop: '10px', color: '#b91c1c', fontSize: '0.9rem' }}>{error}</div>}
            {info && <div style={{ marginTop: '10px', color: '#065f46', fontSize: '0.9rem' }}>{info}</div>}
            {frontendLogs.length > 0 && (
              <div style={{ marginTop: '10px', color: '#92400e', fontSize: '0.86rem', borderTop: '1px dashed #e5e7eb', paddingTop: '8px' }}>
                <div style={{ fontWeight: 800, marginBottom: '4px' }}>日志</div>
                {frontendLogs.map((line, idx) => (
                  <div key={`${idx}-${line}`}>{line}</div>
                ))}
              </div>
            )}
          </section>
        </div>

        <section style={boxStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <button
              type="button"
              onClick={() => setResultTab('current')}
              style={{
                padding: '7px 12px',
                borderRadius: '999px',
                border: resultTab === 'current' ? '1px solid #2563eb' : '1px solid #e5e7eb',
                background: resultTab === 'current' ? '#dbeafe' : '#fff',
                color: resultTab === 'current' ? '#1e40af' : '#374151',
                cursor: 'pointer',
                fontWeight: 700,
              }}
            >
              本次下载结果
            </button>
            <button
              type="button"
              onClick={() => setResultTab('history')}
              style={{
                padding: '7px 12px',
                borderRadius: '999px',
                border: resultTab === 'history' ? '1px solid #2563eb' : '1px solid #e5e7eb',
                background: resultTab === 'history' ? '#dbeafe' : '#fff',
                color: resultTab === 'history' ? '#1e40af' : '#374151',
                cursor: 'pointer',
                fontWeight: 700,
              }}
            >
              历史记录
            </button>
          </div>
          {resultTab === 'current' ? (
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
              <button
                type="button"
                onClick={stopDownload}
                disabled={!sessionId || !['running', 'stopping'].includes(String(sessionStatus || '')) || stopping}
                style={{
                  padding: '9px 12px',
                  borderRadius: '10px',
                  border: '1px solid #f59e0b',
                  background: stopping ? '#fde68a' : '#f59e0b',
                  color: '#fff',
                  cursor:
                    !sessionId || !['running', 'stopping'].includes(String(sessionStatus || '')) || stopping
                      ? 'not-allowed'
                      : 'pointer',
                  fontWeight: 800,
                }}
              >
                {stopping ? '停止中...' : '停止下载'}
              </button>
              <button
                type="button"
                onClick={addAll}
                disabled={!sessionId || addingAll}
                style={{
                  padding: '9px 12px',
                  borderRadius: '10px',
                  border: '1px solid #059669',
                  background: addingAll ? '#6ee7b7' : '#10b981',
                  color: '#fff',
                  cursor: !sessionId || addingAll ? 'not-allowed' : 'pointer',
                  fontWeight: 800,
                }}
              >
                {addingAll ? '批量添加中...' : '全部添加知识库'}
              </button>
              <button
                type="button"
                onClick={removeSession}
                disabled={!sessionId || deletingSession}
                style={{
                  padding: '9px 12px',
                  borderRadius: '10px',
                  border: '1px solid #ef4444',
                  background: deletingSession ? '#fecaca' : '#ef4444',
                  color: '#fff',
                  cursor: !sessionId || deletingSession ? 'not-allowed' : 'pointer',
                  fontWeight: 800,
                }}
              >
                全部删除
              </button>
            </div>
          ) : null}

          {resultTab === 'current' ? (
            !items.length ? (
              <div style={{ color: '#9ca3af', fontSize: '0.9rem' }}>
                {sessionStatus === 'running' ? '下载进行中，结果会逐条显示...' : '暂无下载结果'}
              </div>
            ) : (
              renderPatentItems(items)
            )
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '280px minmax(420px, 1fr)', gap: '10px' }}>
              <div style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '8px', maxHeight: '70vh', overflow: 'auto' }}>
                <div style={{ fontWeight: 800, color: '#111827', marginBottom: '6px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span>历史关键词</span>
                  <button
                    type="button"
                    onClick={refreshHistoryPanel}
                    disabled={historyLoading || historyItemsLoading}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '7px',
                      border: '1px solid #2563eb',
                      background: historyLoading || historyItemsLoading ? '#93c5fd' : '#2563eb',
                      color: '#fff',
                      cursor: historyLoading || historyItemsLoading ? 'not-allowed' : 'pointer',
                      fontSize: '0.78rem',
                      fontWeight: 700,
                    }}
                  >
                    刷新
                  </button>
                </div>
                {historyLoading ? <div style={{ color: '#6b7280', fontSize: '0.86rem' }}>加载中...</div> : null}
                {!historyLoading && !historyKeywords.length ? <div style={{ color: '#9ca3af', fontSize: '0.86rem' }}>暂无历史关键词</div> : null}
                <div style={{ display: 'grid', gap: '6px' }}>
                  {historyKeywords.map((row) => {
                    const active = String(row.history_key || '') === String(selectedHistoryKey || '');
                    const downloadedCount = Number(row?.downloaded_count || 0);
                    const analyzedCount = Number(row?.analyzed_count || 0);
                    const addedCount = Number(row?.added_count || 0);
                    const canAdd = downloadedCount > 0 && addedCount < downloadedCount;
                    const adding = addingHistoryKey === String(row.history_key || '');
                    const allAdded = downloadedCount > 0 && addedCount >= downloadedCount;
                    const partialAdded = addedCount > 0 && addedCount < downloadedCount;
                    const addBtnBg = allAdded ? '#d1d5db' : partialAdded ? '#f59e0b' : '#16a34a';
                    const addBtnBorder = allAdded ? '#9ca3af' : partialAdded ? '#d97706' : '#15803d';
                    return (
                      <div
                        key={row.history_key}
                        style={{
                          border: active ? '1px solid #60a5fa' : '1px solid #e5e7eb',
                          background: active ? '#eff6ff' : '#fff',
                          borderRadius: '8px',
                          padding: '8px',
                          display: 'grid',
                          gap: '6px',
                        }}
                      >
                        <button
                          type="button"
                          onClick={() => setSelectedHistoryKey(String(row.history_key || ''))}
                          style={{
                            textAlign: 'left',
                            border: 'none',
                            background: 'transparent',
                            padding: 0,
                            cursor: 'pointer',
                          }}
                        >
                          <div style={{ fontWeight: 700, color: '#111827', fontSize: '0.88rem' }}>{row.keyword_display || '-'}</div>
                          <div style={{ fontSize: '0.78rem', color: '#6b7280', marginTop: '4px' }}>下载 {downloadedCount}，已分析 {analyzedCount}，已入库 {addedCount}</div>
                        </button>
                        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                          <button
                            type="button"
                            onClick={() => addHistoryKeywordToKb(row)}
                            disabled={!canAdd || adding}
                            style={{
                              padding: '4px 8px',
                              borderRadius: '7px',
                              border: `1px solid ${addBtnBorder}`,
                              background: addBtnBg,
                              color: '#fff',
                              cursor: !canAdd || adding ? 'not-allowed' : 'pointer',
                              fontSize: '0.78rem',
                              fontWeight: 700,
                              opacity: !canAdd || adding ? 0.75 : 1,
                            }}
                          >
                            {adding ? '添加中...' : '添加知识库'}
                          </button>
                          <button
                            type="button"
                            onClick={() => deleteHistoryKeyword(row)}
                            disabled={deletingHistoryKey === String(row.history_key || '')}
                            style={{
                              padding: '4px 8px',
                              borderRadius: '7px',
                              border: '1px solid #ef4444',
                              background: deletingHistoryKey === String(row.history_key || '') ? '#fecaca' : '#ef4444',
                              color: '#fff',
                              cursor: deletingHistoryKey === String(row.history_key || '') ? 'not-allowed' : 'pointer',
                              fontSize: '0.78rem',
                              fontWeight: 700,
                            }}
                          >
                            {deletingHistoryKey === String(row.history_key || '') ? '删除中...' : '删除'}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div>
                {historyError ? <div style={{ color: '#b91c1c', fontSize: '0.88rem', marginBottom: '8px' }}>{historyError}</div> : null}
                {historyItemsLoading ? <div style={{ color: '#6b7280', fontSize: '0.88rem' }}>历史专利加载中...</div> : null}
                {!historyItemsLoading && historyPayload?.history ? (
                  <div style={{ color: '#6b7280', fontSize: '0.82rem', marginBottom: '8px' }}>
                    关键词：{historyPayload.history.keyword_display || '-'}，会话 {historyPayload.history.session_count || 0}，专利 {historyPayload.history.item_count || 0}
                  </div>
                ) : null}
                {!historyItemsLoading && renderPatentItems(historyItems)}
              </div>
            </div>
          )}
        </section>
      </div>

      <DocumentPreviewModal open={previewOpen} onClose={() => setPreviewOpen(false)} target={previewTarget} canDownloadFiles />
    </div>
  );
}
