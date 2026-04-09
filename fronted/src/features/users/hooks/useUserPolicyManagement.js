import { useCallback, useState } from 'react';
import { DEFAULT_POLICY_FORM } from '../utils/constants';
import {
  applyPolicyFormChange,
  togglePolicyGroupSelection,
  togglePolicyToolSelection,
} from '../utils/userManagementDrafts';
import {
  buildClosedPolicyState,
  buildOpenedPolicyState,
} from '../utils/userManagementFormState';
import {
  runStateAction,
} from '../utils/userManagementActionRunners';
import { useManagedDepartmentReset } from './useManagedDepartmentReset';

export const useUserPolicyManagement = ({
  departments,
  initialPolicyForm = DEFAULT_POLICY_FORM,
  clearKbDirectoryCreateError,
}) => {
  const [showPolicyModal, setShowPolicyModal] = useState(false);
  const [policyUser, setPolicyUser] = useState(null);
  const [policyError, setPolicyError] = useState(null);
  const [policyForm, setPolicyFormState] = useState(initialPolicyForm);

  const applyPolicyModalState = useCallback((nextState) => {
    setShowPolicyModal(nextState.showPolicyModal);
    setPolicyUser(nextState.policyUser);
    setPolicyError(nextState.policyError);
    setPolicyFormState(nextState.policyForm);
  }, []);

  const clearMismatchedDepartment = useCallback(() => {
    setPolicyFormState((prev) => ({ ...prev, department_id: '' }));
  }, []);

  useManagedDepartmentReset({
    companyId: policyForm.company_id,
    departmentId: policyForm.department_id,
    departments,
    resetDepartment: clearMismatchedDepartment,
  });

  const handleOpenPolicyModal = useCallback(
    (...args) => {
      clearKbDirectoryCreateError?.();
      runStateAction(
        applyPolicyModalState,
        buildOpenedPolicyState,
        ...args
      );
    },
    [applyPolicyModalState, clearKbDirectoryCreateError]
  );

  const handleClosePolicyModal = useCallback(
    () => {
      clearKbDirectoryCreateError?.();
      runStateAction(
        applyPolicyModalState,
        () => buildClosedPolicyState(initialPolicyForm)
      );
    },
    [applyPolicyModalState, clearKbDirectoryCreateError, initialPolicyForm]
  );

  const handleChangePolicyForm = useCallback((...args) => {
    setPolicyError(null);
    clearKbDirectoryCreateError?.();
    setPolicyFormState((previousState) => applyPolicyFormChange(previousState, ...args));
  }, [clearKbDirectoryCreateError]);

  const handleTogglePolicyGroup = useCallback(
    (groupId, checked) => {
      setPolicyFormState((prev) =>
        togglePolicyGroupSelection({
          draft: prev,
          groupId,
          checked,
          isPolicyAdminUser: String(policyUser?.role || '') === 'admin',
        })
      );
    },
    [policyUser]
  );

  const handleTogglePolicyTool = useCallback(
    (toolId, checked) => {
      setPolicyFormState((prev) =>
        togglePolicyToolSelection({
          draft: prev,
          toolId,
          checked,
          isPolicyAdminUser: String(policyUser?.role || '') === 'admin',
        })
      );
    },
    [policyUser]
  );

  return {
    showPolicyModal,
    policyUser,
    policyError,
    policyForm,
    setPolicyError,
    handleOpenPolicyModal,
    handleClosePolicyModal,
    handleChangePolicyForm,
    handleTogglePolicyGroup,
    handleTogglePolicyTool,
  };
};
