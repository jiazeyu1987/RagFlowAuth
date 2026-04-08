import { useEffect, useMemo, useRef, useState } from 'react';

import { ROOT } from './constants';
import {
  buildContentRows,
  buildCreateForm,
  buildFolderPath,
  buildKnowledgeDatasetItems,
  buildKnowledgeNodeTreeNodes,
  filterContentRows,
} from './permissionGroupManagementHelpers';
import usePermissionGroupManagementActions from './usePermissionGroupManagementActions';
import usePermissionGroupManagementData from './usePermissionGroupManagementData';
import usePermissionGroupManagementDrag from './usePermissionGroupManagementDrag';
import { buildFolderIndexes } from './utils';

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
  const [formData, setFormData] = useState(buildCreateForm(null));

  const modeRef = useRef(mode);
  const folderIndexesRef = useRef(new Map());

  const folderIndexes = useMemo(() => buildFolderIndexes(groupFolders), [groupFolders]);

  useEffect(() => {
    folderIndexesRef.current = folderIndexes.byId;
  }, [folderIndexes.byId]);

  const groupsInCurrentFolder = useMemo(
    () => groups.filter((group) => (group.folder_id || ROOT) === currentFolderId),
    [currentFolderId, groups]
  );

  const folderPath = useMemo(
    () => buildFolderPath(currentFolderId, folderIndexes.byId),
    [currentFolderId, folderIndexes.byId]
  );

  const contentRows = useMemo(
    () =>
      buildContentRows(currentFolderId, folderIndexes.childrenByParent, groupsInCurrentFolder),
    [currentFolderId, folderIndexes.childrenByParent, groupsInCurrentFolder]
  );

  const filteredRows = useMemo(
    () => filterContentRows(contentRows, searchKeyword),
    [contentRows, searchKeyword]
  );

  const editingGroup = useMemo(
    () => groups.find((group) => group.group_id === editingGroupId) || null,
    [editingGroupId, groups]
  );

  const knowledgeNodeTreeNodes = useMemo(
    () => buildKnowledgeNodeTreeNodes(knowledgeTree?.nodes),
    [knowledgeTree?.nodes]
  );

  const knowledgeDatasetItems = useMemo(
    () => buildKnowledgeDatasetItems(knowledgeTree?.datasets),
    [knowledgeTree?.datasets]
  );

  const { fetchAll } = usePermissionGroupManagementData({
    setChatAgents,
    setError,
    setGroupFolders,
    setGroups,
    setKnowledgeTree,
    setLoading,
  });

  const {
    openFolder,
    startCreateGroup,
    viewGroup,
    startEditGroup,
    activateGroup,
    saveForm,
    cancelEdit,
    removeGroup,
    createFolder,
    renameFolder,
    deleteFolder,
    toggleNodeAuth,
    toggleKbAuth,
    toggleChatAuth,
    toggleToolAuth,
    moveGroupToFolder,
  } = usePermissionGroupManagementActions({
    currentFolderId,
    editingGroup,
    editingGroupId,
    fetchAll,
    folderIndexesById: folderIndexes.byId,
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
  });

  const {
    onDragOverFolder,
    onDropFolder,
    onDragLeaveFolder,
    startGroupDrag,
    endGroupDrag,
  } = usePermissionGroupManagementDrag({
    dragGroupId,
    dropTargetFolderId,
    moveGroupToFolder,
    setDragGroupId,
    setDropTargetFolderId,
  });

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  useEffect(() => {
    let active = true;

    fetchAll().then((loadedGroups) => {
      if (!active) return;
      if (modeRef.current === 'create' || modeRef.current === 'edit') return;

      if (loadedGroups.length) {
        viewGroup(loadedGroups[0]);
        return;
      }

      setSelectedItem({ kind: 'folder', id: ROOT });
      setCurrentFolderId(ROOT);
      setSelectedFolderId(ROOT);
      setMode('create');
      setEditingGroupId(null);
      setFormData(buildCreateForm(null));
    });

    return () => {
      active = false;
    };
  }, [fetchAll, viewGroup]);

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
    mode,
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
    viewGroup,
    startEditGroup,
    activateGroup,
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
