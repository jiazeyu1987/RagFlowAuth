import { useCallback, useState } from 'react';
import { knowledgeApi } from '../../knowledge/api';
import { runPreparedUserManagementMutation } from '../utils/userManagementPreparedMutations';
import { prepareRootDirectoryCreateSubmission } from '../utils/userManagementSubmissions';
import {
  bindStateAction,
  runStateAction,
} from '../utils/userManagementActionRunners';
import {
  buildClearedKnowledgeDirectoryRootCreationState,
  buildResetKnowledgeDirectoryRootCreationState,
  bindRootDirectoryCreateAction,
} from '../utils/userKnowledgeDirectories';
import { useKnowledgeDirectoryModeReset } from './useKnowledgeDirectoryModeReset';

export const useKnowledgeDirectoryRootCreation = ({
  isAdminUser,
  createMode,
  policyMode,
  mapErrorMessage,
  companyRequiredMessage,
  nameRequiredMessage,
  createErrorMessage,
  fetchKnowledgeDirectories,
}) => {
  const [kbDirectoryCreatingRoot, setKbDirectoryCreatingRoot] = useState(false);
  const [kbDirectoryCreateError, setKbDirectoryCreateError] = useState(null);

  const applyKnowledgeDirectoryRootCreationState = useCallback((nextState) => {
    setKbDirectoryCreatingRoot(nextState.creatingRoot);
    setKbDirectoryCreateError(nextState.error);
  }, []);

  const clearKbDirectoryCreateError = useCallback(
    () =>
      runStateAction(
        applyKnowledgeDirectoryRootCreationState,
        buildClearedKnowledgeDirectoryRootCreationState,
        { creatingRoot: kbDirectoryCreatingRoot }
      ),
    [applyKnowledgeDirectoryRootCreationState, kbDirectoryCreatingRoot]
  );

  const resetKnowledgeDirectoryRootCreation = useCallback(
    bindStateAction(
      applyKnowledgeDirectoryRootCreationState,
      buildResetKnowledgeDirectoryRootCreationState
    ),
    [applyKnowledgeDirectoryRootCreationState]
  );

  useKnowledgeDirectoryModeReset({
    createMode,
    policyMode,
    resetKnowledgeDirectoryState: resetKnowledgeDirectoryRootCreation,
  });

  const createRootDirectory = useCallback(
    async ({ companyId, name, onCreated }) => {
      let createdNodeId = null;
      let normalizedCompanyId = null;
      clearKbDirectoryCreateError();

      const mutation = await runPreparedUserManagementMutation({
        prepareSubmission: () =>
          prepareRootDirectoryCreateSubmission({
            companyId,
            name,
            isAdminUser,
          }),
        getBlockingMessage: (submission) => {
          if (submission.errorCode === 'company_required') {
            return companyRequiredMessage;
          }
          if (submission.errorCode === 'name_required') {
            return nameRequiredMessage;
          }
          return submission.errorMessage;
        },
        mapErrorMessage,
        fallbackMessage: createErrorMessage,
        setError: setKbDirectoryCreateError,
        onPrepared: (submission) => {
          normalizedCompanyId = submission.normalizedCompanyId;
        },
        execute: (submission) =>
          knowledgeApi.createKnowledgeDirectory(submission.payload, submission.requestOptions),
        onSuccess: async (node) => {
          createdNodeId = String(node?.id || '').trim() || null;
          await fetchKnowledgeDirectories(normalizedCompanyId);
          if (createdNodeId && typeof onCreated === 'function') {
            onCreated(createdNodeId);
          }
        },
        setPending: setKbDirectoryCreatingRoot,
      });

      if (!mutation.ok) {
        return null;
      }
      return createdNodeId;
    },
    [
      companyRequiredMessage,
      createErrorMessage,
      fetchKnowledgeDirectories,
      isAdminUser,
      mapErrorMessage,
      nameRequiredMessage,
      clearKbDirectoryCreateError,
    ]
  );

  const handleCreateModalRootDirectory = useCallback(
    bindRootDirectoryCreateAction(createRootDirectory, createMode),
    [createMode.companyId, createMode.onRootCreated, createRootDirectory]
  );

  const handlePolicyRootDirectory = useCallback(
    bindRootDirectoryCreateAction(createRootDirectory, policyMode),
    [createRootDirectory, policyMode.companyId, policyMode.onRootCreated]
  );

  return {
    kbDirectoryCreatingRoot,
    kbDirectoryCreateError,
    clearKbDirectoryCreateError,
    resetKnowledgeDirectoryRootCreation,
    handleCreateModalRootDirectory,
    handlePolicyRootDirectory,
  };
};
