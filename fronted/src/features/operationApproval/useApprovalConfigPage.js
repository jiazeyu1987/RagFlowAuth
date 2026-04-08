import { useCallback, useState } from 'react';
import operationApprovalApi from './api';
import {
  WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE,
  WORKFLOW_MEMBER_TYPE_USER,
  buildMemberSearchKey,
  buildUserLabel,
  buildWorkflowPayload,
  createUserSearchState,
  specialRoleLabel,
  validateWorkflowDraft,
} from './approvalConfigHelpers';
import useApprovalConfigData from './useApprovalConfigData';
import useApprovalConfigDraftState from './useApprovalConfigDraftState';
import useApprovalConfigMemberSearch from './useApprovalConfigMemberSearch';

export {
  WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE,
  WORKFLOW_MEMBER_TYPE_USER,
  buildMemberSearchKey,
  buildUserLabel,
  createUserSearchState,
  specialRoleLabel,
};

export default function useApprovalConfigPage() {
  const [savingKey, setSavingKey] = useState('');
  const [saveMessage, setSaveMessage] = useState('');
  const {
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
  } = useApprovalConfigData();
  const {
    currentDraft,
    updateDraft,
    setCurrentDraftName,
    addStep,
    removeStep,
    updateStepField,
    addMember,
    removeMember,
    updateMemberField,
  } = useApprovalConfigDraftState({
    drafts,
    setDrafts,
    currentOperationType,
  });
  const {
    updateMemberSearchState,
    handleMemberUserKeywordChange,
    handleSelectMemberUser,
    getMemberSearchState,
  } = useApprovalConfigMemberSearch({
    mergeUsersIntoDirectory,
    updateDraft,
  });

  const handleSave = useCallback(async () => {
    if (!currentDraft) {
      return;
    }

    const validationError = validateWorkflowDraft(currentDraft);
    if (validationError) {
      setError(`${currentDraft.operation_label}: ${validationError}`);
      return;
    }

    setSavingKey(currentDraft.operation_type);
    setError('');
    setSaveMessage('');
    try {
      await operationApprovalApi.updateWorkflow(
        currentDraft.operation_type,
        buildWorkflowPayload(currentDraft)
      );
      setSaveMessage(`${currentDraft.operation_label} 审批流程已保存`);
      await loadData();
    } catch (requestError) {
      setError(requestError?.message || '保存审批流程失败');
    } finally {
      setSavingKey('');
    }
  }, [currentDraft, loadData, setError]);

  return {
    loading,
    savingKey,
    error,
    saveMessage,
    drafts,
    currentOperationType,
    currentDraft,
    searchUsers,
    updateMemberSearchState,
    loadData,
    setCurrentOperationType,
    setCurrentDraftName,
    addStep,
    removeStep,
    updateStepField,
    addMember,
    removeMember,
    updateMemberField,
    handleMemberUserKeywordChange,
    handleSelectMemberUser,
    handleSave,
    getSelectedUser,
    getMemberSearchState,
  };
}
