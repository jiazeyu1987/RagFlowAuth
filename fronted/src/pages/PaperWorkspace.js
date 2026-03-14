import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { paperPlagApi } from '../features/paperPlag/api';

const activeReportStatuses = new Set(['pending', 'running', 'canceling']);

function formatTime(ms) {
  const value = Number(ms);
  if (!Number.isFinite(value) || value <= 0) return '-';
  return new Date(value).toLocaleString('zh-CN');
}

function parseManualSources(text) {
  return String(text || '')
    .split('\n')
    .map((line) => String(line || '').trim())
    .filter(Boolean)
    .map((line, index) => ({
      source_doc_id: `manual_${index + 1}`,
      source_title: `manual_source_${index + 1}`,
      content_text: line,
    }));
}

export default function PaperWorkspace() {
  const navigate = useNavigate();

  const [paperId, setPaperId] = useState('paper_workspace_1');
  const [title, setTitle] = useState('');
  const [contentText, setContentText] = useState('');
  const [note, setNote] = useState('');
  const [sourceText, setSourceText] = useState('');
  const [similarityThresholdPct, setSimilarityThresholdPct] = useState(20);
  const [priority, setPriority] = useState(100);

  const [versionsLoading, setVersionsLoading] = useState(false);
  const [reportsLoading, setReportsLoading] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [startLoading, setStartLoading] = useState(false);
  const [diffLoading, setDiffLoading] = useState(false);
  const [reportDetailLoading, setReportDetailLoading] = useState(false);
  const [rollbackLoadingId, setRollbackLoadingId] = useState('');
  const [cancelLoadingId, setCancelLoadingId] = useState('');
  const [exportLoadingId, setExportLoadingId] = useState('');

  const [versions, setVersions] = useState([]);
  const [reports, setReports] = useState([]);
  const [selectedReportId, setSelectedReportId] = useState('');
  const [reportDetail, setReportDetail] = useState(null);

  const [diffFromVersionId, setDiffFromVersionId] = useState('');
  const [diffToVersionId, setDiffToVersionId] = useState('');
  const [diffResult, setDiffResult] = useState(null);

  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  const normalizedPaperId = useMemo(() => String(paperId || '').trim(), [paperId]);

  const loadVersions = useCallback(async ({ silent = false } = {}) => {
    const currentPaperId = String(normalizedPaperId || '').trim();
    if (!currentPaperId) {
      setVersions([]);
      return;
    }
    if (!silent) setVersionsLoading(true);
    try {
      const payload = await paperPlagApi.listVersions(currentPaperId, 100);
      const nextItems = Array.isArray(payload?.items) ? payload.items : [];
      setVersions(nextItems);
      if (!diffFromVersionId && nextItems[0]?.id) {
        setDiffFromVersionId(String(nextItems[0].id));
      }
      if (!diffToVersionId && nextItems[1]?.id) {
        setDiffToVersionId(String(nextItems[1].id));
      }
      if (!diffToVersionId && !nextItems[1]?.id && nextItems[0]?.id) {
        setDiffToVersionId(String(nextItems[0].id));
      }
    } catch (err) {
      setError(err.message || '加载版本失败');
    } finally {
      if (!silent) setVersionsLoading(false);
    }
  }, [diffFromVersionId, diffToVersionId, normalizedPaperId]);

  const loadReports = useCallback(async ({ silent = false } = {}) => {
    const currentPaperId = String(normalizedPaperId || '').trim();
    if (!currentPaperId) {
      setReports([]);
      return;
    }
    if (!silent) setReportsLoading(true);
    try {
      const payload = await paperPlagApi.listReports({ paperId: currentPaperId, limit: 100 });
      const nextItems = Array.isArray(payload?.items) ? payload.items : [];
      setReports(nextItems);

      if (selectedReportId) {
        const exists = nextItems.some((item) => String(item?.report_id || '') === String(selectedReportId || ''));
        if (!exists) {
          setSelectedReportId('');
          setReportDetail(null);
        }
      }
    } catch (err) {
      setError(err.message || '加载查重报告失败');
    } finally {
      if (!silent) setReportsLoading(false);
    }
  }, [normalizedPaperId, selectedReportId]);

  const loadReportDetail = useCallback(async (reportId, { silent = false } = {}) => {
    const normalizedReportId = String(reportId || '').trim();
    if (!normalizedReportId) return;
    if (!silent) setReportDetailLoading(true);
    try {
      const payload = await paperPlagApi.getReport(normalizedReportId);
      setSelectedReportId(normalizedReportId);
      setReportDetail(payload);
    } catch (err) {
      setError(err.message || '加载报告详情失败');
    } finally {
      if (!silent) setReportDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!normalizedPaperId) return;
    loadVersions();
    loadReports();
  }, [loadReports, loadVersions, normalizedPaperId]);

  const hasActiveReports = useMemo(
    () => reports.some((item) => activeReportStatuses.has(String(item?.status || '').toLowerCase())),
    [reports],
  );

  useEffect(() => {
    if (!hasActiveReports) return undefined;
    const timer = window.setInterval(() => {
      loadReports({ silent: true });
      if (selectedReportId) {
        loadReportDetail(selectedReportId, { silent: true });
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [hasActiveReports, loadReportDetail, loadReports, selectedReportId]);

  const handleSaveVersion = async () => {
    setError('');
    setInfo('');
    if (!normalizedPaperId) {
      setError('请输入论文ID');
      return;
    }
    if (!String(contentText || '').trim()) {
      setError('论文内容不能为空');
      return;
    }
    setSaveLoading(true);
    try {
      const payload = await paperPlagApi.saveVersion(normalizedPaperId, {
        title,
        content_text: contentText,
        note: note || null,
      });
      const versionNo = payload?.version?.version_no;
      setInfo(`版本保存成功${versionNo ? `（v${versionNo}）` : ''}`);
      await loadVersions();
    } catch (err) {
      setError(err.message || '保存版本失败');
    } finally {
      setSaveLoading(false);
    }
  };

  const handleStartReport = async () => {
    setError('');
    setInfo('');
    if (!normalizedPaperId) {
      setError('请输入论文ID');
      return;
    }
    if (!String(contentText || '').trim()) {
      setError('请先填写论文内容再提交查重');
      return;
    }

    const threshold = Math.max(0, Math.min(Number(similarityThresholdPct) || 0, 100)) / 100;
    const normalizedPriority = Math.max(1, Math.min(Number(priority) || 100, 1000));

    setStartLoading(true);
    try {
      const payload = await paperPlagApi.startReport({
        paper_id: normalizedPaperId,
        title,
        content_text: contentText,
        note: note || null,
        similarity_threshold: threshold,
        priority: normalizedPriority,
        sources: parseManualSources(sourceText),
      });
      const reportId = String(payload?.report?.report_id || '');
      setInfo(`查重任务已提交${reportId ? `（${reportId}）` : ''}`);
      await Promise.all([loadVersions(), loadReports()]);
      if (reportId) {
        await loadReportDetail(reportId);
      }
    } catch (err) {
      setError(err.message || '提交查重失败');
    } finally {
      setStartLoading(false);
    }
  };

  const handleLoadVersionToEditor = async (versionId) => {
    setError('');
    setInfo('');
    try {
      const payload = await paperPlagApi.getVersion(normalizedPaperId, versionId);
      const version = payload?.version || {};
      setTitle(String(version.title || ''));
      setContentText(String(version.content_text || ''));
      setNote(String(version.note || ''));
      setInfo(`已加载版本 v${version.version_no || version.id}`);
    } catch (err) {
      setError(err.message || '加载版本内容失败');
    }
  };

  const handleDiffVersions = async () => {
    setError('');
    setInfo('');
    const fromVersionId = Number(diffFromVersionId);
    const toVersionId = Number(diffToVersionId);
    if (!Number.isFinite(fromVersionId) || !Number.isFinite(toVersionId) || fromVersionId <= 0 || toVersionId <= 0) {
      setError('请选择有效的版本进行对比');
      return;
    }

    setDiffLoading(true);
    try {
      const payload = await paperPlagApi.diffVersions(normalizedPaperId, fromVersionId, toVersionId);
      setDiffResult(payload);
      setInfo('版本对比完成');
    } catch (err) {
      setError(err.message || '版本对比失败');
    } finally {
      setDiffLoading(false);
    }
  };

  const handleRollback = async (versionId) => {
    if (!window.confirm(`确定回滚到版本 ${versionId} 并生成新版本吗？`)) return;
    const rollbackNote = window.prompt('请输入回滚备注（可选）', `rollback_from_ui_version=${versionId}`);
    if (rollbackNote === null) return;

    setError('');
    setInfo('');
    setRollbackLoadingId(String(versionId));
    try {
      await paperPlagApi.rollbackVersion(normalizedPaperId, versionId, String(rollbackNote || '').trim() || null);
      setInfo(`版本 ${versionId} 回滚成功`);
      await loadVersions();
    } catch (err) {
      setError(err.message || '版本回滚失败');
    } finally {
      setRollbackLoadingId('');
    }
  };

  const handleCancelReport = async (reportId) => {
    setError('');
    setInfo('');
    setCancelLoadingId(String(reportId));
    try {
      const payload = await paperPlagApi.cancelReport(reportId);
      setInfo(`报告 ${reportId} 已请求取消`);
      await loadReports();
      if (payload?.report?.report_id) {
        await loadReportDetail(payload.report.report_id);
      }
    } catch (err) {
      setError(err.message || '取消查重任务失败');
    } finally {
      setCancelLoadingId('');
    }
  };

  const handleExportReport = async (reportId) => {
    setError('');
    setInfo('');
    setExportLoadingId(String(reportId));
    try {
      const payload = await paperPlagApi.exportReport(reportId, 'md');
      setInfo(`报告导出成功：${payload.filename}`);
    } catch (err) {
      setError(err.message || '导出报告失败');
    } finally {
      setExportLoadingId('');
    }
  };

  return (
    <div style={{ display: 'grid', gap: '12px' }} data-testid="paper-workspace-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
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
          Back To Tools
        </button>
        <button
          type="button"
          onClick={() => {
            setError('');
            setInfo('');
            loadVersions();
            loadReports();
            if (selectedReportId) loadReportDetail(selectedReportId);
          }}
          style={{
            padding: '8px 12px',
            borderRadius: '10px',
            border: '1px solid #e5e7eb',
            background: '#fff',
            cursor: 'pointer',
            fontWeight: 700,
          }}
        >
          Refresh
        </button>
      </div>

      {error && (
        <div style={{ background: '#fee2e2', border: '1px solid #fecaca', color: '#991b1b', borderRadius: '8px', padding: '10px 12px' }}>
          {error}
        </div>
      )}
      {info && (
        <div style={{ background: '#ecfdf5', border: '1px solid #a7f3d0', color: '#065f46', borderRadius: '8px', padding: '10px 12px' }}>
          {info}
        </div>
      )}

      <div style={{ display: 'grid', gap: '12px', gridTemplateColumns: 'minmax(520px, 2fr) minmax(420px, 1fr)' }}>
        <section style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '14px', display: 'grid', gap: '10px' }}>
          <div style={{ fontWeight: 700, fontSize: '1.02rem' }}>论文工作台</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <label style={{ display: 'grid', gap: '4px' }}>
              <span style={{ color: '#6b7280', fontSize: '0.86rem' }}>Paper ID</span>
              <input
                value={paperId}
                onChange={(e) => setPaperId(e.target.value)}
                placeholder="paper_workspace_1"
                style={{ padding: '8px 10px', borderRadius: '8px', border: '1px solid #d1d5db' }}
              />
            </label>
            <label style={{ display: 'grid', gap: '4px' }}>
              <span style={{ color: '#6b7280', fontSize: '0.86rem' }}>标题</span>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="请输入论文标题"
                style={{ padding: '8px 10px', borderRadius: '8px', border: '1px solid #d1d5db' }}
              />
            </label>
          </div>

          <label style={{ display: 'grid', gap: '4px' }}>
            <span style={{ color: '#6b7280', fontSize: '0.86rem' }}>论文内容</span>
            <textarea
              value={contentText}
              onChange={(e) => setContentText(e.target.value)}
              placeholder="输入论文内容..."
              rows={12}
              style={{ padding: '10px', borderRadius: '8px', border: '1px solid #d1d5db', resize: 'vertical', fontFamily: 'monospace' }}
            />
          </label>

          <label style={{ display: 'grid', gap: '4px' }}>
            <span style={{ color: '#6b7280', fontSize: '0.86rem' }}>版本备注/提交备注（可选）</span>
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="例如：第一版草稿"
              style={{ padding: '8px 10px', borderRadius: '8px', border: '1px solid #d1d5db' }}
            />
          </label>

          <div style={{ display: 'grid', gap: '10px', gridTemplateColumns: '1fr 1fr 1fr' }}>
            <label style={{ display: 'grid', gap: '4px' }}>
              <span style={{ color: '#6b7280', fontSize: '0.86rem' }}>相似度阈值（%）</span>
              <input
                type="number"
                min={0}
                max={100}
                value={similarityThresholdPct}
                onChange={(e) => setSimilarityThresholdPct(e.target.value)}
                style={{ padding: '8px 10px', borderRadius: '8px', border: '1px solid #d1d5db' }}
              />
            </label>
            <label style={{ display: 'grid', gap: '4px' }}>
              <span style={{ color: '#6b7280', fontSize: '0.86rem' }}>任务优先级</span>
              <input
                type="number"
                min={1}
                max={1000}
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                style={{ padding: '8px 10px', borderRadius: '8px', border: '1px solid #d1d5db' }}
              />
            </label>
            <div style={{ display: 'flex', alignItems: 'end', gap: '8px' }}>
              <button
                type="button"
                onClick={handleSaveVersion}
                disabled={saveLoading}
                style={{
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: '1px solid #d1d5db',
                  background: '#fff',
                  cursor: saveLoading ? 'not-allowed' : 'pointer',
                  width: '100%',
                }}
              >
                {saveLoading ? '保存中...' : '保存版本'}
              </button>
              <button
                type="button"
                onClick={handleStartReport}
                disabled={startLoading}
                style={{
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: 'none',
                  background: '#2563eb',
                  color: '#fff',
                  cursor: startLoading ? 'not-allowed' : 'pointer',
                  width: '100%',
                }}
              >
                {startLoading ? '提交中...' : '提交查重'}
              </button>
            </div>
          </div>

          <label style={{ display: 'grid', gap: '4px' }}>
            <span style={{ color: '#6b7280', fontSize: '0.86rem' }}>手动来源文本（每行一条，可选）</span>
            <textarea
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              placeholder="用于模拟相似片段来源，每行一段文本"
              rows={4}
              style={{ padding: '10px', borderRadius: '8px', border: '1px solid #d1d5db', resize: 'vertical', fontFamily: 'monospace' }}
            />
          </label>
        </section>

        <section style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '14px', display: 'grid', gap: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontWeight: 700, fontSize: '1.02rem' }}>查重报告</div>
            <span style={{ color: '#6b7280', fontSize: '0.86rem' }}>{reportsLoading ? '加载中...' : `${reports.length} 条`}</span>
          </div>

          <div style={{ maxHeight: '320px', overflow: 'auto', border: '1px solid #f3f4f6', borderRadius: '8px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
              <thead>
                <tr style={{ background: '#f9fafb' }}>
                  <th style={{ padding: '8px', textAlign: 'left' }}>报告ID</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>状态</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>重复率</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((item) => {
                  const reportId = String(item?.report_id || '');
                  const status = String(item?.status || '');
                  const isSelected = reportId && reportId === selectedReportId;
                  return (
                    <tr key={reportId} style={{ background: isSelected ? '#eff6ff' : 'transparent' }}>
                      <td style={{ padding: '8px', borderTop: '1px solid #f3f4f6' }}>{reportId || '-'}</td>
                      <td style={{ padding: '8px', borderTop: '1px solid #f3f4f6' }}>{status || '-'}</td>
                      <td style={{ padding: '8px', borderTop: '1px solid #f3f4f6' }}>
                        {Math.round((Number(item?.duplicate_rate || 0) || 0) * 10000) / 100}%
                      </td>
                      <td style={{ padding: '8px', borderTop: '1px solid #f3f4f6', whiteSpace: 'nowrap' }}>
                        <button
                          type="button"
                          onClick={() => loadReportDetail(reportId)}
                          style={{ padding: '4px 8px', marginRight: '6px', borderRadius: '6px', border: '1px solid #d1d5db', background: '#fff', cursor: 'pointer' }}
                        >
                          详情
                        </button>
                        <button
                          type="button"
                          onClick={() => handleExportReport(reportId)}
                          disabled={exportLoadingId === reportId}
                          style={{ padding: '4px 8px', marginRight: '6px', borderRadius: '6px', border: '1px solid #d1d5db', background: '#fff', cursor: exportLoadingId === reportId ? 'not-allowed' : 'pointer' }}
                        >
                          {exportLoadingId === reportId ? '导出中' : '导出'}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleCancelReport(reportId)}
                          disabled={cancelLoadingId === reportId || !activeReportStatuses.has(status.toLowerCase())}
                          style={{
                            padding: '4px 8px',
                            borderRadius: '6px',
                            border: 'none',
                            background: '#ef4444',
                            color: '#fff',
                            cursor: cancelLoadingId === reportId || !activeReportStatuses.has(status.toLowerCase()) ? 'not-allowed' : 'pointer',
                          }}
                        >
                          {cancelLoadingId === reportId ? '取消中' : '取消'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {!reports.length && (
                  <tr>
                    <td colSpan={4} style={{ padding: '16px', color: '#9ca3af' }}>暂无查重报告</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div style={{ border: '1px solid #f3f4f6', borderRadius: '8px', padding: '10px', minHeight: '180px' }}>
            <div style={{ fontWeight: 600, marginBottom: '6px' }}>
              {selectedReportId ? `报告详情：${selectedReportId}` : '报告详情'}
            </div>
            {reportDetailLoading && <div style={{ color: '#6b7280' }}>加载中...</div>}
            {!reportDetailLoading && !reportDetail && <div style={{ color: '#9ca3af' }}>请选择报告查看详情</div>}
            {!reportDetailLoading && reportDetail && (
              <div style={{ display: 'grid', gap: '8px' }}>
                <div style={{ color: '#374151', fontSize: '0.88rem' }}>
                  状态：{reportDetail?.report?.status || '-'}，重复率：{Math.round((Number(reportDetail?.report?.duplicate_rate || 0) || 0) * 10000) / 100}%
                </div>
                <div style={{ color: '#374151', fontSize: '0.88rem' }}>
                  摘要：{reportDetail?.report?.summary || '-'}
                </div>
                <div style={{ maxHeight: '140px', overflow: 'auto', border: '1px solid #f3f4f6', borderRadius: '6px' }}>
                  {(reportDetail?.hits || []).map((hit) => (
                    <div key={hit.id} style={{ padding: '8px', borderTop: '1px solid #f3f4f6' }}>
                      <div style={{ fontSize: '0.84rem', color: '#111827' }}>
                        {hit.source_title || hit.source_doc_id || 'unknown source'}
                        {' · '}相似度 {Math.round((Number(hit.similarity_score || 0) || 0) * 10000) / 100}%
                      </div>
                      <div style={{ marginTop: '4px', color: '#4b5563', fontSize: '0.82rem' }}>{hit.snippet_text || '-'}</div>
                    </div>
                  ))}
                  {!reportDetail?.hits?.length && <div style={{ padding: '8px', color: '#9ca3af' }}>无命中片段</div>}
                </div>
              </div>
            )}
          </div>
        </section>
      </div>

      <div style={{ display: 'grid', gap: '12px', gridTemplateColumns: 'minmax(520px, 2fr) minmax(420px, 1fr)' }}>
        <section style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '14px', display: 'grid', gap: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontWeight: 700, fontSize: '1.02rem' }}>版本历史</div>
            <span style={{ color: '#6b7280', fontSize: '0.86rem' }}>{versionsLoading ? '加载中...' : `${versions.length} 条`}</span>
          </div>

          <div style={{ display: 'grid', gap: '8px', gridTemplateColumns: '1fr 1fr auto' }}>
            <select
              value={diffFromVersionId}
              onChange={(e) => setDiffFromVersionId(e.target.value)}
              style={{ padding: '8px 10px', borderRadius: '8px', border: '1px solid #d1d5db' }}
            >
              <option value="">选择对比起点版本</option>
              {versions.map((item) => (
                <option key={`from_${item.id}`} value={item.id}>v{item.version_no} (id={item.id})</option>
              ))}
            </select>
            <select
              value={diffToVersionId}
              onChange={(e) => setDiffToVersionId(e.target.value)}
              style={{ padding: '8px 10px', borderRadius: '8px', border: '1px solid #d1d5db' }}
            >
              <option value="">选择对比目标版本</option>
              {versions.map((item) => (
                <option key={`to_${item.id}`} value={item.id}>v{item.version_no} (id={item.id})</option>
              ))}
            </select>
            <button
              type="button"
              onClick={handleDiffVersions}
              disabled={diffLoading}
              style={{
                padding: '8px 12px',
                borderRadius: '8px',
                border: '1px solid #d1d5db',
                background: '#fff',
                cursor: diffLoading ? 'not-allowed' : 'pointer',
              }}
            >
              {diffLoading ? '对比中...' : '版本对比'}
            </button>
          </div>

          <div style={{ maxHeight: '320px', overflow: 'auto', border: '1px solid #f3f4f6', borderRadius: '8px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
              <thead>
                <tr style={{ background: '#f9fafb' }}>
                  <th style={{ padding: '8px', textAlign: 'left' }}>版本</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>备注</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>时间</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {versions.map((item) => (
                  <tr key={item.id}>
                    <td style={{ padding: '8px', borderTop: '1px solid #f3f4f6' }}>v{item.version_no} (id={item.id})</td>
                    <td style={{ padding: '8px', borderTop: '1px solid #f3f4f6' }}>{item.note || '-'}</td>
                    <td style={{ padding: '8px', borderTop: '1px solid #f3f4f6' }}>{formatTime(item.created_at_ms)}</td>
                    <td style={{ padding: '8px', borderTop: '1px solid #f3f4f6', whiteSpace: 'nowrap' }}>
                      <button
                        type="button"
                        onClick={() => handleLoadVersionToEditor(item.id)}
                        style={{ padding: '4px 8px', marginRight: '6px', borderRadius: '6px', border: '1px solid #d1d5db', background: '#fff', cursor: 'pointer' }}
                      >
                        加载
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRollback(item.id)}
                        disabled={rollbackLoadingId === String(item.id)}
                        style={{
                          padding: '4px 8px',
                          borderRadius: '6px',
                          border: 'none',
                          background: '#f59e0b',
                          color: '#fff',
                          cursor: rollbackLoadingId === String(item.id) ? 'not-allowed' : 'pointer',
                        }}
                      >
                        {rollbackLoadingId === String(item.id) ? '回滚中' : '回滚'}
                      </button>
                    </td>
                  </tr>
                ))}
                {!versions.length && (
                  <tr>
                    <td colSpan={4} style={{ padding: '16px', color: '#9ca3af' }}>暂无版本记录</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '14px', display: 'grid', gap: '10px' }}>
          <div style={{ fontWeight: 700, fontSize: '1.02rem' }}>Diff 结果</div>
          {!diffResult && <div style={{ color: '#9ca3af' }}>请先选择两个版本并执行对比</div>}
          {diffResult && (
            <div style={{ display: 'grid', gap: '8px' }}>
              <div style={{ color: '#374151', fontSize: '0.88rem' }}>
                新增行：{diffResult.added_lines || 0}，删除行：{diffResult.removed_lines || 0}，变更块：{diffResult.changed_blocks || 0}
              </div>
              <pre
                style={{
                  margin: 0,
                  maxHeight: '380px',
                  overflow: 'auto',
                  border: '1px solid #f3f4f6',
                  borderRadius: '8px',
                  background: '#f9fafb',
                  padding: '10px',
                  fontSize: '0.82rem',
                }}
              >
                {(diffResult.diff_preview || []).join('\n') || '(empty diff)'}
              </pre>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
