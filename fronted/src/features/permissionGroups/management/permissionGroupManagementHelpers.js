import { HIDDEN_CHAT_NAMES, ROOT, emptyForm } from './constants';
import { pathFolders } from './utils';

export function buildCreateForm(folderId) {
  return {
    ...emptyForm,
    folder_id: folderId || null,
  };
}

export function fillFormFromGroup(group) {
  return {
    ...emptyForm,
    group_name: group?.group_name || '',
    description: group?.description || '',
    folder_id: group?.folder_id || null,
    accessible_kbs: group?.accessible_kbs || [],
    accessible_kb_nodes: group?.accessible_kb_nodes || [],
    accessible_chats: group?.accessible_chats || [],
    accessible_tools: group?.accessible_tools || [],
    can_upload: !!group?.can_upload,
    can_review: !!group?.can_review,
    can_download: group?.can_download !== false,
    can_copy: !!group?.can_copy,
    can_delete: !!group?.can_delete,
    can_manage_kb_directory: !!group?.can_manage_kb_directory,
    can_view_kb_config: group?.can_view_kb_config !== false,
    can_view_tools: group?.can_view_tools !== false,
  };
}

function pathSegmentCount(pathValue) {
  return String(pathValue || '')
    .split('/')
    .map((segment) => segment.trim())
    .filter(Boolean).length;
}

export function filterVisibleChats(chats) {
  return (chats || []).filter((chat) => {
    const rawName = String(chat?.name || '').trim();
    const normalized = rawName.replace(/^\[|\]$/g, '').trim();
    return !HIDDEN_CHAT_NAMES.has(rawName) && !HIDDEN_CHAT_NAMES.has(normalized);
  });
}

export function buildFolderPath(currentFolderId, folderIndexesById) {
  return [
    { id: ROOT, name: '根目录' },
    ...pathFolders(currentFolderId, folderIndexesById).map((folder) => ({
      id: folder.id,
      name: folder.name || '(Unnamed folder)',
    })),
  ];
}

export function buildContentRows(currentFolderId, childrenByParent, groupsInCurrentFolder) {
  const rows = [];

  (childrenByParent.get(currentFolderId) || []).forEach((folder) => {
    rows.push({
      kind: 'folder',
      id: folder.id,
      name: folder.name || '(Unnamed folder)',
      type: '文件夹',
    });
  });

  groupsInCurrentFolder.forEach((group) => {
    rows.push({
      kind: 'group',
      id: group.group_id,
      name: group.group_name || '(Unnamed permission group)',
      type: '权限组',
    });
  });

  return rows;
}

export function filterContentRows(contentRows, searchKeyword) {
  const keyword = String(searchKeyword || '').trim().toLowerCase();
  if (!keyword) return contentRows;

  return contentRows.filter(
    (row) =>
      String(row.name || '').toLowerCase().includes(keyword) ||
      String(row.id || '').toLowerCase().includes(keyword)
  );
}

export function buildKnowledgeNodeTreeNodes(nodes) {
  const items = (nodes || []).map((node) => ({
    id: node.id,
    name: node.name || '(Unnamed folder)',
    parent_id: node.parent_id || ROOT,
    sortPath: String(node.path || ''),
    path: String(node.path || ''),
  }));

  items.sort((left, right) => {
    const byPath = left.sortPath.localeCompare(right.sortPath, 'zh-Hans-CN');
    if (byPath !== 0) return byPath;
    return String(left.name || '').localeCompare(String(right.name || ''), 'zh-Hans-CN');
  });

  return items;
}

export function buildKnowledgeDatasetItems(datasets) {
  const items = (datasets || []).map((dataset) => ({
    id: dataset.id,
    name: dataset.name || '(Unnamed knowledge base)',
    depth: Math.max(0, pathSegmentCount(dataset.node_path)),
    sortPath: String(dataset.node_path || '/'),
  }));

  items.sort((left, right) => {
    const byPath = left.sortPath.localeCompare(right.sortPath, 'zh-Hans-CN');
    if (byPath !== 0) return byPath;
    return String(left.name || '').localeCompare(String(right.name || ''), 'zh-Hans-CN');
  });

  return items;
}
