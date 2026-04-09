import { normalizeDraftByUserType, normalizeGroupIds } from './userAccessPolicy';
import { normalizeToolIds } from './toolCatalog';

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

export const toggleManagedUserDraftTool = (draft, toolId, checked) => {
  if (String(draft?.user_type || 'normal') !== 'sub_admin') {
    return { ...(draft || {}), tool_ids: [] };
  }

  const toolIds = normalizeToolIds(draft?.tool_ids);
  if (checked) {
    if (toolIds.includes(toolId)) return draft;
    return { ...(draft || {}), tool_ids: normalizeToolIds([...toolIds, toolId]) };
  }
  return { ...(draft || {}), tool_ids: toolIds.filter((id) => id !== toolId) };
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

export const togglePolicyToolSelection = ({ draft, toolId, checked, isPolicyAdminUser }) => {
  if (isPolicyAdminUser || String(draft?.user_type || 'normal') !== 'sub_admin') {
    return { ...(draft || {}), tool_ids: [] };
  }

  const current = normalizeToolIds(draft?.tool_ids);
  if (checked) {
    if (current.includes(toolId)) return draft;
    return { ...(draft || {}), tool_ids: normalizeToolIds([...current, toolId]) };
  }
  return { ...(draft || {}), tool_ids: current.filter((id) => id !== toolId) };
};

export const toggleSelectedGroupIds = (groupIds, groupId, checked) => {
  const current = Array.isArray(groupIds) ? groupIds : [];
  if (checked) {
    if (current.includes(groupId)) return current;
    return [...current, groupId];
  }
  return current.filter((id) => id !== groupId);
};

export const toggleSelectedToolIds = (toolIds, toolId, checked) => {
  const current = normalizeToolIds(toolIds);
  if (checked) {
    if (current.includes(toolId)) return current;
    return normalizeToolIds([...current, toolId]);
  }
  return current.filter((id) => id !== toolId);
};
