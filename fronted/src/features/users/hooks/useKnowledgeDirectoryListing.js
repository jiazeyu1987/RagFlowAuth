import { useCallback, useMemo, useState } from 'react';
import { knowledgeApi } from '../../knowledge/api';
import {
  buildEmptyKnowledgeDirectoryListingState,
  buildKnowledgeDirectoryListingErrorState,
  buildKnowledgeDirectoryQuery,
  buildKnowledgeDirectoryListingSuccessState,
} from '../utils/userKnowledgeDirectories';
import { buildManagedKbRootSelectionState } from '../utils/userManagedKbRoots';
import { isManagedKbRootSelectionInvalid } from '../utils/userManagementDerivedState';
import { runStateAction } from '../utils/userManagementActionRunners';
import { runUserManagementMutation } from '../utils/userManagementMutations';
import { useKnowledgeDirectoryModeLoader } from './useKnowledgeDirectoryModeLoader';
import { useKnowledgeDirectoryModeReset } from './useKnowledgeDirectoryModeReset';

export const useKnowledgeDirectoryListing = ({
  allUsers,
  isAdminUser,
  createMode,
  policyMode,
  policyUser,
  mapErrorMessage,
  loadErrorMessage,
}) => {
  const [kbDirectorySourceNodes, setKbDirectorySourceNodes] = useState([]);
  const [kbDirectoryLoading, setKbDirectoryLoading] = useState(false);
  const [kbDirectoryError, setKbDirectoryError] = useState(null);

  const applyKnowledgeDirectoryListingState = useCallback((nextState) => {
    setKbDirectorySourceNodes(nextState.nodes);
    setKbDirectoryError(nextState.error);
  }, []);

  const clearKnowledgeDirectoryListing = useCallback(() => {
    runStateAction(
      applyKnowledgeDirectoryListingState,
      buildEmptyKnowledgeDirectoryListingState
    );
  }, [applyKnowledgeDirectoryListingState]);

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

  const managedKbRootSelectionContext = useMemo(() => {
    if (policyMode.isOpen && String(policyMode.userType || 'normal') === 'sub_admin') {
      return {
        companyId: policyMode.companyId,
        excludeUserId: policyUser?.user_id,
        selectedNodeId: policyMode.selectedManagedKbRootNodeId,
      };
    }
    if (createMode.isOpen && String(createMode.userType || 'normal') === 'sub_admin') {
      return {
        companyId: createMode.companyId,
        excludeUserId: '',
        selectedNodeId: createMode.selectedManagedKbRootNodeId,
      };
    }
    return {
      companyId: null,
      excludeUserId: '',
      selectedNodeId: '',
    };
  }, [
    createMode.companyId,
    createMode.isOpen,
    createMode.selectedManagedKbRootNodeId,
    createMode.userType,
    policyMode.companyId,
    policyMode.isOpen,
    policyMode.selectedManagedKbRootNodeId,
    policyMode.userType,
    policyUser?.user_id,
  ]);

  const managedKbRootSelectionState = useMemo(
    () =>
      buildManagedKbRootSelectionState({
        nodes: kbDirectorySourceNodes,
        users: allUsers,
        companyId: managedKbRootSelectionContext.companyId,
        excludeUserId: managedKbRootSelectionContext.excludeUserId,
        selectedNodeId: managedKbRootSelectionContext.selectedNodeId,
      }),
    [
      allUsers,
      kbDirectorySourceNodes,
      managedKbRootSelectionContext.companyId,
      managedKbRootSelectionContext.excludeUserId,
      managedKbRootSelectionContext.selectedNodeId,
    ]
  );

  const kbDirectoryNodes = managedKbRootSelectionState.nodes;
  const kbDirectoryDisabledNodeIds = managedKbRootSelectionState.disabledNodeIds;

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
    kbDirectoryDisabledNodeIds,
    kbDirectoryLoading,
    kbDirectoryError,
    managedKbRootInvalid,
    fetchKnowledgeDirectories,
  };
};
