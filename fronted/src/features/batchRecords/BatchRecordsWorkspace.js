import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import batchRecordsApi from './api';
import { electronicSignatureApi } from '../electronicSignature/api';
import { mapUserFacingErrorMessage } from '../../shared/errors/userFacingErrorMessages';

const PANEL_STYLE = {
  background: '#ffffff',
  border: '1px solid #dbe2ea',
  borderRadius: '16px',
  padding: '18px',
  boxShadow: '0 10px 30px rgba(15, 23, 42, 0.06)',
};

const INPUT_STYLE = {
  border: '1px solid #cbd5e1',
  borderRadius: 10,
  padding: '10px 12px',
};

const TEXTAREA_STYLE = {
  ...INPUT_STYLE,
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
  minHeight: 110,
  resize: 'vertical',
};

const buttonStyle = (variant = 'primary') => {
  if (variant === 'secondary') {
    return {
      border: '1px solid #cbd5e1',
      borderRadius: 10,
      background: '#ffffff',
      color: '#0f172a',
      cursor: 'pointer',
      padding: '8px 12px',
      fontWeight: 700,
    };
  }
  return {
    border: '1px solid #0f766e',
    borderRadius: 10,
    background: '#0f766e',
    color: '#ffffff',
    cursor: 'pointer',
    padding: '8px 12px',
    fontWeight: 700,
  };
};

const pillStyle = (background, color) => ({
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  borderRadius: 999,
  padding: '6px 10px',
  background,
  color,
  fontSize: '0.82rem',
  fontWeight: 800,
});

const formatTime = (ms) => {
  const value = Number(ms);
  if (!Number.isFinite(value) || value <= 0) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
};

const safeJson = (value) => {
  try {
    return JSON.stringify(value ?? {}, null, 2);
  } catch {
    return '{}';
  }
};

const parseJsonStrict = (text, code) => {
  try {
    return JSON.parse(String(text ?? '').trim() || 'null');
  } catch {
    throw new Error(code);
  }
};

const STEP_PHOTO_FIELD = 'photo_evidences';

const encodeBase64 = (buffer) => {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
};

const readFilesAsPhotoEvidence = async (files) => Promise.all(
  Array.from(files || []).map(async (file) => {
    const mediaType = String(file?.type || '').trim();
    if (!mediaType.startsWith('image/')) {
      throw new Error('step_photo_media_type_invalid');
    }
    const buffer = typeof file?.arrayBuffer === 'function'
      ? await file.arrayBuffer()
      : await new Response(file).arrayBuffer();
    return {
      filename: String(file?.name || 'photo-evidence'),
      media_type: mediaType,
      captured_at_ms: Date.now(),
      data_url: `data:${mediaType};base64,${encodeBase64(buffer)}`,
    };
  })
);

export default function BatchRecordsWorkspace() {
  const { can } = useAuth();

  const permissions = useMemo(() => ({
    templateManage: typeof can === 'function' ? can('batch_records', 'template_manage') : false,
    execute: typeof can === 'function' ? can('batch_records', 'execute') : false,
    sign: typeof can === 'function' ? can('batch_records', 'sign') : false,
    review: typeof can === 'function' ? can('batch_records', 'review') : false,
    export: typeof can === 'function' ? can('batch_records', 'export') : false,
  }), [can]);

  const [templates, setTemplates] = useState([]);
  const [templatesLoading, setTemplatesLoading] = useState(true);
  const [templatesError, setTemplatesError] = useState('');

  const [executions, setExecutions] = useState([]);
  const [executionsLoading, setExecutionsLoading] = useState(true);
  const [executionsError, setExecutionsError] = useState('');

  const [selectedExecutionId, setSelectedExecutionId] = useState('');
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [detail, setDetail] = useState(null); // { bundle, signed_signature, reviewed_signature }
  const [stepDrafts, setStepDrafts] = useState({});
  const [stepPhotoDrafts, setStepPhotoDrafts] = useState({});

  const [createTemplateForm, setCreateTemplateForm] = useState({
    template_code: '',
    template_name: '',
    stepsJson: '[\\n  {\"key\":\"step-1\",\"title\":\"Step 1\"}\\n]',
    metaJson: '{\\n  \"kind\": \"production\"\\n}',
  });
  const [createVersionForm, setCreateVersionForm] = useState({
    template_code: '',
    template_name: '',
    stepsJson: '[\\n  {\"key\":\"step-1\",\"title\":\"Step 1\"}\\n]',
    metaJson: '{\\n  \"kind\": \"production\"\\n}',
  });
  const [createExecutionForm, setCreateExecutionForm] = useState({
    template_id: '',
    batch_no: '',
    title: '',
  });

  const [signatureForm, setSignatureForm] = useState({
    meaning: '',
    reason: '',
    password: '',
  });
  const [signatureSubmitting, setSignatureSubmitting] = useState(false);
  const [signatureError, setSignatureError] = useState('');

  const activeTemplates = useMemo(
    () => templates.filter((t) => String(t?.status || '') === 'active'),
    [templates]
  );

  const loadTemplates = useCallback(async () => {
    setTemplatesLoading(true);
    setTemplatesError('');
    try {
      const items = await batchRecordsApi.listTemplates({ includeVersions: true, includeObsolete: true, limit: 200 });
      setTemplates(items);
      if (!createExecutionForm.template_id) {
        const first = items.find((t) => String(t?.status || '') === 'active') || items[0];
        if (first?.template_id) {
          setCreateExecutionForm((prev) => ({ ...prev, template_id: first.template_id }));
        }
      }
    } catch (err) {
      setTemplates([]);
      setTemplatesError(mapUserFacingErrorMessage(err?.message, '加载模板失败'));
    } finally {
      setTemplatesLoading(false);
    }
  }, [createExecutionForm.template_id]);

  const loadExecutions = useCallback(async () => {
    setExecutionsLoading(true);
    setExecutionsError('');
    try {
      const items = await batchRecordsApi.listExecutions({ limit: 200 });
      setExecutions(items);
    } catch (err) {
      setExecutions([]);
      setExecutionsError(mapUserFacingErrorMessage(err?.message, '加载执行记录失败'));
    } finally {
      setExecutionsLoading(false);
    }
  }, []);

  const loadDetail = useCallback(async (executionId) => {
    const clean = String(executionId || '').trim();
    if (!clean) {
      setSelectedExecutionId('');
      setDetail(null);
      setStepDrafts({});
      setStepPhotoDrafts({});
      return;
    }
    setDetailLoading(true);
    setDetailError('');
    try {
      const payload = await batchRecordsApi.getExecution(clean);
      setSelectedExecutionId(clean);
      setDetail(payload);
      const templateSteps = Array.isArray(payload?.bundle?.template?.steps) ? payload.bundle.template.steps : [];
      const latest = payload?.bundle?.latest_steps || {};
      const drafts = {};
      templateSteps.forEach((step) => {
        const key = String(step?.key || '').trim();
        if (!key) return;
        drafts[key] = safeJson(latest?.[key]?.payload ?? {});
      });
      setStepDrafts(drafts);
      setStepPhotoDrafts({});
    } catch (err) {
      setDetail(null);
      setStepDrafts({});
      setStepPhotoDrafts({});
      setDetailError(mapUserFacingErrorMessage(err?.message, '加载批记录失败'));
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedExecutionId) return;
    const firstExecutionId = String(executions?.[0]?.execution_id || '').trim();
    if (!firstExecutionId) return;
    loadDetail(firstExecutionId);
  }, [executions, loadDetail, selectedExecutionId]);

  useEffect(() => {
    loadTemplates();
    loadExecutions();
  }, [loadTemplates, loadExecutions]);

  const handlePublishTemplate = useCallback(async (templateId) => {
    try {
      await batchRecordsApi.publishTemplate(templateId);
      await loadTemplates();
    } catch (err) {
      setTemplatesError(mapUserFacingErrorMessage(err?.message, '发布失败'));
    }
  }, [loadTemplates]);

  const handleCreateTemplate = useCallback(async () => {
    setTemplatesError('');
    const steps = parseJsonStrict(createTemplateForm.stepsJson, 'template_steps_invalid_json');
    if (!Array.isArray(steps)) throw new Error('template_steps_invalid_json');
    const meta = parseJsonStrict(createTemplateForm.metaJson, 'template_meta_invalid_json');
    if (meta !== null && (typeof meta !== 'object' || Array.isArray(meta))) throw new Error('template_meta_invalid_json');
    await batchRecordsApi.createTemplate({
      template_code: createTemplateForm.template_code,
      template_name: createTemplateForm.template_name,
      steps,
      meta: meta || {},
    });
    setCreateTemplateForm((prev) => ({ ...prev, template_code: '', template_name: '' }));
    await loadTemplates();
  }, [createTemplateForm, loadTemplates]);

  const handleCreateVersion = useCallback(async () => {
    setTemplatesError('');
    const steps = parseJsonStrict(createVersionForm.stepsJson, 'template_steps_invalid_json');
    if (!Array.isArray(steps)) throw new Error('template_steps_invalid_json');
    const meta = parseJsonStrict(createVersionForm.metaJson, 'template_meta_invalid_json');
    if (meta !== null && (typeof meta !== 'object' || Array.isArray(meta))) throw new Error('template_meta_invalid_json');
    await batchRecordsApi.createTemplateVersion(createVersionForm.template_code, {
      template_name: createVersionForm.template_name,
      steps,
      meta: meta || {},
    });
    setCreateVersionForm((prev) => ({ ...prev, template_code: '', template_name: '' }));
    await loadTemplates();
  }, [createVersionForm, loadTemplates]);

  const handleCreateExecution = useCallback(async () => {
    setExecutionsError('');
    const bundle = await batchRecordsApi.createExecution({
      template_id: createExecutionForm.template_id,
      batch_no: createExecutionForm.batch_no,
      title: createExecutionForm.title || undefined,
    });
    const executionId = bundle?.execution?.execution_id;
    setCreateExecutionForm((prev) => ({ ...prev, batch_no: '', title: '' }));
    await loadExecutions();
    if (executionId) await loadDetail(executionId);
  }, [createExecutionForm, loadExecutions, loadDetail]);

  const handleWriteStep = useCallback(async (stepKey) => {
    const key = String(stepKey || '').trim();
    if (!key) return;
    const payload = parseJsonStrict(stepDrafts[key], 'step_payload_invalid_json');
    if (payload === null || typeof payload !== 'object' || Array.isArray(payload)) {
      throw new Error('step_payload_invalid_json');
    }
    const pendingPhotos = Array.isArray(stepPhotoDrafts[key]) ? stepPhotoDrafts[key] : [];
    const nextPayload = { ...payload };
    if (pendingPhotos.length > 0) {
      const existingPhotos = Array.isArray(nextPayload[STEP_PHOTO_FIELD])
        ? nextPayload[STEP_PHOTO_FIELD].filter((item) => !!item && typeof item === 'object')
        : [];
      nextPayload[STEP_PHOTO_FIELD] = [...existingPhotos, ...pendingPhotos];
    }
    await batchRecordsApi.writeStep(selectedExecutionId, { step_key: key, payload: nextPayload });
    setStepPhotoDrafts((prev) => ({ ...prev, [key]: [] }));
    await loadDetail(selectedExecutionId);
  }, [loadDetail, selectedExecutionId, stepDrafts, stepPhotoDrafts]);

  const handleSelectStepPhotos = useCallback(async (stepKey, files) => {
    const key = String(stepKey || '').trim();
    if (!key) return;
    const photoEvidence = await readFilesAsPhotoEvidence(files);
    setStepPhotoDrafts((prev) => ({ ...prev, [key]: photoEvidence }));
  }, []);

  const handleSignOrReview = useCallback(async (kind) => {
    setSignatureError('');
    setSignatureSubmitting(true);
    try {
      const challenge = await electronicSignatureApi.requestSignatureChallenge(signatureForm.password);
      const signToken = challenge?.sign_token;
      if (!signToken) throw new Error('sign_token_invalid');
      const payload = {
        sign_token: signToken,
        meaning: signatureForm.meaning,
        reason: signatureForm.reason,
      };
      if (kind === 'review') {
        await batchRecordsApi.reviewExecution(selectedExecutionId, payload);
      } else {
        await batchRecordsApi.signExecution(selectedExecutionId, payload);
      }
      setSignatureForm((prev) => ({ ...prev, password: '' }));
      await loadDetail(selectedExecutionId);
    } catch (err) {
      setSignatureError(mapUserFacingErrorMessage(err?.message, '签名失败'));
    } finally {
      setSignatureSubmitting(false);
    }
  }, [signatureForm, selectedExecutionId, loadDetail]);

  const handleExport = useCallback(async () => {
    const payload = await batchRecordsApi.exportExecution(selectedExecutionId);
    const filename = String(payload?.filename || `batch-record-${selectedExecutionId}.json`);
    const blob = new Blob([safeJson(payload?.export ?? {})], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    try {
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
    } finally {
      URL.revokeObjectURL(url);
    }
  }, [selectedExecutionId]);

  const execution = detail?.bundle?.execution || null;
  const template = detail?.bundle?.template || null;
  const status = String(execution?.status || '');
  const editable = permissions.execute && status === 'in_progress';
  const canSignNow = permissions.sign && status === 'in_progress';
  const canReviewNow = permissions.review && status === 'signed';
  const canExportNow = permissions.export && (status === 'signed' || status === 'reviewed');

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <section style={PANEL_STYLE} data-testid="batch-records-capabilities">
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <h3 style={{ margin: 0 }}>能力</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <span style={pillStyle(permissions.templateManage ? '#ccfbf1' : '#e2e8f0', permissions.templateManage ? '#115e59' : '#475569')}>template_manage</span>
            <span style={pillStyle(permissions.execute ? '#ccfbf1' : '#e2e8f0', permissions.execute ? '#115e59' : '#475569')}>execute</span>
            <span style={pillStyle(permissions.sign ? '#ccfbf1' : '#e2e8f0', permissions.sign ? '#115e59' : '#475569')}>sign</span>
            <span style={pillStyle(permissions.review ? '#ccfbf1' : '#e2e8f0', permissions.review ? '#115e59' : '#475569')}>review</span>
            <span style={pillStyle(permissions.export ? '#ccfbf1' : '#e2e8f0', permissions.export ? '#115e59' : '#475569')}>export</span>
          </div>
        </div>
      </section>

      <section style={{ ...PANEL_STYLE, display: 'grid', gap: 12 }} data-testid="batch-records-templates">
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <h3 style={{ margin: 0 }}>模板</h3>
          <button type="button" style={buttonStyle('secondary')} onClick={loadTemplates} disabled={templatesLoading}>刷新</button>
        </div>
        {templatesError ? <div style={{ color: '#991b1b' }} data-testid="batch-records-templates-error">{templatesError}</div> : null}
        {templatesLoading ? <div style={{ color: '#475569' }}>正在加载...</div> : (
          <div style={{ display: 'grid', gap: 10 }}>
            {templates.length === 0 ? <div style={{ color: '#475569' }}>暂无模板。</div> : templates.map((tpl) => (
              <div key={tpl.template_id} style={{ border: '1px solid #e2e8f0', borderRadius: 12, padding: 12, display: 'grid', gap: 6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                  <strong>{String(tpl.template_code)} v{String(tpl.version_no)} · {String(tpl.template_name)}</strong>
                  <span style={pillStyle(tpl.status === 'active' ? '#dcfce7' : tpl.status === 'draft' ? '#e0f2fe' : '#fee2e2', tpl.status === 'active' ? '#166534' : tpl.status === 'draft' ? '#075985' : '#991b1b')}>{String(tpl.status)}</span>
                </div>
                <div style={{ color: '#64748b', fontSize: '0.92rem' }}>updated_at: {formatTime(tpl.updated_at_ms)}</div>
                {permissions.templateManage && tpl.status !== 'active' ? (
                  <button
                    type="button"
                    style={buttonStyle()}
                    onClick={() => handlePublishTemplate(tpl.template_id)}
                    data-testid={`batch-records-template-publish-${tpl.template_id}`}
                  >
                    发布为 active
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        )}

        {permissions.templateManage ? (
          <div style={{ display: 'grid', gap: 14, borderTop: '1px solid #e2e8f0', paddingTop: 14 }}>
            <h4 style={{ margin: 0 }}>模板管理</h4>
            <div style={{ display: 'grid', gap: 10 }}>
              <strong>新建模板（v1）</strong>
              <input
                style={INPUT_STYLE}
                value={createTemplateForm.template_code}
                onChange={(e) => setCreateTemplateForm((prev) => ({ ...prev, template_code: e.target.value }))}
                placeholder="模板编码（例如 BR-TPL-001）"
              />
              <input
                style={INPUT_STYLE}
                value={createTemplateForm.template_name}
                onChange={(e) => setCreateTemplateForm((prev) => ({ ...prev, template_name: e.target.value }))}
                placeholder="模板名称"
              />
              <textarea
                style={TEXTAREA_STYLE}
                value={createTemplateForm.stepsJson}
                onChange={(e) => setCreateTemplateForm((prev) => ({ ...prev, stepsJson: e.target.value }))}
              />
              <textarea
                style={TEXTAREA_STYLE}
                value={createTemplateForm.metaJson}
                onChange={(e) => setCreateTemplateForm((prev) => ({ ...prev, metaJson: e.target.value }))}
              />
              <button
                type="button"
                style={buttonStyle()}
                onClick={() => handleCreateTemplate().catch((err) => setTemplatesError(mapUserFacingErrorMessage(err?.message, '创建失败')))}
                data-testid="batch-records-template-create"
              >
                创建模板
              </button>
            </div>

            <div style={{ display: 'grid', gap: 10 }}>
              <strong>创建新版本（草稿）</strong>
              <input
                style={INPUT_STYLE}
                value={createVersionForm.template_code}
                onChange={(e) => setCreateVersionForm((prev) => ({ ...prev, template_code: e.target.value }))}
                placeholder="已有模板编码"
              />
              <input
                style={INPUT_STYLE}
                value={createVersionForm.template_name}
                onChange={(e) => setCreateVersionForm((prev) => ({ ...prev, template_name: e.target.value }))}
                placeholder="模板名称"
              />
              <textarea
                style={TEXTAREA_STYLE}
                value={createVersionForm.stepsJson}
                onChange={(e) => setCreateVersionForm((prev) => ({ ...prev, stepsJson: e.target.value }))}
              />
              <textarea
                style={TEXTAREA_STYLE}
                value={createVersionForm.metaJson}
                onChange={(e) => setCreateVersionForm((prev) => ({ ...prev, metaJson: e.target.value }))}
              />
              <button
                type="button"
                style={buttonStyle('secondary')}
                onClick={() => handleCreateVersion().catch((err) => setTemplatesError(mapUserFacingErrorMessage(err?.message, '创建失败')))}
                data-testid="batch-records-template-version-create"
              >
                创建新版本
              </button>
            </div>
          </div>
        ) : null}
      </section>

      <section style={{ ...PANEL_STYLE, display: 'grid', gap: 12 }} data-testid="batch-records-executions">
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <h3 style={{ margin: 0 }}>执行</h3>
          <button type="button" style={buttonStyle('secondary')} onClick={loadExecutions} disabled={executionsLoading}>刷新</button>
        </div>
        {executionsError ? <div style={{ color: '#991b1b' }} data-testid="batch-records-executions-error">{executionsError}</div> : null}

        {permissions.execute ? (
          <div style={{ display: 'grid', gap: 10 }}>
            <strong>新建执行实例</strong>
            <select
              style={INPUT_STYLE}
              value={createExecutionForm.template_id}
              onChange={(e) => setCreateExecutionForm((prev) => ({ ...prev, template_id: e.target.value }))}
            >
              <option value="">选择已启用模板</option>
              {activeTemplates.map((tpl) => (
                <option key={tpl.template_id} value={tpl.template_id}>
                  {tpl.template_code} v{tpl.version_no} · {tpl.template_name}
                </option>
              ))}
            </select>
            <input
              style={INPUT_STYLE}
              value={createExecutionForm.batch_no}
              onChange={(e) => setCreateExecutionForm((prev) => ({ ...prev, batch_no: e.target.value }))}
              placeholder="批号（例如 B-0001）"
            />
            <input
              style={INPUT_STYLE}
              value={createExecutionForm.title}
              onChange={(e) => setCreateExecutionForm((prev) => ({ ...prev, title: e.target.value }))}
              placeholder="标题（可选）"
            />
            <button
              type="button"
              style={buttonStyle()}
              onClick={() => handleCreateExecution().catch((err) => setExecutionsError(mapUserFacingErrorMessage(err?.message, '创建失败')))}
              data-testid="batch-records-execution-create"
            >
              创建执行
            </button>
          </div>
        ) : (
          <div style={{ color: '#991b1b' }} data-testid="batch-records-execution-create-denied">
            缺少 batch_records.execute，无法创建执行。
          </div>
        )}

        {executionsLoading ? <div style={{ color: '#475569' }}>正在加载...</div> : (
          <div style={{ display: 'grid', gap: 8 }}>
            {executions.length === 0 ? <div style={{ color: '#475569' }}>暂无执行记录。</div> : executions.map((item) => (
              <button
                key={item.execution_id}
                type="button"
                onClick={() => loadDetail(item.execution_id)}
                style={{
                  textAlign: 'left',
                  border: selectedExecutionId === item.execution_id ? '1px solid #14b8a6' : '1px solid #e2e8f0',
                  borderRadius: 12,
                  padding: 12,
                  background: selectedExecutionId === item.execution_id ? '#f0fdfa' : '#ffffff',
                  cursor: 'pointer',
                }}
                data-testid={`batch-records-execution-item-${item.execution_id}`}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                  <strong>{String(item.title || item.execution_id)}</strong>
                  <span style={pillStyle('#f1f5f9', '#475569')}>{String(item.status)}</span>
                </div>
                <div style={{ marginTop: 6, color: '#64748b', fontSize: '0.92rem' }}>
                  批号：{String(item.batch_no)} · {String(item.template_code)} v{String(item.template_version_no)}
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      <section style={{ ...PANEL_STYLE, display: 'grid', gap: 12 }} data-testid="batch-records-detail">
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <h3 style={{ margin: 0 }}>详情</h3>
          {selectedExecutionId ? (
            <button type="button" style={buttonStyle('secondary')} onClick={() => loadDetail(selectedExecutionId)} disabled={detailLoading}>
              刷新详情
            </button>
          ) : null}
        </div>
        {detailError ? <div style={{ color: '#991b1b' }} data-testid="batch-records-detail-error">{detailError}</div> : null}
        {!selectedExecutionId ? <div style={{ color: '#475569' }}>请选择一条执行记录。</div> : null}
        {detailLoading ? <div style={{ color: '#475569' }}>正在加载...</div> : null}
        {selectedExecutionId && !detailLoading && detail?.bundle ? (
          <div style={{ display: 'grid', gap: 14 }}>
            <div style={{ display: 'grid', gap: 6, color: '#0f172a' }}>
              <div><strong>Execution:</strong> {String(execution?.execution_id)}</div>
              <div><strong>Status:</strong> {String(execution?.status)}</div>
              <div><strong>Batch No:</strong> {String(execution?.batch_no)}</div>
              <div><strong>Started:</strong> {formatTime(execution?.started_at_ms)}</div>
              <div><strong>Template:</strong> {String(template?.template_code)} v{String(template?.version_no)} · {String(template?.template_name)}</div>
            </div>

            <div style={{ display: 'grid', gap: 10 }}>
              <h4 style={{ margin: 0 }}>步骤（实时写入，服务器时间留痕）</h4>
              {Array.isArray(template?.steps) && template.steps.length > 0 ? template.steps.map((step) => {
                const key = String(step?.key || '').trim();
                if (!key) return null;
                const latest = detail?.bundle?.latest_steps?.[key] || null;
                const latestPhotos = Array.isArray(latest?.payload?.[STEP_PHOTO_FIELD])
                  ? latest.payload[STEP_PHOTO_FIELD]
                  : [];
                const pendingPhotos = Array.isArray(stepPhotoDrafts[key]) ? stepPhotoDrafts[key] : [];
                return (
                  <div key={key} style={{ border: '1px solid #e2e8f0', borderRadius: 12, padding: 12, display: 'grid', gap: 8 }} data-testid={`batch-records-step-${key}`}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                      <strong>{key} · {String(step?.title || '')}</strong>
                      <span style={pillStyle('#f1f5f9', '#475569')}>{formatTime(latest?.created_at_ms)}</span>
                    </div>
                    <div style={{ color: '#64748b', fontSize: '0.92rem' }}>
                      latest_by: {String(latest?.created_by_username || '-')}
                    </div>
                    <textarea
                      style={TEXTAREA_STYLE}
                      value={String(stepDrafts[key] ?? '{}')}
                      onChange={(e) => setStepDrafts((prev) => ({ ...prev, [key]: e.target.value }))}
                      disabled={!editable}
                    />
                    <div style={{ display: 'grid', gap: 8 }}>
                      <label style={{ display: 'grid', gap: 6, color: '#334155', fontSize: '0.92rem', fontWeight: 600 }}>
                        现场拍照证据
                        <input
                          type="file"
                          accept="image/*"
                          capture="environment"
                          multiple
                          disabled={!editable}
                          data-testid={`batch-records-step-photo-${key}`}
                          onChange={async (event) => {
                            try {
                              await handleSelectStepPhotos(key, event.target.files);
                              setDetailError('');
                            } catch (err) {
                              setDetailError(mapUserFacingErrorMessage(err?.message, '照片处理失败'));
                            } finally {
                              event.target.value = '';
                            }
                          }}
                        />
                      </label>
                      {pendingPhotos.length > 0 ? (
                        <div
                          style={{ color: '#0f766e', fontSize: '0.92rem' }}
                          data-testid={`batch-records-step-photo-pending-${key}`}
                        >
                          待写入照片: {pendingPhotos.map((item) => String(item.filename || 'photo')).join(', ')}
                        </div>
                      ) : null}
                      {latestPhotos.length > 0 ? (
                        <div
                          style={{ color: '#475569', fontSize: '0.92rem' }}
                          data-testid={`batch-records-step-photo-latest-${key}`}
                        >
                          最近一次已保存照片: {latestPhotos.map((item) => String(item.filename || 'photo')).join(', ')}
                        </div>
                      ) : null}
                    </div>
                    <button
                      type="button"
                      style={buttonStyle(editable ? 'primary' : 'secondary')}
                      disabled={!editable}
                      onClick={() => handleWriteStep(key).catch((err) => setDetailError(mapUserFacingErrorMessage(err?.message, '写入失败')))}
                      data-testid={`batch-records-step-save-${key}`}
                    >
                      写入步骤
                    </button>
                  </div>
                );
              }) : <div style={{ color: '#991b1b' }}>模板步骤为空，无法执行。</div>}
            </div>

            <div style={{ display: 'grid', gap: 10 }}>
              <h4 style={{ margin: 0 }}>签名 / 复核（复用电子签名）</h4>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <span style={pillStyle(detail?.signed_signature ? '#dcfce7' : '#e2e8f0', detail?.signed_signature ? '#166534' : '#475569')}>
                  签名: {detail?.signed_signature ? '已签' : '未签'}
                </span>
                <span style={pillStyle(detail?.reviewed_signature ? '#dcfce7' : '#e2e8f0', detail?.reviewed_signature ? '#166534' : '#475569')}>
                  复核: {detail?.reviewed_signature ? '已复核' : '未复核'}
                </span>
              </div>
              {detail?.signed_signature ? (
                <div style={{ color: '#475569', fontSize: '0.92rem' }}>
                  签名人：{String(detail.signed_signature.signed_by_username)}，时间：{formatTime(detail.signed_signature.signed_at_ms)}，校验结果：{String(detail.signed_signature.signature_verified)}
                </div>
              ) : null}
              {detail?.reviewed_signature ? (
                <div style={{ color: '#475569', fontSize: '0.92rem' }}>
                  复核人：{String(detail.reviewed_signature.signed_by_username)}，时间：{formatTime(detail.reviewed_signature.signed_at_ms)}，校验结果：{String(detail.reviewed_signature.signature_verified)}
                </div>
              ) : null}

              <div style={{ display: 'grid', gap: 10, borderTop: '1px solid #e2e8f0', paddingTop: 14 }}>
                <input
                  style={INPUT_STYLE}
                  value={signatureForm.meaning}
                  onChange={(e) => setSignatureForm((prev) => ({ ...prev, meaning: e.target.value }))}
                  placeholder="签名含义"
                />
                <input
                  style={INPUT_STYLE}
                  value={signatureForm.reason}
                  onChange={(e) => setSignatureForm((prev) => ({ ...prev, reason: e.target.value }))}
                  placeholder="签名原因"
                />
                <input
                  style={INPUT_STYLE}
                  type="password"
                  value={signatureForm.password}
                  onChange={(e) => setSignatureForm((prev) => ({ ...prev, password: e.target.value }))}
                  placeholder="电子签名口令"
                  autoComplete="current-password"
                />
                {signatureError ? <div style={{ color: '#991b1b' }} data-testid="batch-records-signature-error">{signatureError}</div> : null}
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    style={buttonStyle()}
                    disabled={!canSignNow || signatureSubmitting}
                    onClick={() => handleSignOrReview('sign')}
                    data-testid="batch-records-sign"
                  >
                    签名
                  </button>
                  <button
                    type="button"
                    style={buttonStyle('secondary')}
                    disabled={!canReviewNow || signatureSubmitting}
                    onClick={() => handleSignOrReview('review')}
                    data-testid="batch-records-review"
                  >
                    复核
                  </button>
                  <button
                    type="button"
                    style={buttonStyle('secondary')}
                    disabled={!canExportNow}
                    onClick={() => handleExport().catch((err) => setDetailError(mapUserFacingErrorMessage(err?.message, '导出失败')))}
                    data-testid="batch-records-export"
                  >
                    导出 JSON
                  </button>
                </div>
                <div style={{ color: '#64748b', fontSize: '0.92rem' }}>
                  editable={String(editable)} · sign={String(canSignNow)} · review={String(canReviewNow)} · export={String(canExportNow)}
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
