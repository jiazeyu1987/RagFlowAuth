import { useCallback, useEffect, useMemo, useState } from 'react';
import operationApprovalApi from './api';
import { usersApi } from '../users/api';

export const WORKFLOW_MEMBER_TYPE_USER = 'user';
export const WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE = 'special_role';
export const SPECIAL_ROLE_DIRECT_MANAGER = 'direct_manager';

const USER_SEARCH_LIMIT = 20;

const createEmptyMember = () => ({
  member_type: WORKFLOW_MEMBER_TYPE_USER,
  member_ref: '',
});

const createEmptyStep = (stepNo) => ({
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

const collectConfiguredUserIds = (drafts) => {
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

export const specialRoleLabel = (memberRef) => {
  if (memberRef === SPECIAL_ROLE_DIRECT_MANAGER) return '直属主管';
  return memberRef || '-';
};

export default function useApprovalConfigPage() {
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState('');
  const [error, setError] = useState('');
  const [saveMessage, setSaveMessage] = useState('');
  const [drafts, setDrafts] = useState([]);
  const [userDirectory, setUserDirectory] = useState({});
  const [memberSearchStates, setMemberSearchStates] = useState({});
  const [currentOperationType, setCurrentOperationType] = useState('');

  const mergeUsersIntoDirectory = useCallback((items) => {
    setUserDirectory((prev) => {
      let changed = false;
      const next = { ...prev };
      (items || []).forEach((item) => {
        const userId = String(item?.user_id || '').trim();
        if (!userId) return;
        next[userId] = item;
        changed = true;
      });
      return changed ? next : prev;
    });
  }, []);

  const searchUsers = useCallback(async (keyword) => {
    const items = await usersApi.search(keyword, USER_SEARCH_LIMIT);
    mergeUsersIntoDirectory(items);
    return items;
  }, [mergeUsersIntoDirectory]);

  const hydrateConfiguredUsers = useCallback(async (nextDrafts) => {
    const configuredIds = collectConfiguredUserIds(nextDrafts);
    if (configuredIds.length === 0) return;
    const resolvedUsers = await Promise.all(configuredIds.map((userId) => usersApi.get(userId)));
    mergeUsersIntoDirectory(resolvedUsers);
  }, [mergeUsersIntoDirectory]);

  const updateMemberSearchState = useCallback((searchKey, updater) => {
    setMemberSearchStates((prev) => {
      const current = prev[searchKey] || createUserSearchState();
      const nextState = typeof updater === 'function' ? updater(current) : updater;
      return {
        ...prev,
        [searchKey]: nextState,
      };
    });
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const workflowItems = await operationApprovalApi.listWorkflows();
      const nextDrafts = workflowItems.map(createDraftFromWorkflow);
      setDrafts(nextDrafts);
      await hydrateConfiguredUsers(nextDrafts);
      setCurrentOperationType((prev) => {
        if (prev && nextDrafts.some((draft) => draft.operation_type === prev)) return prev;
        return nextDrafts[0]?.operation_type || '';
      });
    } catch (requestError) {
      setError(requestError?.message || '加载审批配置失败');
      setDrafts([]);
      setCurrentOperationType('');
    } finally {
      setLoading(false);
    }
  }, [hydrateConfiguredUsers]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const currentDraft = useMemo(
    () => drafts.find((draft) => draft.operation_type === currentOperationType) || null,
    [currentOperationType, drafts]
  );

  const updateDraft = useCallback((operationType, updater) => {
    setDrafts((prev) =>
      prev.map((draft) => (draft.operation_type === operationType ? updater(draft) : draft))
    );
  }, []);

  const updateCurrentDraft = useCallback((updater) => {
    if (!currentOperationType) return;
    updateDraft(currentOperationType, updater);
  }, [currentOperationType, updateDraft]);

  const setCurrentDraftName = useCallback((value) => {
    updateCurrentDraft((draft) => ({
      ...draft,
      name: value,
    }));
  }, [updateCurrentDraft]);

  const addStep = useCallback(() => {
    updateCurrentDraft((draft) => ({
      ...draft,
      steps: [...(draft.steps || []), createEmptyStep((draft.steps || []).length + 1)],
    }));
  }, [updateCurrentDraft]);

  const removeStep = useCallback((index) => {
    updateCurrentDraft((draft) => ({
      ...draft,
      steps: (draft.steps || [])
        .filter((_, stepIndex) => stepIndex !== index)
        .map((step, stepIndex) => ({ ...step, step_no: stepIndex + 1 })),
    }));
  }, [updateCurrentDraft]);

  const updateStepField = useCallback((index, field, value) => {
    updateCurrentDraft((draft) => ({
      ...draft,
      steps: (draft.steps || []).map((step, stepIndex) =>
        stepIndex === index ? { ...step, [field]: value } : step
      ),
    }));
  }, [updateCurrentDraft]);

  const addMember = useCallback((stepIndex) => {
    updateCurrentDraft((draft) => ({
      ...draft,
      steps: (draft.steps || []).map((step, index) =>
        index === stepIndex
          ? { ...step, members: [...(step.members || []), createEmptyMember()] }
          : step
      ),
    }));
  }, [updateCurrentDraft]);

  const removeMember = useCallback((stepIndex, memberIndex) => {
    updateCurrentDraft((draft) => ({
      ...draft,
      steps: (draft.steps || []).map((step, index) => {
        if (index !== stepIndex) return step;
        const nextMembers = (step.members || []).filter(
          (_, currentMemberIndex) => currentMemberIndex !== memberIndex
        );
        return {
          ...step,
          members: nextMembers.length > 0 ? nextMembers : [createEmptyMember()],
        };
      }),
    }));
  }, [updateCurrentDraft]);

  const updateMemberField = useCallback((stepIndex, memberIndex, field, value) => {
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
  }, [updateCurrentDraft]);

  const handleMemberUserKeywordChange = useCallback((operationType, stepIndex, memberIndex, value) => {
    const searchKey = buildMemberSearchKey(operationType, stepIndex, memberIndex);
    updateDraft(operationType, (draft) => ({
      ...draft,
      steps: (draft.steps || []).map((step, currentStepIndex) => {
        if (currentStepIndex !== stepIndex) return step;
        return {
          ...step,
          members: (step.members || []).map((member, currentMemberIndex) =>
            currentMemberIndex === memberIndex ? { ...member, member_ref: '' } : member
          ),
        };
      }),
    }));
    updateMemberSearchState(searchKey, (prev) => ({
      ...prev,
      keyword: value,
      open: true,
      error: '',
      ...(String(value || '').trim() ? {} : { results: [] }),
    }));
  }, [updateDraft, updateMemberSearchState]);

  const handleSelectMemberUser = useCallback((operationType, stepIndex, memberIndex, selectedUser) => {
    const searchKey = buildMemberSearchKey(operationType, stepIndex, memberIndex);
    mergeUsersIntoDirectory([selectedUser]);
    updateDraft(operationType, (draft) => ({
      ...draft,
      steps: (draft.steps || []).map((step, currentStepIndex) => {
        if (currentStepIndex !== stepIndex) return step;
        return {
          ...step,
          members: (step.members || []).map((member, currentMemberIndex) =>
            currentMemberIndex === memberIndex
              ? { ...member, member_ref: String(selectedUser?.user_id || '') }
              : member
          ),
        };
      }),
    }));
    updateMemberSearchState(searchKey, (prev) => ({
      ...prev,
      keyword: buildUserLabel(selectedUser),
      open: false,
      loading: false,
      results: [],
      error: '',
    }));
  }, [mergeUsersIntoDirectory, updateDraft, updateMemberSearchState]);

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
      setError(requestError?.message || '保存审批流程失败');
    } finally {
      setSavingKey('');
    }
  }, [currentDraft, loadData, validateDraft]);

  const getSelectedUser = useCallback((memberRef) => {
    return userDirectory[String(memberRef || '')] || null;
  }, [userDirectory]);

  const getMemberSearchState = useCallback((operationType, stepIndex, memberIndex) => {
    return (
      memberSearchStates[buildMemberSearchKey(operationType, stepIndex, memberIndex)] ||
      createUserSearchState()
    );
  }, [memberSearchStates]);

  return {
    loading,
    savingKey,
    error,
    saveMessage,
    drafts,
    currentOperationType,
    currentDraft,
    searchUsers,
    updateMemberSearchState,
    loadData,
    setCurrentOperationType,
    setCurrentDraftName,
    addStep,
    removeStep,
    updateStepField,
    addMember,
    removeMember,
    updateMemberField,
    handleMemberUserKeywordChange,
    handleSelectMemberUser,
    handleSave,
    getSelectedUser,
    getMemberSearchState,
  };
}
