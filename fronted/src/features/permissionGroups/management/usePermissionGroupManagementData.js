import { useCallback } from 'react';

import { mapUserFacingErrorMessage } from '../../../shared/errors/userFacingErrorMessages';
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
  const loadSupplementalResources = useCallback(async () => {
    const [knowledgeTreeResult, chatsResult] = await Promise.allSettled([
      permissionGroupsApi.listKnowledgeTree(),
      permissionGroupsApi.listChats(),
    ]);

    if (knowledgeTreeResult.status === 'fulfilled') {
      setKnowledgeTree(knowledgeTreeResult.value);
    }

    if (chatsResult.status === 'fulfilled') {
      setChatAgents(filterVisibleChats(chatsResult.value));
    }
  }, [setChatAgents, setKnowledgeTree]);

  const fetchAll = useCallback(
    async (options = {}) => {
      const includeSupplemental = options.includeSupplemental !== false;

      setLoading(true);
      setError('');

      try {
        const [groupsResponse, folderResponse] = await Promise.all([
          permissionGroupsApi.list(),
          permissionGroupsApi.listGroupFolders(),
        ]);

        const normalizedGroups = normalizeGroups(groupsResponse, folderResponse.group_bindings);

        setGroups(normalizedGroups);
        setGroupFolders(folderResponse.folders);

        if (includeSupplemental) {
          void loadSupplementalResources();
        }

        return normalizedGroups;
      } catch (requestError) {
        setError(mapUserFacingErrorMessage(requestError?.message, '加载权限组失败'));
        return [];
      } finally {
        setLoading(false);
      }
    },
    [loadSupplementalResources, setError, setGroupFolders, setGroups, setLoading]
  );

  return {
    fetchAll,
    loadSupplementalResources,
  };
}
