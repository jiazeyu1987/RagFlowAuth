import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { permissionGroupsApi } from '../api';
import { HIDDEN_CHAT_NAMES, emptyForm, ROOT } from './constants';
import { buildFolderIndexes, normalizeGroups, pathFolders, toggleInArray } from './utils';

function fillFormFromGroup(group) {
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
    can_delete: !!group?.can_delete,
    can_manage_kb_directory: !!group?.can_manage_kb_directory,
    can_view_kb_config: group?.can_view_kb_config !== false,
    can_view_tools: group?.can_view_tools !== false,
  };
}

function normalizeKnowledgeTreeResponse(knowledgeRes, knowledgeBasesRes) {
  if (knowledgeRes?.data && Array.isArray(knowledgeRes.data.datasets)) {
    return knowledgeRes.data;
  }
  const datasets = (knowledgeBasesRes?.data || []).map((item) => ({
    id: item.id,
    name: item.name,
    node_path: '/',
  }));
  return { nodes: [], datasets };
}

function pathSegmentCount(pathValue) {
  return String(pathValue || '')
    .split('/')
    .map((segment) => segment.trim())
    .filter((segment) => !!segment).length;
}

export default function usePermissionGroupManagement() {
  const [groups, setGroups] = useState([]);
  const [groupFolders, setGroupFolders] = useState([]);
  const [knowledgeTree, setKnowledgeTree] = useState({ nodes: [], datasets: [] });
  const [chatAgents, setChatAgents] = useState([]);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [hint, setHint] = useState('');

  const [currentFolderId, setCurrentFolderId] = useState(ROOT);
  const [selectedFolderId, setSelectedFolderId] = useState(ROOT);
  const [expandedFolderIds, setExpandedFolderIds] = useState([]);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [selectedItem, setSelectedItem] = useState(null);
  const [dragGroupId, setDragGroupId] = useState(null);
  const [dropTargetFolderId, setDropTargetFolderId] = useState(null);

  const [mode, setMode] = useState('');
  const [editingGroupId, setEditingGroupId] = useState(null);
  const [formData, setFormData] = useState({ ...emptyForm });
  const modeRef = useRef(mode);

  const folderIndexes = useMemo(() => buildFolderIndexes(groupFolders), [groupFolders]);

  const folderPath = useMemo(
    () => [
      { id: ROOT, name: '根目录' },
      ...pathFolders(currentFolderId, folderIndexes.byId).map((folder) => ({
        id: folder.id,
        name: folder.name || '(Unnamed folder)',
      })),
    ],
    [currentFolderId, folderIndexes.byId]
  );

  const groupsInCurrentFolder = useMemo(
    () => groups.filter((group) => (group.folder_id || ROOT) === currentFolderId),
    [groups, currentFolderId]
  );

  const contentRows = useMemo(() => {
    const rows = [];
    (folderIndexes.childrenByParent.get(currentFolderId) || []).forEach((folder) => {
      rows.push({
        kind: 'folder',
        id: folder.id,
        name: folder.name || '(未命名文件夹)',
        type: '文件夹',
      });
    });
    groupsInCurrentFolder.forEach((group) => {
      rows.push({
        kind: 'group',
        id: group.group_id,
        name: group.group_name || '(未命名权限组)',
        type: '权限组',
      });
    });
    return rows;
  }, [currentFolderId, folderIndexes.childrenByParent, groupsInCurrentFolder]);

  const filteredRows = useMemo(() => {
    const keyword = String(searchKeyword || '').trim().toLowerCase();
    if (!keyword) return contentRows;
    return contentRows.filter(
      (row) =>
        String(row.name || '').toLowerCase().includes(keyword) ||
        String(row.id || '').toLowerCase().includes(keyword)
    );
  }, [contentRows, searchKeyword]);

  const editingGroup = useMemo(
    () => groups.find((group) => group.group_id === editingGroupId) || null,
    [groups, editingGroupId]
  );

  const knowledgeNodeTreeNodes = useMemo(() => {
    const items = (knowledgeTree?.nodes || []).map((node) => {
      return {
        id: node.id,
        name: node.name || '(未命名文件夹)',
        parent_id: node.parent_id || ROOT,
        sortPath: String(node.path || ''),
        path: String(node.path || ''),
      };
    });
    items.sort((a, b) => {
      const byPath = a.sortPath.localeCompare(b.sortPath, 'zh-Hans-CN');
      if (byPath !== 0) return byPath;
      return String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN');
    });
    return items;
  }, [knowledgeTree?.nodes]);

  const knowledgeDatasetItems = useMemo(() => {
    const items = (knowledgeTree?.datasets || []).map((dataset) => {
      const depth = Math.max(0, pathSegmentCount(dataset.node_path));
      return {
        id: dataset.id,
        name: dataset.name || '(未命名知识库)',
        depth,
        sortPath: String(dataset.node_path || '/'),
      };
    });
    items.sort((a, b) => {
      const byPath = a.sortPath.localeCompare(b.sortPath, 'zh-Hans-CN');
      if (byPath !== 0) return byPath;
      return String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN');
    });
    return items;
  }, [knowledgeTree?.datasets]);

  const ensureFolderExpanded = useCallback(
    (folderId) => {
      if (!folderId) return;
      const ids = pathFolders(folderId, folderIndexes.byId).map((folder) => folder.id);
      setExpandedFolderIds((previous) => {
        const next = new Set(previous);
        ids.forEach((id) => next.add(id));
        return Array.from(next);
      });
    },
    [folderIndexes.byId]
  );

  const openFolder = useCallback(
    (folderId) => {
      const next = folderId || ROOT;
      setCurrentFolderId(next);
      setSelectedFolderId(next);
      if (next) ensureFolderExpanded(next);
    },
    [ensureFolderExpanded]
  );

  const startCreateGroup = useCallback(() => {
    setMode('create');
    setEditingGroupId(null);
    setFormData({ ...emptyForm, folder_id: currentFolderId || null });
  }, [currentFolderId]);

  const startEditGroup = useCallback((group) => {
    if (!group) return;
    setMode('edit');
    setEditingGroupId(group.group_id);
    setFormData(fillFormFromGroup(group));
  }, []);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const groupsRes = await permissionGroupsApi.list();
      const [folderRes, knowledgeTreeRes, knowledgeBasesRes, chatsRes] = await Promise.all([
        permissionGroupsApi.listGroupFolders().catch(() => null),
        permissionGroupsApi.listKnowledgeTree().catch(() => null),
        permissionGroupsApi.listKnowledgeBases().catch(() => null),
        permissionGroupsApi.listChats().catch(() => ({ ok: true, data: [] })),
      ]);

      const folderData = folderRes?.data || {
        folders: [],
        group_bindings: {},
        root_group_count: 0,
      };
      const normalizedGroups = normalizeGroups(groupsRes?.data || [], folderData.group_bindings || {});
      const visibleChats = (chatsRes?.data || []).filter((chat) => {
        const rawName = String(chat?.name || '').trim();
        const normalized = rawName.replace(/^\[|\]$/g, '').trim();
        return !HIDDEN_CHAT_NAMES.has(rawName) && !HIDDEN_CHAT_NAMES.has(normalized);
      });
      const nextKnowledgeTree = normalizeKnowledgeTreeResponse(knowledgeTreeRes, knowledgeBasesRes);

      setGroups(normalizedGroups);
      setGroupFolders(folderData.folders || []);
      setKnowledgeTree(nextKnowledgeTree);
      setChatAgents(visibleChats);
      return normalizedGroups;
    } catch (requestError) {
      setError(requestError?.message || '加载权限组失败');
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    fetchAll().then((list) => {
      if (!active) return;
      if (modeRef.current === 'create' || modeRef.current === 'edit') return;
      if (list.length) startEditGroup(list[0]);
      else startCreateGroup();
    });
    return () => {
      active = false;
    };
  }, [fetchAll, startCreateGroup, startEditGroup]);

  const saveForm = useCallback(
    async (event) => {
      event.preventDefault();
      setSaving(true);
      setError('');
      setHint('');
      try {
        if (mode === 'create') {
          const response = await permissionGroupsApi.create(formData);
          const newId = response?.data?.group_id;
          const nextGroups = await fetchAll();
          const created = nextGroups.find((group) => group.group_id === newId) || null;
          if (created) {
            startEditGroup(created);
            setHint('权限组已创建');
          }
        } else if (mode === 'edit' && editingGroupId != null) {
          await permissionGroupsApi.update(editingGroupId, formData);
          const nextGroups = await fetchAll();
          const updated = nextGroups.find((group) => group.group_id === editingGroupId) || null;
          if (updated) {
            startEditGroup(updated);
            setHint('权限组已保存');
          }
        }
      } catch (saveError) {
        setError(saveError?.message || '保存权限组失败');
      } finally {
        setSaving(false);
      }
    },
    [editingGroupId, fetchAll, formData, mode, startEditGroup]
  );

  const cancelEdit = useCallback(() => {
    if (mode === 'edit' && editingGroup) {
      setFormData(fillFormFromGroup(editingGroup));
      return;
    }
    startCreateGroup();
  }, [editingGroup, mode, startCreateGroup]);

  const removeGroup = useCallback(
    async (group, options = {}) => {
      if (!group?.group_id) return;
      const skipConfirm = options?.skipConfirm === true;
      if (!skipConfirm) {
        const ok = window.confirm(`确认删除权限组“${group.group_name || group.group_id}”？`);
        if (!ok) return;
      }
      setError('');
      setHint('');
      try {
        await permissionGroupsApi.remove(group.group_id);
        const nextGroups = await fetchAll();
        if (editingGroupId === group.group_id) {
          if (nextGroups.length) startEditGroup(nextGroups[0]);
          else startCreateGroup();
        }
        setHint('权限组已删除');
      } catch (removeError) {
        setError(removeError?.message || '删除权限组失败');
      }
    },
    [editingGroupId, fetchAll, startCreateGroup, startEditGroup]
  );

  const createFolder = useCallback(async () => {
    const name = window.prompt('请输入文件夹名称');
    if (!name || !name.trim()) return;
    setError('');
    setHint('');
    try {
      const response = await permissionGroupsApi.createFolder({
        name: name.trim(),
        parent_id: currentFolderId || null,
      });
      const newId = response?.data?.id || '';
      await fetchAll();
      if (newId) {
        openFolder(newId);
        setSelectedItem({ kind: 'folder', id: newId });
      }
      setHint('文件夹已创建');
    } catch (createError) {
      setError(createError?.message || '创建文件夹失败');
    }
  }, [currentFolderId, fetchAll, openFolder]);

  const renameFolder = useCallback(async () => {
    const targetId = selectedFolderId || ROOT;
    if (!targetId || targetId === ROOT) return;
    const folder = folderIndexes.byId.get(targetId);
    const next = window.prompt('请输入文件夹名称', folder?.name || '');
    if (!next || !next.trim()) return;
    setError('');
    setHint('');
    try {
      await permissionGroupsApi.updateFolder(targetId, { name: next.trim() });
      await fetchAll();
      ensureFolderExpanded(targetId);
      setHint('文件夹已重命名');
    } catch (renameError) {
      setError(renameError?.message || '重命名文件夹失败');
    }
  }, [ensureFolderExpanded, fetchAll, folderIndexes.byId, selectedFolderId]);

  const deleteFolder = useCallback(async () => {
    const targetId = selectedFolderId || ROOT;
    if (!targetId || targetId === ROOT) return;
    const folder = folderIndexes.byId.get(targetId);
    const ok = window.confirm(
      `确认删除文件夹“${folder?.name || targetId}”？\n请先确保该文件夹为空。`
    );
    if (!ok) return;
    setError('');
    setHint('');
    try {
      await permissionGroupsApi.removeFolder(targetId);
      const parent = folder?.parent_id || ROOT;
      openFolder(parent);
      setSelectedItem(null);
      await fetchAll();
      setHint('文件夹已删除');
    } catch (deleteError) {
      setError(deleteError?.message || '删除文件夹失败');
    }
  }, [fetchAll, folderIndexes.byId, openFolder, selectedFolderId]);

  const toggleNodeAuth = useCallback((nodeId) => {
    setFormData((previous) => ({
      ...previous,
      accessible_kb_nodes: toggleInArray(previous.accessible_kb_nodes, nodeId),
    }));
  }, []);

  const toggleKbAuth = useCallback((kbId) => {
    setFormData((previous) => ({
      ...previous,
      accessible_kbs: toggleInArray(previous.accessible_kbs, kbId),
    }));
  }, []);

  const toggleChatAuth = useCallback((chatId) => {
    setFormData((previous) => ({
      ...previous,
      accessible_chats: toggleInArray(previous.accessible_chats, chatId),
    }));
  }, []);

  const toggleToolAuth = useCallback((toolId) => {
    setFormData((previous) => ({
      ...previous,
      accessible_tools: toggleInArray(previous.accessible_tools, toolId),
    }));
  }, []);

  const moveGroupToFolder = useCallback(
    async (groupId, folderId) => {
      if (!groupId) return;
      setError('');
      setHint('');
      try {
        await permissionGroupsApi.update(groupId, { folder_id: folderId || null });
        const nextGroups = await fetchAll();
        const moved = nextGroups.find((group) => group.group_id === groupId);
        if (editingGroupId === groupId && moved) {
          setFormData((previous) => ({ ...previous, folder_id: moved.folder_id || null }));
        }
        setHint('权限组已移动');
      } catch (moveError) {
        setError(moveError?.message || '移动权限组失败');
      }
    },
    [editingGroupId, fetchAll]
  );

  const onDragOverFolder = useCallback(
    (event, folderId) => {
      if (!dragGroupId) return;
      event.preventDefault();
      if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
      setDropTargetFolderId(folderId);
    },
    [dragGroupId]
  );

  const onDragLeaveFolder = useCallback(
    (event, folderId) => {
      if (!dragGroupId) return;
      const related = event.relatedTarget;
      if (related && event.currentTarget.contains(related)) return;
      if (dropTargetFolderId === folderId) setDropTargetFolderId(null);
    },
    [dragGroupId, dropTargetFolderId]
  );

  const onDropFolder = useCallback(
    async (event, folderId) => {
      if (!dragGroupId) return;
      event.preventDefault();
      const raw = event.dataTransfer?.getData('application/x-pg-group-id');
      const droppedId = Number(raw || dragGroupId);
      setDropTargetFolderId(null);
      setDragGroupId(null);
      if (!Number.isFinite(droppedId)) return;
      await moveGroupToFolder(droppedId, folderId);
    },
    [dragGroupId, moveGroupToFolder]
  );

  const startGroupDrag = useCallback((event, groupId) => {
    event.dataTransfer.setData('application/x-pg-group-id', String(groupId));
    event.dataTransfer.effectAllowed = 'move';
    setDragGroupId(groupId);
    setDropTargetFolderId(null);
  }, []);

  const endGroupDrag = useCallback(() => {
    setDragGroupId(null);
    setDropTargetFolderId(null);
  }, []);

  return {
    groups,
    loading,
    saving,
    error,
    hint,
    currentFolderId,
    selectedFolderId,
    expandedFolderIds,
    searchKeyword,
    selectedItem,
    dragGroupId,
    dropTargetFolderId,
    formData,
    editingGroup,
    folderIndexes,
    folderPath,
    filteredRows,
    knowledgeNodeTreeNodes,
    knowledgeDatasetItems,
    chatAgents,
    setSearchKeyword,
    setExpandedFolderIds,
    setSelectedItem,
    setSelectedFolderId,
    setFormData,
    fetchAll,
    createFolder,
    renameFolder,
    deleteFolder,
    startCreateGroup,
    startEditGroup,
    saveForm,
    cancelEdit,
    removeGroup,
    toggleNodeAuth,
    toggleKbAuth,
    toggleChatAuth,
    toggleToolAuth,
    openFolder,
    onDragOverFolder,
    onDropFolder,
    onDragLeaveFolder,
    startGroupDrag,
    endGroupDrag,
  };
}
