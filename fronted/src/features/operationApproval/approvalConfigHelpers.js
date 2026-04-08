export const WORKFLOW_MEMBER_TYPE_USER = 'user';
export const WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE = 'special_role';
export const SPECIAL_ROLE_DIRECT_MANAGER = 'direct_manager';
export const USER_SEARCH_LIMIT = 20;

export const createEmptyMember = () => ({
  member_type: WORKFLOW_MEMBER_TYPE_USER,
  member_ref: '',
});

export const createEmptyStep = (stepNo) => ({
  step_no: Number(stepNo),
  step_name: `第 ${stepNo} 层`,
  members: [createEmptyMember()],
});

export const createUserSearchState = () => ({
  keyword: '',
  results: [],
  loading: false,
  open: false,
  error: '',
});

export const buildUserLabel = (user) => {
  if (!user) return '-';
  const fullName = String(user.full_name || '').trim();
  const username = String(user.username || '').trim();
  return fullName || username || String(user.user_id || '-');
};

export const buildMemberSearchKey = (operationType, stepIndex, memberIndex) =>
  `${String(operationType || '')}:${Number(stepIndex)}:${Number(memberIndex)}`;

export const collectConfiguredUserIds = (drafts) => {
  const ids = new Set();
  (drafts || []).forEach((draft) => {
    (draft.steps || []).forEach((step) => {
      (step.members || []).forEach((member) => {
        if (String(member?.member_type || '') !== WORKFLOW_MEMBER_TYPE_USER) return;
        const userId = String(member?.member_ref || '').trim();
        if (userId) {
          ids.add(userId);
        }
      });
    });
  });
  return Array.from(ids);
};

export const normalizeMembers = (step) => {
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

export const createDraftFromWorkflow = (workflow) => ({
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

export const specialRoleLabel = (memberRef) => {
  if (memberRef === SPECIAL_ROLE_DIRECT_MANAGER) return '直属主管';
  return memberRef || '-';
};

export const validateWorkflowDraft = (draft) => {
  const steps = Array.isArray(draft?.steps) ? draft.steps : [];
  if (steps.length === 0) return '至少保留一层审批';
  for (const step of steps) {
    if (!String(step?.step_name || '').trim()) return '每一层都必须填写名称';
    const members = Array.isArray(step?.members) ? step.members : [];
    if (members.length === 0) return '每一层至少配置一名成员';
    for (const member of members) {
      const memberType = String(member?.member_type || '').trim();
      const memberRef = String(member?.member_ref || '').trim();
      if (!memberType) return '审批成员类型不能为空';
      if (memberType === WORKFLOW_MEMBER_TYPE_USER && !memberRef) {
        return '固定用户成员必须选择用户';
      }
      if (
        memberType === WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE &&
        memberRef !== SPECIAL_ROLE_DIRECT_MANAGER
      ) {
        return '当前仅支持直属主管特殊角色';
      }
    }
  }
  return '';
};

export const buildWorkflowPayload = (draft) => ({
  name: String(draft?.name || '').trim() || null,
  steps: (draft?.steps || []).map((step, index) => ({
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
