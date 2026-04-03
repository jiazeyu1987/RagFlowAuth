import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ApprovalConfig from './ApprovalConfig';
import operationApprovalApi from '../features/operationApproval/api';
import { usersApi } from '../features/users/api';

jest.mock('../features/operationApproval/api', () => ({
  __esModule: true,
  default: {
    listWorkflows: jest.fn(),
    updateWorkflow: jest.fn(),
  },
}));

jest.mock('../features/users/api', () => ({
  usersApi: {
    list: jest.fn(),
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
          approver_user_ids: ['u-1'],
        },
      ],
    },
  ],
};

const activeUsers = [
  { user_id: 'u-1', username: 'alice', full_name: 'Alice' },
  { user_id: 'u-2', username: 'bob', full_name: 'Bob' },
];

describe('ApprovalConfig', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    operationApprovalApi.listWorkflows.mockResolvedValue(workflowResponse);
    operationApprovalApi.updateWorkflow.mockResolvedValue({});
    usersApi.list.mockResolvedValue(activeUsers);
  });

  it('adds a step and saves workflow with selected approvers', async () => {
    const user = userEvent.setup();

    render(<ApprovalConfig />);

    await screen.findByTestId('approval-config-card-knowledge_file_upload');

    await user.click(screen.getByTestId('approval-config-add-step-knowledge_file_upload'));

    const secondStepName = screen.getByTestId('approval-config-step-name-knowledge_file_upload-1');
    await user.clear(secondStepName);
    await user.type(secondStepName, '第二层');

    const secondApprovers = screen.getByTestId('approval-config-step-approvers-knowledge_file_upload-1');
    await user.selectOptions(secondApprovers, ['u-2']);

    await user.click(screen.getByTestId('approval-config-save-knowledge_file_upload'));

    await waitFor(() => {
      expect(operationApprovalApi.updateWorkflow).toHaveBeenCalledWith(
        'knowledge_file_upload',
        expect.objectContaining({
          steps: [
            expect.objectContaining({ step_name: '第一层', approver_user_ids: ['u-1'] }),
            expect.objectContaining({ step_name: '第二层', approver_user_ids: ['u-2'] }),
          ],
        })
      );
    });
  });

  it('shows validation error when a step has no approver', async () => {
    const user = userEvent.setup();

    render(<ApprovalConfig />);

    await screen.findByTestId('approval-config-card-knowledge_file_upload');

    const firstApprovers = screen.getByTestId('approval-config-step-approvers-knowledge_file_upload-0');
    await user.deselectOptions(firstApprovers, ['u-1']);
    await user.click(screen.getByTestId('approval-config-save-knowledge_file_upload'));

    expect(await screen.findByTestId('approval-config-error')).toHaveTextContent('每一层至少选择一位审批人');
    expect(operationApprovalApi.updateWorkflow).not.toHaveBeenCalled();
  });
});
