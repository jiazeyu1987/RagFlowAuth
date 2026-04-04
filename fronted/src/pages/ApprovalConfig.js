import React, { useCallback, useEffect, useMemo, useState } from 'react';
import operationApprovalApi from '../features/operationApproval/api';
import { usersApi } from '../features/users/api';

const WORKFLOW_MEMBER_TYPE_USER = 'user';
const WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE = 'special_role';
const SPECIAL_ROLE_DIRECT_MANAGER = 'direct_manager';

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

const createEmptyMember = () => ({
  member_type: WORKFLOW_MEMBER_TYPE_USER,
  member_ref: '',
});

const createEmptyStep = (stepNo) => ({
  step_no: Number(stepNo),
  step_name: `第 ${stepNo} 层`,
  members: [createEmptyMember()],
});

const normalizeUsers = (response) => {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.items)) return response.items;
  return [];
};

const normalizeMembers = (step) => {
  if (Array.isArray(step?.members) && step.members.length > 0) {
    return step.members.map((member) => ({
      member_type: String(member?.member_type || WORKFLOW_MEMBER_TYPE_USER),
      member_ref: String(member?.member_ref || ''),
    }));
  }
  if (Array.isArray(step?.approver_user_ids) && step.approver_user_ids.length > 0) {
    return step.approver_user_ids.map((memberRef) => ({
      member_type: WORKFLOW_MEMBER_TYPE_USER,
      member_ref: String(memberRef || ''),
    }));
  }
  return [createEmptyMember()];
};

const createDraftFromWorkflow = (workflow) => ({
  operation_type: workflow?.operation_type || '',
  operation_label: workflow?.operation_label || workflow?.operation_type || '',
  name: workflow?.name || '',
  is_configured: !!workflow?.is_configured,
  steps:
    Array.isArray(workflow?.steps) && workflow.steps.length > 0
      ? workflow.steps.map((step, index) => ({
          step_no: Number(step?.step_no || index + 1),
          step_name: String(step?.step_name || ''),
          members: normalizeMembers(step),
        }))
      : [createEmptyStep(1)],
});

const specialRoleLabel = (memberRef) => {
  if (memberRef === SPECIAL_ROLE_DIRECT_MANAGER) return '直属主管';
  return memberRef || '-';
};

export default function ApprovalConfig() {
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState('');
  const [error, setError] = useState('');
  const [saveMessage, setSaveMessage] = useState('');
  const [drafts, setDrafts] = useState([]);
  const [users, setUsers] = useState([]);
  const [currentOperationType, setCurrentOperationType] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [workflowResponse, userResponse] = await Promise.all([
        operationApprovalApi.listWorkflows(),
        usersApi.list({ limit: 500, status: 'active' }),
      ]);
      const workflowItems = Array.isArray(workflowResponse?.items) ? workflowResponse.items : [];
      const nextDrafts = workflowItems.map(createDraftFromWorkflow);
      setDrafts(nextDrafts);
      setUsers(normalizeUsers(userResponse));
      setCurrentOperationType((prev) => {
        if (prev && nextDrafts.some((draft) => draft.operation_type === prev)) return prev;
        return nextDrafts[0]?.operation_type || '';
      });
    } catch (requestError) {
      setError(requestError?.message || 'Failed to load approval config');
      setDrafts([]);
      setUsers([]);
      setCurrentOperationType('');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const userOptions = useMemo(
    () =>
      users
        .map((user) => ({
          value: String(user?.user_id || ''),
          label: String(user?.full_name || user?.username || user?.user_id || ''),
        }))
        .filter((item) => item.value),
    [users]
  );

  const currentDraft = useMemo(
    () => drafts.find((draft) => draft.operation_type === currentOperationType) || null,
    [currentOperationType, drafts]
  );

  const updateDraft = useCallback((operationType, updater) => {
    setDrafts((prev) =>
      prev.map((draft) => (draft.operation_type === operationType ? updater(draft) : draft))
    );
  }, []);

  const updateCurrentDraft = useCallback(
    (updater) => {
      if (!currentOperationType) return;
      updateDraft(currentOperationType, updater);
    },
    [currentOperationType, updateDraft]
  );

  const addStep = useCallback(() => {
    updateCurrentDraft((draft) => ({
      ...draft,
      steps: [...(draft.steps || []), createEmptyStep((draft.steps || []).length + 1)],
    }));
  }, [updateCurrentDraft]);

  const removeStep = useCallback(
    (index) => {
      updateCurrentDraft((draft) => ({
        ...draft,
        steps: (draft.steps || [])
          .filter((_, stepIndex) => stepIndex !== index)
          .map((step, stepIndex) => ({ ...step, step_no: stepIndex + 1 })),
      }));
    },
    [updateCurrentDraft]
  );

  const updateStepField = useCallback(
    (index, field, value) => {
      updateCurrentDraft((draft) => ({
        ...draft,
        steps: (draft.steps || []).map((step, stepIndex) =>
          stepIndex === index ? { ...step, [field]: value } : step
        ),
      }));
    },
    [updateCurrentDraft]
  );

  const addMember = useCallback(
    (stepIndex) => {
      updateCurrentDraft((draft) => ({
        ...draft,
        steps: (draft.steps || []).map((step, index) =>
          index === stepIndex ? { ...step, members: [...(step.members || []), createEmptyMember()] } : step
        ),
      }));
    },
    [updateCurrentDraft]
  );

  const removeMember = useCallback(
    (stepIndex, memberIndex) => {
      updateCurrentDraft((draft) => ({
        ...draft,
        steps: (draft.steps || []).map((step, index) => {
          if (index !== stepIndex) return step;
          const nextMembers = (step.members || []).filter((_, currentMemberIndex) => currentMemberIndex !== memberIndex);
          return {
            ...step,
            members: nextMembers.length > 0 ? nextMembers : [createEmptyMember()],
          };
        }),
      }));
    },
    [updateCurrentDraft]
  );

  const updateMemberField = useCallback(
    (stepIndex, memberIndex, field, value) => {
      updateCurrentDraft((draft) => ({
        ...draft,
        steps: (draft.steps || []).map((step, index) => {
          if (index !== stepIndex) return step;
          return {
            ...step,
            members: (step.members || []).map((member, currentMemberIndex) => {
              if (currentMemberIndex !== memberIndex) return member;
              const nextMember = { ...member, [field]: value };
              if (field === 'member_type' && value === WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE) {
                nextMember.member_ref = SPECIAL_ROLE_DIRECT_MANAGER;
              }
              if (field === 'member_type' && value === WORKFLOW_MEMBER_TYPE_USER) {
                nextMember.member_ref = '';
              }
              return nextMember;
            }),
          };
        }),
      }));
    },
    [updateCurrentDraft]
  );

  const validateDraft = useCallback((draft) => {
    const steps = Array.isArray(draft?.steps) ? draft.steps : [];
    if (steps.length === 0) return '至少保留一层审批';
    for (const step of steps) {
      if (!String(step?.step_name || '').trim()) return '每一层都必须填写名称';
      const members = Array.isArray(step?.members) ? step.members : [];
      if (members.length === 0) return '每一层至少配置一个成员';
      for (const member of members) {
        const memberType = String(member?.member_type || '').trim();
        const memberRef = String(member?.member_ref || '').trim();
        if (!memberType) return '审批成员类型不能为空';
        if (memberType === WORKFLOW_MEMBER_TYPE_USER && !memberRef) return '固定用户成员必须选择用户';
        if (memberType === WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE && memberRef !== SPECIAL_ROLE_DIRECT_MANAGER) {
          return '当前仅支持直属主管特殊角色';
        }
      }
    }
    return '';
  }, []);

  const handleSave = useCallback(async () => {
    if (!currentDraft) return;
    const validationError = validateDraft(currentDraft);
    if (validationError) {
      setError(`${currentDraft.operation_label}: ${validationError}`);
      return;
    }
    setSavingKey(currentDraft.operation_type);
    setError('');
    setSaveMessage('');
    try {
      await operationApprovalApi.updateWorkflow(currentDraft.operation_type, {
        name: String(currentDraft.name || '').trim() || null,
        steps: (currentDraft.steps || []).map((step, index) => ({
          step_name: String(step.step_name || '').trim(),
          step_no: index + 1,
          members: (step.members || []).map((member) => ({
            member_type: String(member.member_type || ''),
            member_ref:
              String(member.member_type || '') === WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE
                ? SPECIAL_ROLE_DIRECT_MANAGER
                : String(member.member_ref || ''),
          })),
        })),
      });
      setSaveMessage(`${currentDraft.operation_label} 审批流程已保存`);
      await loadData();
    } catch (requestError) {
      setError(requestError?.message || 'Failed to save workflow');
    } finally {
      setSavingKey('');
    }
  }, [currentDraft, loadData, validateDraft]);

  return (
    <div style={{ display: 'grid', gap: '16px' }} data-testid="approval-config-page">
      <div style={{ ...cardStyle, display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#111827' }}>审批配置</div>
          <div style={{ color: '#4b5563', marginTop: '4px' }}>用场景下拉切换当前审批流程，支持固定用户和直属主管混合配置。</div>
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
      ) : !currentDraft ? (
        <div style={cardStyle}>暂无审批场景</div>
      ) : (
        <section
          key={currentDraft.operation_type}
          style={cardStyle}
          data-testid={`approval-config-card-${currentDraft.operation_type}`}
        >
          <div style={{ display: 'grid', gap: '14px' }}>
            <label style={{ display: 'grid', gap: '6px' }}>
              <span style={{ fontWeight: 600, color: '#111827' }}>审批场景</span>
              <select
                value={currentOperationType}
                onChange={(event) => setCurrentOperationType(event.target.value)}
                data-testid="approval-config-operation-select"
                style={{ padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '10px' }}
              >
                {drafts.map((draft) => (
                  <option key={draft.operation_type} value={draft.operation_type}>
                    {draft.operation_label}
                  </option>
                ))}
              </select>
            </label>

            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
              <div>
                <div style={{ fontWeight: 700, color: '#111827' }}>{currentDraft.operation_label}</div>
                <div style={{ color: '#6b7280', marginTop: '4px' }}>{currentDraft.operation_type}</div>
              </div>
              <button
                type="button"
                data-testid={`approval-config-save-${currentDraft.operation_type}`}
                onClick={handleSave}
                disabled={savingKey === currentDraft.operation_type}
                style={primaryButtonStyle}
              >
                {savingKey === currentDraft.operation_type ? '保存中...' : '保存'}
              </button>
            </div>

            <label style={{ display: 'grid', gap: '6px' }}>
              <span style={{ fontWeight: 600, color: '#111827' }}>工作流名称</span>
              <input
                type="text"
                value={currentDraft.name}
                data-testid={`approval-config-name-${currentDraft.operation_type}`}
                onChange={(event) =>
                  updateCurrentDraft((draft) => ({
                    ...draft,
                    name: event.target.value,
                  }))
                }
                style={{ padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '10px' }}
              />
            </label>

            {(currentDraft.steps || []).map((step, stepIndex) => (
              <div
                key={`${currentDraft.operation_type}-${step.step_no}`}
                style={{ border: '1px solid #e5e7eb', borderRadius: '12px', padding: '12px' }}
                data-testid={`approval-config-step-${currentDraft.operation_type}-${stepIndex}`}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <strong>{`第 ${stepIndex + 1} 层`}</strong>
                  <button
                    type="button"
                    onClick={() => removeStep(stepIndex)}
                    disabled={(currentDraft.steps || []).length <= 1}
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
                      data-testid={`approval-config-step-name-${currentDraft.operation_type}-${stepIndex}`}
                      onChange={(event) => updateStepField(stepIndex, 'step_name', event.target.value)}
                      style={{ padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '10px' }}
                    />
                  </label>

                  <div style={{ display: 'grid', gap: '10px' }}>
                    <div style={{ fontWeight: 600, color: '#111827' }}>审批成员</div>
                    {(step.members || []).map((member, memberIndex) => (
                      <div
                        key={`${currentDraft.operation_type}-${stepIndex}-${memberIndex}`}
                        style={{ display: 'grid', gridTemplateColumns: '180px minmax(0, 1fr) auto', gap: '10px', alignItems: 'center' }}
                        data-testid={`approval-config-member-${currentDraft.operation_type}-${stepIndex}-${memberIndex}`}
                      >
                        <select
                          value={member.member_type}
                          data-testid={`approval-config-member-type-${currentDraft.operation_type}-${stepIndex}-${memberIndex}`}
                          onChange={(event) => updateMemberField(stepIndex, memberIndex, 'member_type', event.target.value)}
                          style={{ padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '10px' }}
                        >
                          <option value={WORKFLOW_MEMBER_TYPE_USER}>固定用户</option>
                          <option value={WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE}>直属主管</option>
                        </select>

                        {member.member_type === WORKFLOW_MEMBER_TYPE_USER ? (
                          <select
                            value={member.member_ref}
                            data-testid={`approval-config-member-ref-${currentDraft.operation_type}-${stepIndex}-${memberIndex}`}
                            onChange={(event) => updateMemberField(stepIndex, memberIndex, 'member_ref', event.target.value)}
                            style={{ padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '10px' }}
                          >
                            <option value="">请选择用户</option>
                            {userOptions.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <div
                            data-testid={`approval-config-member-role-${currentDraft.operation_type}-${stepIndex}-${memberIndex}`}
                            style={{
                              padding: '10px 12px',
                              border: '1px solid #d1d5db',
                              borderRadius: '10px',
                              background: '#f9fafb',
                              color: '#374151',
                            }}
                          >
                            {specialRoleLabel(member.member_ref || SPECIAL_ROLE_DIRECT_MANAGER)}
                          </div>
                        )}

                        <button
                          type="button"
                          onClick={() => removeMember(stepIndex, memberIndex)}
                          style={buttonStyle}
                        >
                          删除成员
                        </button>
                      </div>
                    ))}

                    <div>
                      <button
                        type="button"
                        data-testid={`approval-config-add-member-${currentDraft.operation_type}-${stepIndex}`}
                        onClick={() => addMember(stepIndex)}
                        style={buttonStyle}
                      >
                        增加成员
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            <div>
              <button
                type="button"
                data-testid={`approval-config-add-step-${currentDraft.operation_type}`}
                onClick={addStep}
                style={buttonStyle}
              >
                增加一层
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
