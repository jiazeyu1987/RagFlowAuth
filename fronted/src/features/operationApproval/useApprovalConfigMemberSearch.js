import { useCallback, useState } from 'react';
import {
  buildMemberSearchKey,
  buildUserLabel,
  createUserSearchState,
} from './approvalConfigHelpers';

export default function useApprovalConfigMemberSearch({
  mergeUsersIntoDirectory,
  updateDraft,
}) {
  const [memberSearchStates, setMemberSearchStates] = useState({});

  const updateMemberSearchState = useCallback((searchKey, updater) => {
    setMemberSearchStates((prev) => {
      const current = prev[searchKey] || createUserSearchState();
      const nextState = typeof updater === 'function' ? updater(current) : updater;
      return {
        ...prev,
        [searchKey]: nextState,
      };
    });
  }, []);

  const handleMemberUserKeywordChange = useCallback((operationType, stepIndex, memberIndex, value) => {
    const searchKey = buildMemberSearchKey(operationType, stepIndex, memberIndex);
    updateDraft(operationType, (draft) => ({
      ...draft,
      steps: (draft.steps || []).map((step, currentStepIndex) => {
        if (currentStepIndex !== stepIndex) {
          return step;
        }
        return {
          ...step,
          members: (step.members || []).map((member, currentMemberIndex) =>
            currentMemberIndex === memberIndex ? { ...member, member_ref: '' } : member
          ),
        };
      }),
    }));
    updateMemberSearchState(searchKey, (prev) => ({
      ...prev,
      keyword: value,
      open: true,
      error: '',
      ...(String(value || '').trim() ? {} : { results: [] }),
    }));
  }, [updateDraft, updateMemberSearchState]);

  const handleSelectMemberUser = useCallback((operationType, stepIndex, memberIndex, selectedUser) => {
    const searchKey = buildMemberSearchKey(operationType, stepIndex, memberIndex);
    mergeUsersIntoDirectory([selectedUser]);
    updateDraft(operationType, (draft) => ({
      ...draft,
      steps: (draft.steps || []).map((step, currentStepIndex) => {
        if (currentStepIndex !== stepIndex) {
          return step;
        }
        return {
          ...step,
          members: (step.members || []).map((member, currentMemberIndex) =>
            currentMemberIndex === memberIndex
              ? { ...member, member_ref: String(selectedUser?.user_id || '') }
              : member
          ),
        };
      }),
    }));
    updateMemberSearchState(searchKey, (prev) => ({
      ...prev,
      keyword: buildUserLabel(selectedUser),
      open: false,
      loading: false,
      results: [],
      error: '',
    }));
  }, [mergeUsersIntoDirectory, updateDraft, updateMemberSearchState]);

  const getMemberSearchState = useCallback(
    (operationType, stepIndex, memberIndex) =>
      memberSearchStates[buildMemberSearchKey(operationType, stepIndex, memberIndex)] ||
      createUserSearchState(),
    [memberSearchStates]
  );

  return {
    updateMemberSearchState,
    handleMemberUserKeywordChange,
    handleSelectMemberUser,
    getMemberSearchState,
  };
}
