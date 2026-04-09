import { act, renderHook, waitFor } from '@testing-library/react';
import { usersApi } from '../api';
import { useUserCreateManagement } from './useUserCreateManagement';

jest.mock('../api', () => ({
  usersApi: {
    create: jest.fn(),
  },
}));

describe('useUserCreateManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    usersApi.create.mockResolvedValue({});
  });

  it('clears mismatched departments after the selected company changes', async () => {
    const { result } = renderHook(() =>
      useUserCreateManagement({
        departments: [{ id: 11, company_id: 2, name: 'Ops' }],
        fetchUsers: jest.fn(),
        mapErrorMessage: (value) => value,
      })
    );

    act(() => {
      result.current.setNewUserField('company_id', '1');
      result.current.setNewUserField('department_id', '11');
    });

    await waitFor(() => expect(result.current.newUser.department_id).toBe(''));
  });

  it('defaults create modal company to target company when present', async () => {
    const { result } = renderHook(() =>
      useUserCreateManagement({
        companies: [
          { id: 8, name: 'Other Co' },
          { id: 19, name: '\u745b\u6cf0\u533b\u7597' },
        ],
        departments: [],
        fetchUsers: jest.fn(),
        mapErrorMessage: (value) => value,
      })
    );

    act(() => {
      result.current.handleOpenCreateModal();
    });

    await waitFor(() => expect(result.current.newUser.company_id).toBe('19'));
  });

  it('submits a valid create request and resets modal state', async () => {
    const fetchUsers = jest.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() =>
      useUserCreateManagement({
        departments: [{ id: 11, company_id: 1, name: 'QA' }],
        fetchUsers,
        mapErrorMessage: (value) => value,
      })
    );

    act(() => {
      result.current.handleOpenCreateModal();
      result.current.setNewUserField('username', 'emp-001');
      result.current.setNewUserField('employee_user_id', 'emp-001');
      result.current.setNewUserField('full_name', 'Alice');
      result.current.setNewUserField('company_id', '1');
      result.current.setNewUserField('department_id', '11');
      result.current.setNewUserField('manager_user_id', 'sub-1');
    });

    await act(async () => {
      await result.current.handleCreateUser(
        { preventDefault() {} },
        { kbDirectoryNodes: [], orgDirectoryError: null }
      );
    });

    await waitFor(() =>
      expect(usersApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          role: 'viewer',
          username: 'emp-001',
          employee_user_id: 'emp-001',
          company_id: 1,
          department_id: 11,
          manager_user_id: 'sub-1',
        })
      )
    );
    expect(fetchUsers).toHaveBeenCalledTimes(1);
    expect(result.current.showCreateModal).toBe(false);
  });
});
