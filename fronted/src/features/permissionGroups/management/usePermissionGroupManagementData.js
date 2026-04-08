import { useCallback } from 'react';

import { permissionGroupsApi } from '../api';
import { filterVisibleChats } from './permissionGroupManagementHelpers';
import { normalizeGroups } from './utils';

export default function usePermissionGroupManagementData({
  setChatAgents,
  setError,
  setGroupFolders,
  setGroups,
  setKnowledgeTree,
  setLoading,
}) {
  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const [groupsResponse, folderResponse, knowledgeTreeResponse, chatsResponse] = await Promise.all([
        permissionGroupsApi.list(),
        permissionGroupsApi.listGroupFolders(),
        permissionGroupsApi.listKnowledgeTree(),
        permissionGroupsApi.listChats(),
      ]);

      const normalizedGroups = normalizeGroups(groupsResponse, folderResponse.group_bindings);

      setGroups(normalizedGroups);
      setGroupFolders(folderResponse.folders);
      setKnowledgeTree(knowledgeTreeResponse);
      setChatAgents(filterVisibleChats(chatsResponse));

      return normalizedGroups;
    } catch (requestError) {
      setError(requestError?.message || '加载权限组失败');
      return [];
    } finally {
      setLoading(false);
    }
  }, [setChatAgents, setError, setGroupFolders, setGroups, setKnowledgeTree, setLoading]);

  return {
    fetchAll,
  };
}
