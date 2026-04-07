import { useCallback, useMemo, useState } from 'react';
import { knowledgeApi } from '../../knowledge/api';
import {
  buildEmptyKnowledgeDirectoryListingState,
  buildKnowledgeDirectoryListingErrorState,
  buildKnowledgeDirectoryQuery,
  buildKnowledgeDirectoryListingSuccessState,
} from '../utils/userKnowledgeDirectories';
import { isManagedKbRootSelectionInvalid } from '../utils/userManagementDerivedState';
import {
  bindStateAction,
  runStateAction,
} from '../utils/userManagementActionRunners';
import { runUserManagementMutation } from '../utils/userManagementMutations';
import { useKnowledgeDirectoryModeLoader } from './useKnowledgeDirectoryModeLoader';
import { useKnowledgeDirectoryModeReset } from './useKnowledgeDirectoryModeReset';

export const useKnowledgeDirectoryListing = ({
  isAdminUser,
  createMode,
  policyMode,
  policyUser,
  mapErrorMessage,
  loadErrorMessage,
}) => {
  const [kbDirectoryNodes, setKbDirectoryNodes] = useState([]);
  const [kbDirectoryLoading, setKbDirectoryLoading] = useState(false);
  const [kbDirectoryError, setKbDirectoryError] = useState(null);

  const applyKnowledgeDirectoryListingState = useCallback((nextState) => {
    setKbDirectoryNodes(nextState.nodes);
    setKbDirectoryError(nextState.error);
  }, []);

  const clearKnowledgeDirectoryListing = useCallback(
    bindStateAction(
      applyKnowledgeDirectoryListingState,
      buildEmptyKnowledgeDirectoryListingState
    ),
    [applyKnowledgeDirectoryListingState]
  );

  const fetchKnowledgeDirectories = useCallback(
    async (companyId) => {
      const query = buildKnowledgeDirectoryQuery({ companyId, isAdminUser });
      if (query == null) {
        clearKnowledgeDirectoryListing();
        return [];
      }

      let nodes = [];
      const mutation = await runUserManagementMutation({
        execute: () => knowledgeApi.listKnowledgeDirectories(query),
        mapErrorMessage,
        fallbackMessage: loadErrorMessage,
        onMappedError: (message) => {
          runStateAction(
            applyKnowledgeDirectoryListingState,
            buildKnowledgeDirectoryListingErrorState,
            message
          );
        },
        onSuccess: (data) => {
          const nextState = buildKnowledgeDirectoryListingSuccessState(data);
          nodes = nextState.nodes;
          applyKnowledgeDirectoryListingState(nextState);
        },
        setPending: setKbDirectoryLoading,
      });

      if (!mutation.ok) {
        return [];
      }
      return nodes;
    },
    [
      applyKnowledgeDirectoryListingState,
      clearKnowledgeDirectoryListing,
      isAdminUser,
      loadErrorMessage,
      mapErrorMessage,
    ]
  );

  const resetKnowledgeDirectoryListing = useCallback(() => {
    clearKnowledgeDirectoryListing();
    setKbDirectoryLoading(false);
  }, [clearKnowledgeDirectoryListing]);

  useKnowledgeDirectoryModeLoader({
    companyId: createMode.companyId,
    isOpen: createMode.isOpen,
    userType: createMode.userType,
    loadKnowledgeDirectories: fetchKnowledgeDirectories,
  });

  useKnowledgeDirectoryModeLoader({
    companyId: policyMode.companyId,
    isOpen: policyMode.isOpen,
    userType: policyMode.userType,
    loadKnowledgeDirectories: fetchKnowledgeDirectories,
  });

  useKnowledgeDirectoryModeReset({
    createMode,
    policyMode,
    resetKnowledgeDirectoryState: resetKnowledgeDirectoryListing,
  });

  const managedKbRootInvalid = useMemo(
    () =>
      isManagedKbRootSelectionInvalid({
        policyUserType: policyMode.userType,
        managedKbRootNodeId: policyUser?.managed_kb_root_node_id,
        managedKbRootPath: policyUser?.managed_kb_root_path,
        kbDirectoryNodes,
        selectedManagedKbRootNodeId: policyMode.selectedManagedKbRootNodeId,
      }),
    [
      kbDirectoryNodes,
      policyMode.selectedManagedKbRootNodeId,
      policyMode.userType,
      policyUser?.managed_kb_root_node_id,
      policyUser?.managed_kb_root_path,
    ]
  );

  return {
    kbDirectoryNodes,
    kbDirectoryLoading,
    kbDirectoryError,
    managedKbRootInvalid,
    fetchKnowledgeDirectories,
  };
};
