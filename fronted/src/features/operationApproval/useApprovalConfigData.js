import { useCallback, useEffect, useState } from 'react';
import { mapUserFacingErrorMessage } from '../../shared/errors/userFacingErrorMessages';
import operationApprovalApi from './api';
import {
  USER_SEARCH_LIMIT,
  collectConfiguredUserIds,
  createDraftFromWorkflow,
} from './approvalConfigHelpers';
import { usersApi } from '../users/api';

export default function useApprovalConfigData() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [drafts, setDrafts] = useState([]);
  const [userDirectory, setUserDirectory] = useState({});
  const [currentOperationType, setCurrentOperationType] = useState('');

  const mergeUsersIntoDirectory = useCallback((items) => {
    setUserDirectory((prev) => {
      let changed = false;
      const next = { ...prev };

      (items || []).forEach((item) => {
        const userId = String(item?.user_id || '').trim();
        if (!userId) {
          return;
        }
        next[userId] = item;
        changed = true;
      });

      return changed ? next : prev;
    });
  }, []);

  const searchUsers = useCallback(
    async (keyword) => {
      const items = await usersApi.search(keyword, USER_SEARCH_LIMIT);
      mergeUsersIntoDirectory(items);
      return items;
    },
    [mergeUsersIntoDirectory]
  );

  const hydrateConfiguredUsers = useCallback(
    async (nextDrafts) => {
      const configuredIds = collectConfiguredUserIds(nextDrafts);
      if (configuredIds.length === 0) {
        return;
      }

      const resolvedUsers = await Promise.all(
        configuredIds.map((userId) => usersApi.get(userId))
      );
      mergeUsersIntoDirectory(resolvedUsers);
    },
    [mergeUsersIntoDirectory]
  );

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const workflowItems = await operationApprovalApi.listWorkflows();
      const nextDrafts = workflowItems.map(createDraftFromWorkflow);
      setDrafts(nextDrafts);
      await hydrateConfiguredUsers(nextDrafts);
      setCurrentOperationType((prev) => {
        if (prev && nextDrafts.some((draft) => draft.operation_type === prev)) {
          return prev;
        }
        return nextDrafts[0]?.operation_type || '';
      });
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, '加载审批配置失败'));
      setDrafts([]);
      setCurrentOperationType('');
    } finally {
      setLoading(false);
    }
  }, [hydrateConfiguredUsers]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const getSelectedUser = useCallback(
    (memberRef) => userDirectory[String(memberRef || '')] || null,
    [userDirectory]
  );

  return {
    loading,
    error,
    setError,
    drafts,
    setDrafts,
    currentOperationType,
    setCurrentOperationType,
    searchUsers,
    loadData,
    mergeUsersIntoDirectory,
    getSelectedUser,
  };
}
