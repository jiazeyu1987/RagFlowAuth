import React, { useCallback, useEffect, useMemo, useState } from 'react';
import operationApprovalApi from '../features/operationApproval/api';
import { usersApi } from '../features/users/api';

const cardStyle = {
  background: '#ffffff',
  border: '1px solid #e5e7eb',
  borderRadius: '14px',
  padding: '16px',
};

const buttonStyle = {
  border: '1px solid #d1d5db',
  borderRadius: '10px',
  background: '#ffffff',
  color: '#111827',
  cursor: 'pointer',
  padding: '8px 12px',
};

const primaryButtonStyle = {
  ...buttonStyle,
  background: '#2563eb',
  borderColor: '#2563eb',
  color: '#ffffff',
};

const createDraftFromWorkflow = (workflow) => ({
  operation_type: workflow?.operation_type || '',
  operation_label: workflow?.operation_label || workflow?.operation_type || '',
  name: workflow?.name || '',
  is_configured: !!workflow?.is_configured,
  steps: Array.isArray(workflow?.steps) && workflow.steps.length > 0
    ? workflow.steps.map((step, index) => ({
        step_no: Number(step?.step_no || index + 1),
        step_name: String(step?.step_name || ''),
        approver_user_ids: Array.isArray(step?.approver_user_ids)
          ? step.approver_user_ids.map((item) => String(item))
          : [],
      }))
    : [{ step_no: 1, step_name: '第 1 层', approver_user_ids: [] }],
});

const normalizeUsers = (response) => {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.items)) return response.items;
  return [];
};

export default function ApprovalConfig() {
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState('');
  const [error, setError] = useState('');
  const [saveMessage, setSaveMessage] = useState('');
  const [drafts, setDrafts] = useState([]);
  const [users, setUsers] = useState([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [workflowResponse, userResponse] = await Promise.all([
        operationApprovalApi.listWorkflows(),
        usersApi.list({ limit: 500, status: 'active' }),
      ]);
      const workflowItems = Array.isArray(workflowResponse?.items) ? workflowResponse.items : [];
      setDrafts(workflowItems.map(createDraftFromWorkflow));
      setUsers(normalizeUsers(userResponse));
    } catch (requestError) {
      setError(requestError?.message || 'Failed to load approval config');
      setDrafts([]);
      setUsers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const userOptions = useMemo(
    () => users.map((user) => ({
      value: String(user?.user_id || ''),
      label: String(user?.full_name || user?.username || user?.user_id || ''),
    })).filter((item) => item.value),
    [users]
  );

  const updateDraft = useCallback((operationType, updater) => {
    setDrafts((prev) => prev.map((draft) => (
      draft.operation_type === operationType ? updater(draft) : draft
    )));
  }, []);

  const addStep = useCallback((operationType) => {
    updateDraft(operationType, (draft) => ({
      ...draft,
      steps: [
        ...(draft.steps || []),
        {
          step_no: (draft.steps || []).length + 1,
          step_name: `第 ${(draft.steps || []).length + 1} 层`,
          approver_user_ids: [],
        },
      ],
    }));
  }, [updateDraft]);

  const removeStep = useCallback((operationType, index) => {
    updateDraft(operationType, (draft) => ({
      ...draft,
      steps: (draft.steps || [])
        .filter((_, itemIndex) => itemIndex !== index)
        .map((step, stepIndex) => ({ ...step, step_no: stepIndex + 1 })),
    }));
  }, [updateDraft]);

  const updateStepField = useCallback((operationType, index, field, value) => {
    updateDraft(operationType, (draft) => ({
      ...draft,
      steps: (draft.steps || []).map((step, stepIndex) => (
        stepIndex === index ? { ...step, [field]: value } : step
      )),
    }));
  }, [updateDraft]);

  const validateDraft = (draft) => {
    const steps = Array.isArray(draft?.steps) ? draft.steps : [];
    if (steps.length === 0) return '至少保留一层审批';
    for (const step of steps) {
      if (!String(step?.step_name || '').trim()) return '每一层都必须填写名称';
      if (!Array.isArray(step?.approver_user_ids) || step.approver_user_ids.length === 0) {
        return '每一层至少选择一位审批人';
      }
    }
    return '';
  };

  const handleSave = useCallback(async (draft) => {
    const validationError = validateDraft(draft);
    if (validationError) {
      setError(`${draft.operation_label}: ${validationError}`);
      return;
    }
    setSavingKey(draft.operation_type);
    setError('');
    setSaveMessage('');
    try {
      await operationApprovalApi.updateWorkflow(draft.operation_type, {
        name: String(draft.name || '').trim() || null,
        steps: (draft.steps || []).map((step, index) => ({
          step_name: String(step.step_name || '').trim(),
          approver_user_ids: Array.from(new Set((step.approver_user_ids || []).map((item) => String(item)))),
          step_no: index + 1,
        })),
      });
      setSaveMessage(`${draft.operation_label} 审批流已保存`);
      await loadData();
    } catch (requestError) {
      setError(requestError?.message || 'Failed to save workflow');
    } finally {
      setSavingKey('');
    }
  }, [loadData]);

  return (
    <div style={{ display: 'grid', gap: '16px' }} data-testid="approval-config-page">
      <div style={{ ...cardStyle, display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#111827' }}>审批配置</div>
          <div style={{ color: '#4b5563', marginTop: '4px' }}>为四类操作分别设置审批层级和每层审批人。</div>
        </div>
        <button type="button" onClick={loadData} style={buttonStyle}>刷新</button>
      </div>

      {error ? (
        <div
          data-testid="approval-config-error"
          style={{ ...cardStyle, borderColor: '#fecaca', background: '#fef2f2', color: '#991b1b' }}
        >
          {error}
        </div>
      ) : null}

      {saveMessage ? (
        <div
          data-testid="approval-config-success"
          style={{ ...cardStyle, borderColor: '#bbf7d0', background: '#f0fdf4', color: '#166534' }}
        >
          {saveMessage}
        </div>
      ) : null}

      {loading ? (
        <div style={cardStyle}>正在加载审批配置...</div>
      ) : (
        <div style={{ display: 'grid', gap: '16px' }}>
          {drafts.map((draft) => (
            <section
              key={draft.operation_type}
              style={cardStyle}
              data-testid={`approval-config-card-${draft.operation_type}`}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontWeight: 700, color: '#111827' }}>{draft.operation_label}</div>
                  <div style={{ color: '#6b7280', marginTop: '4px' }}>{draft.operation_type}</div>
                </div>
                <button
                  type="button"
                  data-testid={`approval-config-save-${draft.operation_type}`}
                  onClick={() => handleSave(draft)}
                  disabled={savingKey === draft.operation_type}
                  style={primaryButtonStyle}
                >
                  {savingKey === draft.operation_type ? '保存中...' : '保存'}
                </button>
              </div>

              <div style={{ marginTop: '14px', display: 'grid', gap: '12px' }}>
                <label style={{ display: 'grid', gap: '6px' }}>
                  <span style={{ fontWeight: 600, color: '#111827' }}>工作流名称</span>
                  <input
                    type="text"
                    value={draft.name}
                    data-testid={`approval-config-name-${draft.operation_type}`}
                    onChange={(event) => updateDraft(draft.operation_type, (item) => ({ ...item, name: event.target.value }))}
                    style={{ padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '10px' }}
                  />
                </label>

                {(draft.steps || []).map((step, index) => (
                  <div
                    key={`${draft.operation_type}-${step.step_no}`}
                    style={{ border: '1px solid #e5e7eb', borderRadius: '12px', padding: '12px' }}
                    data-testid={`approval-config-step-${draft.operation_type}-${index}`}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                      <strong>{`第 ${index + 1} 层`}</strong>
                      <button
                        type="button"
                        onClick={() => removeStep(draft.operation_type, index)}
                        disabled={(draft.steps || []).length <= 1}
                        style={buttonStyle}
                      >
                        删除本层
                      </button>
                    </div>

                    <div style={{ marginTop: '12px', display: 'grid', gap: '12px' }}>
                      <label style={{ display: 'grid', gap: '6px' }}>
                        <span style={{ fontWeight: 600, color: '#111827' }}>层名称</span>
                        <input
                          type="text"
                          value={step.step_name}
                          data-testid={`approval-config-step-name-${draft.operation_type}-${index}`}
                          onChange={(event) => updateStepField(draft.operation_type, index, 'step_name', event.target.value)}
                          style={{ padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '10px' }}
                        />
                      </label>

                      <label style={{ display: 'grid', gap: '6px' }}>
                        <span style={{ fontWeight: 600, color: '#111827' }}>审批人</span>
                        <select
                          multiple
                          size={Math.min(Math.max(userOptions.length, 4), 8)}
                          data-testid={`approval-config-step-approvers-${draft.operation_type}-${index}`}
                          value={step.approver_user_ids}
                          onChange={(event) => {
                            const values = Array.from(event.target.selectedOptions).map((option) => option.value);
                            updateStepField(draft.operation_type, index, 'approver_user_ids', values);
                          }}
                          style={{ padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '10px' }}
                        >
                          {userOptions.map((option) => (
                            <option key={option.value} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      </label>
                    </div>
                  </div>
                ))}

                <div>
                  <button
                    type="button"
                    data-testid={`approval-config-add-step-${draft.operation_type}`}
                    onClick={() => addStep(draft.operation_type)}
                    style={buttonStyle}
                  >
                    增加一层
                  </button>
                </div>
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
