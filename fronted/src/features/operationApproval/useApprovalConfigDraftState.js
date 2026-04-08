import { useCallback, useMemo } from 'react';
import {
  SPECIAL_ROLE_DIRECT_MANAGER,
  WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE,
  WORKFLOW_MEMBER_TYPE_USER,
  createEmptyMember,
  createEmptyStep,
} from './approvalConfigHelpers';

export default function useApprovalConfigDraftState({
  drafts,
  setDrafts,
  currentOperationType,
}) {
  const currentDraft = useMemo(
    () => drafts.find((draft) => draft.operation_type === currentOperationType) || null,
    [currentOperationType, drafts]
  );

  const updateDraft = useCallback((operationType, updater) => {
    setDrafts((prev) =>
      prev.map((draft) => (draft.operation_type === operationType ? updater(draft) : draft))
    );
  }, [setDrafts]);

  const updateCurrentDraft = useCallback(
    (updater) => {
      if (!currentOperationType) {
        return;
      }
      updateDraft(currentOperationType, updater);
    },
    [currentOperationType, updateDraft]
  );

  const setCurrentDraftName = useCallback(
    (value) => {
      updateCurrentDraft((draft) => ({
        ...draft,
        name: value,
      }));
    },
    [updateCurrentDraft]
  );

  const addStep = useCallback(() => {
    updateCurrentDraft((draft) => ({
      ...draft,
      steps: [...(draft.steps || []), createEmptyStep((draft.steps || []).length + 1)],
    }));
  }, [updateCurrentDraft]);

  const removeStep = useCallback((index) => {
    updateCurrentDraft((draft) => ({
      ...draft,
      steps: (draft.steps || [])
        .filter((_, stepIndex) => stepIndex !== index)
        .map((step, stepIndex) => ({ ...step, step_no: stepIndex + 1 })),
    }));
  }, [updateCurrentDraft]);

  const updateStepField = useCallback((index, field, value) => {
    updateCurrentDraft((draft) => ({
      ...draft,
      steps: (draft.steps || []).map((step, stepIndex) =>
        stepIndex === index ? { ...step, [field]: value } : step
      ),
    }));
  }, [updateCurrentDraft]);

  const addMember = useCallback((stepIndex) => {
    updateCurrentDraft((draft) => ({
      ...draft,
      steps: (draft.steps || []).map((step, index) =>
        index === stepIndex
          ? { ...step, members: [...(step.members || []), createEmptyMember()] }
          : step
      ),
    }));
  }, [updateCurrentDraft]);

  const removeMember = useCallback((stepIndex, memberIndex) => {
    updateCurrentDraft((draft) => ({
      ...draft,
      steps: (draft.steps || []).map((step, index) => {
        if (index !== stepIndex) {
          return step;
        }

        const nextMembers = (step.members || []).filter(
          (_, currentMemberIndex) => currentMemberIndex !== memberIndex
        );
        return {
          ...step,
          members: nextMembers.length > 0 ? nextMembers : [createEmptyMember()],
        };
      }),
    }));
  }, [updateCurrentDraft]);

  const updateMemberField = useCallback((stepIndex, memberIndex, field, value) => {
    updateCurrentDraft((draft) => ({
      ...draft,
      steps: (draft.steps || []).map((step, index) => {
        if (index !== stepIndex) {
          return step;
        }

        return {
          ...step,
          members: (step.members || []).map((member, currentMemberIndex) => {
            if (currentMemberIndex !== memberIndex) {
              return member;
            }

            const nextMember = { ...member, [field]: value };
            if (field === 'member_type' && value === WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE) {
              nextMember.member_ref = SPECIAL_ROLE_DIRECT_MANAGER;
            }
            if (field === 'member_type' && value === WORKFLOW_MEMBER_TYPE_USER) {
              nextMember.member_ref = '';
            }
            return nextMember;
          }),
        };
      }),
    }));
  }, [updateCurrentDraft]);

  return {
    currentDraft,
    updateDraft,
    setCurrentDraftName,
    addStep,
    removeStep,
    updateStepField,
    addMember,
    removeMember,
    updateMemberField,
  };
}
