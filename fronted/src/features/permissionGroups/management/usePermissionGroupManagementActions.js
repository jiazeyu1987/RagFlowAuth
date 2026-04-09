import { useCallback } from 'react';

import { mapUserFacingErrorMessage } from '../../../shared/errors/userFacingErrorMessages';
import { permissionGroupsApi } from '../api';
import { ROOT } from './constants';
import { buildCreateForm, fillFormFromGroup } from './permissionGroupManagementHelpers';
import { pathFolders, toggleInArray } from './utils';

export default function usePermissionGroupManagementActions({
  currentFolderId,
  editingGroup,
  editingGroupId,
  fetchAll,
  folderIndexesById,
  folderIndexesRef,
  formData,
  groups,
  mode,
  selectedFolderId,
  selectedItem,
  setCurrentFolderId,
  setEditingGroupId,
  setError,
  setExpandedFolderIds,
  setFormData,
  setHint,
  setMode,
  setSaving,
  setSelectedFolderId,
  setSelectedItem,
}) {
  const clearFeedback = useCallback(() => {
    setError('');
    setHint('');
  }, [setError, setHint]);

  const ensureFolderExpanded = useCallback(
    (folderId) => {
      if (!folderId) return;

      const ids = pathFolders(folderId, folderIndexesRef.current).map((folder) => folder.id);
      setExpandedFolderIds((previous) => {
        const next = new Set(previous);
        ids.forEach((id) => next.add(id));
        return Array.from(next);
      });
    },
    [folderIndexesRef, setExpandedFolderIds]
  );

  const openFolder = useCallback(
    (folderId) => {
      const next = folderId || ROOT;
      setCurrentFolderId(next);
      setSelectedFolderId(next);

      if (next) {
        ensureFolderExpanded(next);
      }
    },
    [ensureFolderExpanded, setCurrentFolderId, setSelectedFolderId]
  );

  const startCreateGroup = useCallback(() => {
    setMode('create');
    setEditingGroupId(null);
    setFormData(buildCreateForm(currentFolderId));
  }, [currentFolderId, setEditingGroupId, setFormData, setMode]);

  const selectGroup = useCallback(
    (group) => {
      if (!group) return;

      setEditingGroupId(group.group_id);
      setFormData(fillFormFromGroup(group));
      setSelectedItem({ kind: 'group', id: group.group_id });
      openFolder(group.folder_id || ROOT);
    },
    [openFolder, setEditingGroupId, setFormData, setSelectedItem]
  );

  const viewGroup = useCallback(
    (group) => {
      if (!group) return;

      setMode('view');
      selectGroup(group);
    },
    [selectGroup, setMode]
  );

  const startEditGroup = useCallback(
    (group) => {
      if (!group) return;

      setMode('edit');
      selectGroup(group);
    },
    [selectGroup, setMode]
  );

  const saveForm = useCallback(
    async (event) => {
      event.preventDefault();
      setSaving(true);
      clearFeedback();

      try {
        if (mode === 'create') {
          const response = await permissionGroupsApi.create(formData);
          const createdId = response?.group_id;
          const nextGroups = await fetchAll({ includeSupplemental: false });
          const createdGroup = nextGroups.find((group) => group.group_id === createdId) || null;

          if (createdGroup) {
            viewGroup(createdGroup);
            setHint('权限组已创建');
          }
        } else if (mode === 'edit' && editingGroupId != null) {
          await permissionGroupsApi.update(editingGroupId, formData);
          const nextGroups = await fetchAll({ includeSupplemental: false });
          const updatedGroup = nextGroups.find((group) => group.group_id === editingGroupId) || null;

          if (updatedGroup) {
            viewGroup(updatedGroup);
            setHint('权限组已保存');
          }
        }
      } catch (saveError) {
        setError(mapUserFacingErrorMessage(saveError?.message, '保存权限组失败'));
      } finally {
        setSaving(false);
      }
    },
    [clearFeedback, editingGroupId, fetchAll, formData, mode, setError, setHint, setSaving, viewGroup]
  );

  const cancelEdit = useCallback(() => {
    if (mode === 'edit' && editingGroup) {
      viewGroup(editingGroup);
      return;
    }

    if (mode === 'create') {
      const selectedGroup =
        selectedItem?.kind === 'group'
          ? groups.find((group) => group.group_id === selectedItem.id) || null
          : null;

      if (selectedGroup) {
        viewGroup(selectedGroup);
        return;
      }

      setMode('');
      setEditingGroupId(null);
      setFormData(buildCreateForm(currentFolderId));
    }
  }, [
    currentFolderId,
    editingGroup,
    groups,
    mode,
    selectedItem,
    setEditingGroupId,
    setFormData,
    setMode,
    viewGroup,
  ]);

  const removeGroup = useCallback(
    async (group, options = {}) => {
      if (!group?.group_id) return;

      const skipConfirm = options?.skipConfirm === true;
      if (!skipConfirm) {
        const confirmed = window.confirm(
          `确认删除权限组“${group.group_name || group.group_id}”？`
        );
        if (!confirmed) return;
      }

      clearFeedback();

      try {
        await permissionGroupsApi.remove(group.group_id);
        const nextGroups = await fetchAll({ includeSupplemental: false });

        if (editingGroupId === group.group_id) {
          if (nextGroups.length) {
            viewGroup(nextGroups[0]);
          } else {
            startCreateGroup();
          }
        }

        setHint('权限组已删除');
      } catch (removeError) {
        setError(mapUserFacingErrorMessage(removeError?.message, '删除权限组失败'));
      }
    },
    [clearFeedback, editingGroupId, fetchAll, setError, setHint, startCreateGroup, viewGroup]
  );

  const createFolder = useCallback(async () => {
    const name = window.prompt('请输入文件夹名称');
    if (!name || !name.trim()) return;

    clearFeedback();

    try {
      const response = await permissionGroupsApi.createFolder({
        name: name.trim(),
        parent_id: currentFolderId || null,
      });
      const newFolderId = response?.id || '';

      await fetchAll({ includeSupplemental: false });

      if (newFolderId) {
        openFolder(newFolderId);
        setSelectedItem({ kind: 'folder', id: newFolderId });
      }

      setHint('文件夹已创建');
    } catch (createError) {
      setError(mapUserFacingErrorMessage(createError?.message, '创建文件夹失败'));
    }
  }, [clearFeedback, currentFolderId, fetchAll, openFolder, setError, setHint, setSelectedItem]);

  const renameFolder = useCallback(async () => {
    const targetFolderId = selectedFolderId || ROOT;
    if (!targetFolderId || targetFolderId === ROOT) return;

    const folder = folderIndexesById.get(targetFolderId);
    const nextName = window.prompt('请输入文件夹名称', folder?.name || '');
    if (!nextName || !nextName.trim()) return;

    clearFeedback();

    try {
      await permissionGroupsApi.updateFolder(targetFolderId, { name: nextName.trim() });
      await fetchAll({ includeSupplemental: false });
      ensureFolderExpanded(targetFolderId);
      setHint('文件夹已重命名');
    } catch (renameError) {
      setError(mapUserFacingErrorMessage(renameError?.message, '重命名文件夹失败'));
    }
  }, [
    clearFeedback,
    ensureFolderExpanded,
    fetchAll,
    folderIndexesById,
    selectedFolderId,
    setError,
    setHint,
  ]);

  const deleteFolder = useCallback(async () => {
    const targetFolderId = selectedFolderId || ROOT;
    if (!targetFolderId || targetFolderId === ROOT) return;

    const folder = folderIndexesById.get(targetFolderId);
    const confirmed = window.confirm(
      `确认删除文件夹“${folder?.name || targetFolderId}”？\n请先确保该文件夹为空。`
    );
    if (!confirmed) return;

    clearFeedback();

    try {
      await permissionGroupsApi.removeFolder(targetFolderId);
      const parentFolderId = folder?.parent_id || ROOT;
      openFolder(parentFolderId);
      setSelectedItem(null);
      await fetchAll({ includeSupplemental: false });
      setHint('文件夹已删除');
    } catch (deleteError) {
      setError(mapUserFacingErrorMessage(deleteError?.message, '删除文件夹失败'));
    }
  }, [
    clearFeedback,
    fetchAll,
    folderIndexesById,
    openFolder,
    selectedFolderId,
    setError,
    setHint,
    setSelectedItem,
  ]);

  const toggleNodeAuth = useCallback((nodeId) => {
    setFormData((previous) => ({
      ...previous,
      accessible_kb_nodes: toggleInArray(previous.accessible_kb_nodes, nodeId),
    }));
  }, [setFormData]);

  const toggleKbAuth = useCallback((kbId) => {
    setFormData((previous) => ({
      ...previous,
      accessible_kbs: toggleInArray(previous.accessible_kbs, kbId),
    }));
  }, [setFormData]);

  const toggleChatAuth = useCallback((chatId) => {
    setFormData((previous) => ({
      ...previous,
      accessible_chats: toggleInArray(previous.accessible_chats, chatId),
    }));
  }, [setFormData]);

  const moveGroupToFolder = useCallback(
    async (groupId, folderId) => {
      if (!groupId) return;

      clearFeedback();

      try {
        await permissionGroupsApi.update(groupId, { folder_id: folderId || null });
        const nextGroups = await fetchAll({ includeSupplemental: false });
        const movedGroup = nextGroups.find((group) => group.group_id === groupId);

        if (editingGroupId === groupId && movedGroup) {
          setFormData((previous) => ({
            ...previous,
            folder_id: movedGroup.folder_id || null,
          }));
        }

        setHint('权限组已移动');
      } catch (moveError) {
        setError(mapUserFacingErrorMessage(moveError?.message, '移动权限组失败'));
      }
    },
    [clearFeedback, editingGroupId, fetchAll, setError, setFormData, setHint]
  );

  return {
    ensureFolderExpanded,
    openFolder,
    startCreateGroup,
    viewGroup,
    startEditGroup,
    activateGroup: startEditGroup,
    saveForm,
    cancelEdit,
    removeGroup,
    createFolder,
    renameFolder,
    deleteFolder,
    toggleNodeAuth,
    toggleKbAuth,
    toggleChatAuth,
    moveGroupToFolder,
  };
}
