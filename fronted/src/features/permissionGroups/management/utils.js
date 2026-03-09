import { ROOT } from './constants';

export function normalizeGroups(rawGroups, groupBindings = {}) {
  return (rawGroups || []).map((group) => {
    const key = String(group?.group_id ?? '');
    const bound = Object.prototype.hasOwnProperty.call(groupBindings || {}, key) ? groupBindings[key] : undefined;
    const folderId = group?.folder_id ?? bound ?? null;
    return {
      ...group,
      folder_id: typeof folderId === 'string' && folderId ? folderId : null,
      accessible_kbs: Array.isArray(group?.accessible_kbs) ? group.accessible_kbs : [],
      accessible_kb_nodes: Array.isArray(group?.accessible_kb_nodes) ? group.accessible_kb_nodes : [],
      accessible_chats: Array.isArray(group?.accessible_chats) ? group.accessible_chats : [],
    };
  });
}

export function buildFolderIndexes(folders) {
  const byId = new Map();
  const childrenByParent = new Map();
  (folders || []).forEach((folder) => {
    if (!folder?.id) return;
    byId.set(folder.id, folder);
    const parent = folder.parent_id || ROOT;
    if (!childrenByParent.has(parent)) childrenByParent.set(parent, []);
    childrenByParent.get(parent).push(folder);
  });
  for (const arr of childrenByParent.values()) {
    arr.sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN'));
  }
  return { byId, childrenByParent };
}

export function pathFolders(folderId, byId) {
  if (!folderId) return [];
  const output = [];
  const seen = new Set();
  let current = folderId;
  while (current && !seen.has(current)) {
    seen.add(current);
    const folder = byId.get(current);
    if (!folder) break;
    output.push(folder);
    current = folder.parent_id || ROOT;
  }
  return output.reverse();
}

export function toggleInArray(values, item) {
  const list = Array.isArray(values) ? values : [];
  return list.includes(item) ? list.filter((value) => value !== item) : [...list, item];
}
