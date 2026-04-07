import { normalizeDraftByUserType, normalizeGroupIds } from './userAccessPolicy';

export const applyManagedUserFieldChange = (draft, field, value) => {
  const next = { ...(draft || {}), [field]: value };
  if (field === 'company_id') {
    next.department_id = '';
    next.manager_user_id = '';
    next.managed_kb_root_node_id = '';
  }
  return normalizeDraftByUserType(next);
};

export const toggleManagedUserDraftGroup = (draft, groupId, checked) => {
  if (String(draft?.user_type || 'normal') !== 'sub_admin') {
    return { ...(draft || {}), group_ids: [] };
  }

  const groupIds = Array.isArray(draft?.group_ids) ? draft.group_ids : [];
  if (checked) {
    if (groupIds.includes(groupId)) return draft;
    return { ...(draft || {}), group_ids: [...groupIds, groupId] };
  }
  return { ...(draft || {}), group_ids: groupIds.filter((id) => id !== groupId) };
};

export const applyPolicyFormChange = (previousDraft, nextValue) => {
  const draft = typeof nextValue === 'function' ? nextValue(previousDraft) : nextValue;
  const next = normalizeDraftByUserType(draft);
  if (String(next.company_id || '') !== String(previousDraft?.company_id || '')) {
    next.department_id = '';
    next.manager_user_id = '';
    next.managed_kb_root_node_id = '';
  }
  return next;
};

export const togglePolicyGroupSelection = ({ draft, groupId, checked, isPolicyAdminUser }) => {
  if (isPolicyAdminUser || String(draft?.user_type || 'normal') !== 'sub_admin') {
    return { ...(draft || {}), group_ids: [] };
  }

  const current = normalizeGroupIds(draft?.group_ids);
  if (checked) {
    if (current.includes(groupId)) return draft;
    return { ...(draft || {}), group_ids: [...current, groupId] };
  }
  return { ...(draft || {}), group_ids: current.filter((id) => id !== groupId) };
};

export const toggleSelectedGroupIds = (groupIds, groupId, checked) => {
  const current = Array.isArray(groupIds) ? groupIds : [];
  if (checked) {
    if (current.includes(groupId)) return current;
    return [...current, groupId];
  }
  return current.filter((id) => id !== groupId);
};
