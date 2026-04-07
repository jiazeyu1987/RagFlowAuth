import { act, renderHook } from '@testing-library/react';
import { useUserManagementActions } from './useUserManagementActions';
import { useUserPolicySubmission } from './useUserPolicySubmission';

jest.mock('./useUserPolicySubmission', () => ({
  useUserPolicySubmission: jest.fn(),
}));

describe('useUserManagementActions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useUserPolicySubmission.mockReturnValue({
      policySubmitting: false,
      handleSavePolicy: jest.fn(),
    });
  });

  it('clears kb directory errors before forwarding create and policy actions', () => {
    const events = [];
    const createManagement = {
      handleOpenCreateModal: jest.fn(() => events.push('open-create')),
      handleCloseCreateModal: jest.fn(() => events.push('close-create')),
      setNewUserField: jest.fn((field, value) => events.push(`field:${field}:${value}`)),
      handleCreateUser: jest.fn(),
    };
    const policyManagement = {
      handleOpenPolicyModal: jest.fn((user) => events.push(`open-policy:${user.user_id}`)),
      handleClosePolicyModal: jest.fn(() => events.push('close-policy')),
      handleChangePolicyForm: jest.fn((value) => events.push(`change-policy:${value.user_type}`)),
      policyUser: { user_id: 'u-1' },
      policyForm: { user_type: 'normal' },
      setPolicyError: jest.fn(),
    };
    const clearKbDirectoryCreateError = jest.fn(() => events.push('clear'));

    const { result } = renderHook(() =>
      useUserManagementActions({
        createManagement,
        policyManagement,
        kbDirectoryNodes: [],
        orgDirectoryError: null,
        clearKbDirectoryCreateError,
        fetchUsers: jest.fn(),
        mapErrorMessage: (value) => value,
      })
    );

    act(() => {
      result.current.handleOpenCreateModal();
      result.current.handleCloseCreateModal();
      result.current.setNewUserField('company_id', '1');
      result.current.handleOpenPolicyModal({ user_id: 'u-1' });
      result.current.handleClosePolicyModal();
      result.current.handleChangePolicyForm({ user_type: 'sub_admin' });
    });

    expect(events).toEqual([
      'clear',
      'open-create',
      'clear',
      'close-create',
      'clear',
      'field:company_id:1',
      'clear',
      'open-policy:u-1',
      'clear',
      'close-policy',
      'clear',
      'change-policy:sub_admin',
    ]);
  });

  it('passes create and policy submission dependencies through unchanged', async () => {
    const handleSavePolicy = jest.fn();
    useUserPolicySubmission.mockReturnValue({
      policySubmitting: true,
      handleSavePolicy,
    });

    const createManagement = {
      handleOpenCreateModal: jest.fn(),
      handleCloseCreateModal: jest.fn(),
      setNewUserField: jest.fn(),
      handleCreateUser: jest.fn(),
    };
    const policyManagement = {
      handleOpenPolicyModal: jest.fn(),
      handleClosePolicyModal: jest.fn(),
      handleChangePolicyForm: jest.fn(),
      policyUser: { user_id: 'u-2' },
      policyForm: { user_type: 'normal' },
      setPolicyError: jest.fn(),
    };
    const fetchUsers = jest.fn();

    const { result } = renderHook(() =>
      useUserManagementActions({
        createManagement,
        policyManagement,
        kbDirectoryNodes: [{ id: 'node-1' }],
        orgDirectoryError: 'org error',
        clearKbDirectoryCreateError: jest.fn(),
        fetchUsers,
        mapErrorMessage: (value) => value,
      })
    );

    await act(async () => {
      await result.current.handleCreateUser({ preventDefault() {} });
    });

    expect(createManagement.handleCreateUser).toHaveBeenCalledWith(
      expect.any(Object),
      {
        kbDirectoryNodes: [{ id: 'node-1' }],
        orgDirectoryError: 'org error',
      }
    );
    expect(result.current.policySubmitting).toBe(true);
    expect(result.current.handleSavePolicy).toBe(handleSavePolicy);
    expect(useUserPolicySubmission).toHaveBeenCalledWith({
      fetchUsers,
      kbDirectoryNodes: [{ id: 'node-1' }],
      orgDirectoryError: 'org error',
      policyUser: policyManagement.policyUser,
      policyForm: policyManagement.policyForm,
      setPolicyError: policyManagement.setPolicyError,
      handleClosePolicyModal: result.current.handleClosePolicyModal,
      mapErrorMessage: expect.any(Function),
    });
  });
});
