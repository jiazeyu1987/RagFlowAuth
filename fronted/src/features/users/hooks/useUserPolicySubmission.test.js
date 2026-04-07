import { act, renderHook, waitFor } from '@testing-library/react';
import { usersApi } from '../api';
import { useUserPolicySubmission } from './useUserPolicySubmission';

jest.mock('../api', () => ({
  usersApi: {
    update: jest.fn(),
  },
}));

describe('useUserPolicySubmission', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    usersApi.update.mockResolvedValue({});
  });

  it('saves a valid policy update and closes the modal', async () => {
    const fetchUsers = jest.fn().mockResolvedValue(undefined);
    const handleClosePolicyModal = jest.fn();
    const setPolicyError = jest.fn();

    const { result } = renderHook(() =>
      useUserPolicySubmission({
        fetchUsers,
        kbDirectoryNodes: [{ id: 'node-1' }],
        orgDirectoryError: null,
        policyUser: {
          user_id: 'u-2',
          role: 'sub_admin',
        },
        policyForm: {
          full_name: 'Sub A',
          company_id: '1',
          department_id: '11',
          user_type: 'sub_admin',
          manager_user_id: '',
          managed_kb_root_node_id: 'node-1',
          group_ids: [7],
          max_login_sessions: 3,
          idle_timeout_minutes: 120,
          can_change_password: true,
          disable_account: false,
          disable_mode: 'immediate',
          disable_until_date: '',
        },
        setPolicyError,
        handleClosePolicyModal,
        mapErrorMessage: (value) => value,
      })
    );

    await act(async () => {
      await result.current.handleSavePolicy();
    });

    await waitFor(() =>
      expect(usersApi.update).toHaveBeenCalledWith(
        'u-2',
        expect.objectContaining({
          role: 'sub_admin',
          group_ids: [7],
        })
      )
    );
    expect(handleClosePolicyModal).toHaveBeenCalledTimes(1);
    expect(fetchUsers).toHaveBeenCalledTimes(1);
  });

  it('fails fast on invalid viewer policy submissions', async () => {
    const setPolicyError = jest.fn();

    const { result } = renderHook(() =>
      useUserPolicySubmission({
        fetchUsers: jest.fn(),
        kbDirectoryNodes: [],
        orgDirectoryError: null,
        policyUser: {
          user_id: 'u-1',
          role: 'viewer',
        },
        policyForm: {
          full_name: 'Viewer A',
          company_id: '1',
          department_id: '11',
          user_type: 'normal',
          manager_user_id: '',
          managed_kb_root_node_id: '',
          group_ids: [],
          max_login_sessions: 3,
          idle_timeout_minutes: 120,
          can_change_password: true,
          disable_account: false,
          disable_mode: 'immediate',
          disable_until_date: '',
        },
        setPolicyError,
        handleClosePolicyModal: jest.fn(),
        mapErrorMessage: (value) => value,
      })
    );

    await act(async () => {
      await result.current.handleSavePolicy();
    });

    expect(setPolicyError).toHaveBeenCalledWith('请选择归属子管理员');
    expect(usersApi.update).not.toHaveBeenCalled();
  });
});
