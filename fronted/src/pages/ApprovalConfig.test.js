import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ApprovalConfig from './ApprovalConfig';
import authClient from '../api/authClient';
import operationApprovalApi from '../features/operationApproval/api';

jest.mock('../api/authClient', () => ({
  __esModule: true,
  default: {
    listUsers: jest.fn(),
  },
}));

jest.mock('../features/operationApproval/api', () => ({
  __esModule: true,
  default: {
    listWorkflows: jest.fn(),
    updateWorkflow: jest.fn(),
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
    {
      operation_type: 'knowledge_file_delete',
      operation_label: '文件删除',
      name: '文件删除审批流',
      is_configured: true,
      steps: [
        {
          step_no: 1,
          step_name: '删除审批',
          members: [
            {
              member_type: 'user',
              member_ref: 'u-2',
            },
          ],
        },
      ],
    },
  ],
};

const activeUsers = [
  { user_id: 'u-1', username: 'alice', full_name: 'Alice' },
  { user_id: 'u-2', username: 'bob', full_name: 'Bob' },
  { user_id: 'u-3', username: 'carol', full_name: 'Carol' },
];

describe('ApprovalConfig', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    operationApprovalApi.listWorkflows.mockResolvedValue(workflowResponse);
    operationApprovalApi.updateWorkflow.mockResolvedValue({});
    authClient.listUsers.mockImplementation(async ({ q }) => {
      const keyword = String(q || '').trim().toLowerCase();
      return activeUsers.filter((item) => (
        item.user_id.toLowerCase().includes(keyword)
        || item.username.toLowerCase().includes(keyword)
        || item.full_name.toLowerCase().includes(keyword)
      ));
    });
  });

  it('switches workflow scenario by dropdown', async () => {
    const user = userEvent.setup();

    render(<ApprovalConfig />);

    await screen.findByTestId('approval-config-card-knowledge_file_upload');
    expect(screen.getByTestId('approval-config-name-knowledge_file_upload')).toHaveValue('文件上传审批流');

    await user.selectOptions(screen.getByTestId('approval-config-operation-select'), 'knowledge_file_delete');

    expect(await screen.findByTestId('approval-config-card-knowledge_file_delete')).toBeInTheDocument();
    expect(screen.queryByTestId('approval-config-card-knowledge_file_upload')).not.toBeInTheDocument();
    expect(screen.getByTestId('approval-config-name-knowledge_file_delete')).toHaveValue('文件删除审批流');
  });

  it('adds and removes steps and members for the selected workflow', async () => {
    const user = userEvent.setup();

    render(<ApprovalConfig />);

    await screen.findByTestId('approval-config-card-knowledge_file_upload');

    await user.click(screen.getByTestId('approval-config-add-step-knowledge_file_upload'));
    expect(screen.getByTestId('approval-config-step-knowledge_file_upload-1')).toBeInTheDocument();

    await user.click(screen.getByTestId('approval-config-add-member-knowledge_file_upload-1'));
    expect(screen.getByTestId('approval-config-member-knowledge_file_upload-1-1')).toBeInTheDocument();

    const secondStep = screen.getByTestId('approval-config-step-knowledge_file_upload-1');
    const removeMemberButtons = within(secondStep).getAllByRole('button', { name: '删除成员' });
    await user.click(removeMemberButtons[1]);
    expect(screen.queryByTestId('approval-config-member-knowledge_file_upload-1-1')).not.toBeInTheDocument();

    await user.click(within(secondStep).getByRole('button', { name: '删除本层' }));
    expect(screen.queryByTestId('approval-config-step-knowledge_file_upload-1')).not.toBeInTheDocument();
  });

  it('saves workflow with mixed fixed users and direct manager members', async () => {
    const user = userEvent.setup();

    render(<ApprovalConfig />);

    await screen.findByTestId('approval-config-card-knowledge_file_upload');

    await user.click(screen.getByTestId('approval-config-add-member-knowledge_file_upload-0'));
    await user.selectOptions(
      screen.getByTestId('approval-config-member-type-knowledge_file_upload-0-1'),
      'special_role'
    );

    expect(screen.getByTestId('approval-config-member-role-knowledge_file_upload-0-1')).toHaveTextContent(
      '直属主管'
    );

    await user.click(screen.getByTestId('approval-config-save-knowledge_file_upload'));

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

  it('uses the same fuzzy user output style as training compliance for fixed members', async () => {
    const user = userEvent.setup();

    render(<ApprovalConfig />);

    await screen.findByTestId('approval-config-card-knowledge_file_upload');
    await waitFor(() => {
      expect(authClient.listUsers).toHaveBeenCalledWith({ q: 'u-1', limit: 20 });
    });

    expect(await screen.findByTestId('approval-config-member-ref-knowledge_file_upload-0-0-selected')).toHaveTextContent(
      '已选择用户: Alice (alice) / u-1'
    );

    const memberInput = screen.getByTestId('approval-config-member-ref-knowledge_file_upload-0-0-input');
    await user.clear(memberInput);
    await user.type(memberInput, 'carol');

    await waitFor(() => {
      expect(authClient.listUsers).toHaveBeenCalledWith({ q: 'carol', limit: 20 });
    });

    await user.click(await screen.findByTestId('approval-config-member-ref-knowledge_file_upload-0-0-result-u-3'));
    expect(screen.getByTestId('approval-config-member-ref-knowledge_file_upload-0-0-selected')).toHaveTextContent(
      '已选择用户: Carol (carol) / u-3'
    );

    await user.click(screen.getByTestId('approval-config-save-knowledge_file_upload'));

    await waitFor(() => {
      expect(operationApprovalApi.updateWorkflow).toHaveBeenCalledWith(
        'knowledge_file_upload',
        expect.objectContaining({
          steps: [
            {
              step_name: '第一层',
              step_no: 1,
              members: [
                {
                  member_type: 'user',
                  member_ref: 'u-3',
                },
              ],
            },
          ],
        })
      );
    });
  });

  it('shows validation error when a fixed user member is missing', async () => {
    const user = userEvent.setup();

    render(<ApprovalConfig />);

    await screen.findByTestId('approval-config-card-knowledge_file_upload');
    await screen.findByTestId('approval-config-member-ref-knowledge_file_upload-0-0-selected');

    await user.clear(screen.getByTestId('approval-config-member-ref-knowledge_file_upload-0-0-input'));
    await user.click(screen.getByTestId('approval-config-save-knowledge_file_upload'));

    expect(await screen.findByTestId('approval-config-error')).toHaveTextContent('固定用户成员必须选择用户');
    expect(operationApprovalApi.updateWorkflow).not.toHaveBeenCalled();
  });
});
