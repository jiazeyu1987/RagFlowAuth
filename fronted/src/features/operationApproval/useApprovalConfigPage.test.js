import { act, renderHook, waitFor } from '@testing-library/react';
import operationApprovalApi from './api';
import { usersApi } from '../users/api';
import useApprovalConfigPage from './useApprovalConfigPage';

jest.mock('./api', () => ({
  __esModule: true,
  default: {
    listWorkflows: jest.fn(),
    updateWorkflow: jest.fn(),
  },
}));

jest.mock('../users/api', () => ({
  __esModule: true,
  usersApi: {
    search: jest.fn(),
  },
}));

const workflowResponse = {
  items: [
    {
      operation_type: 'knowledge_file_upload',
      operation_label: '文件上传',
      name: '文件上传审批流',
      is_configured: true,
      steps: [
        {
          step_no: 1,
          step_name: '第一层',
          members: [
            {
              member_type: 'user',
              member_ref: 'u-1',
            },
          ],
        },
      ],
    },
  ],
};

describe('useApprovalConfigPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    operationApprovalApi.listWorkflows.mockResolvedValue(workflowResponse);
    operationApprovalApi.updateWorkflow.mockResolvedValue({});
    usersApi.search.mockImplementation(async (keyword) => {
      const normalized = String(keyword || '').trim().toLowerCase();
      const items = [
        { user_id: 'u-1', username: 'alice', full_name: 'Alice' },
        { user_id: 'u-3', username: 'carol', full_name: 'Carol' },
      ];
      return items.filter((item) => (
        item.user_id.toLowerCase().includes(normalized)
        || item.username.toLowerCase().includes(normalized)
        || item.full_name.toLowerCase().includes(normalized)
      ));
    });
  });

  it('loads workflows and hydrates configured users into stable hook state', async () => {
    const { result } = renderHook(() => useApprovalConfigPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(operationApprovalApi.listWorkflows).toHaveBeenCalledTimes(1);
    expect(usersApi.search).toHaveBeenCalledWith('u-1', 20);
    expect(result.current.currentOperationType).toBe('knowledge_file_upload');
    expect(result.current.currentDraft).toEqual(
      expect.objectContaining({
        name: '文件上传审批流',
        operation_label: '文件上传',
      })
    );
    expect(result.current.getSelectedUser('u-1')).toEqual(
      expect.objectContaining({
        full_name: 'Alice',
      })
    );
  });

  it('saves the edited workflow through the feature api with normalized members', async () => {
    const { result } = renderHook(() => useApprovalConfigPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      result.current.addMember(0);
      result.current.updateMemberField(0, 1, 'member_type', 'special_role');
    });

    await act(async () => {
      await result.current.handleSave();
    });

    await waitFor(() => {
      expect(operationApprovalApi.updateWorkflow).toHaveBeenCalledWith(
        'knowledge_file_upload',
        expect.objectContaining({
          name: '文件上传审批流',
          steps: [
            {
              step_name: '第一层',
              step_no: 1,
              members: [
                {
                  member_type: 'user',
                  member_ref: 'u-1',
                },
                {
                  member_type: 'special_role',
                  member_ref: 'direct_manager',
                },
              ],
            },
          ],
        })
      );
    });
  });
});
