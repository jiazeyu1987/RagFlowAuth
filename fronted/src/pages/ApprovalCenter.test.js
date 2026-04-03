import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ApprovalCenter from './ApprovalCenter';
import authClient from '../api/authClient';
import operationApprovalApi from '../features/operationApproval/api';
import { useAuth } from '../hooks/useAuth';

jest.mock('../api/authClient', () => ({
  requestSignatureChallenge: jest.fn(),
}));

jest.mock('../features/operationApproval/api', () => ({
  __esModule: true,
  default: {
    listRequests: jest.fn(),
    getRequest: jest.fn(),
    approveRequest: jest.fn(),
    rejectRequest: jest.fn(),
    withdrawRequest: jest.fn(),
  },
}));

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

const requestBrief = {
  request_id: 'req-1',
  operation_type: 'knowledge_file_upload',
  operation_label: '文件上传',
  status: 'in_approval',
  current_step_no: 1,
  current_step_name: '第一层',
  submitted_at_ms: 1_710_000_000_000,
  target_ref: 'kb-a',
  target_label: 'demo.txt',
  applicant_user_id: 'user-1',
  applicant_username: 'user1',
  summary: { filename: 'demo.txt' },
};

const requestDetail = {
  ...requestBrief,
  steps: [
    {
      request_step_id: 'step-1',
      step_no: 1,
      step_name: '第一层',
      status: 'active',
      approvers: [
        {
          approver_user_id: 'approver-1',
          approver_username: 'approver1',
          status: 'pending',
        },
      ],
    },
  ],
  events: [
    {
      event_id: 'evt-1',
      event_type: 'request_submitted',
      actor_user_id: 'user-1',
      actor_username: 'user1',
      step_no: 1,
      created_at_ms: 1_710_000_000_000,
    },
  ],
};

describe('ApprovalCenter', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      user: {
        user_id: 'approver-1',
        role: 'reviewer',
      },
    });
    operationApprovalApi.listRequests.mockResolvedValue({ items: [requestBrief] });
    operationApprovalApi.getRequest.mockResolvedValue(requestDetail);
  });

  it('submits approve action with electronic signature', async () => {
    const user = userEvent.setup();
    authClient.requestSignatureChallenge.mockResolvedValue({ sign_token: 'sign-token-1' });
    operationApprovalApi.approveRequest.mockResolvedValue({ ...requestDetail, status: 'executed' });

    render(
      <MemoryRouter initialEntries={['/approvals?request_id=req-1']}>
        <ApprovalCenter />
      </MemoryRouter>
    );

    await screen.findByTestId('approval-center-approve');
    await user.click(screen.getByTestId('approval-center-approve'));

    await user.type(screen.getByTestId('review-signature-password'), 'SignPass123');
    await user.clear(screen.getByTestId('review-signature-meaning'));
    await user.type(screen.getByTestId('review-signature-meaning'), 'Approve request');
    await user.clear(screen.getByTestId('review-signature-reason'));
    await user.type(screen.getByTestId('review-signature-reason'), 'Looks good');
    await user.click(screen.getByTestId('review-signature-submit'));

    await waitFor(() => {
      expect(authClient.requestSignatureChallenge).toHaveBeenCalledWith('SignPass123');
    });
    await waitFor(() => {
      expect(operationApprovalApi.approveRequest).toHaveBeenCalledWith(
        'req-1',
        expect.objectContaining({
          sign_token: 'sign-token-1',
          signature_meaning: 'Approve request',
          signature_reason: 'Looks good',
          notes: 'Looks good',
        })
      );
    });
  });

  it('allows applicant to withdraw request', async () => {
    const user = userEvent.setup();
    useAuth.mockReturnValue({
      user: {
        user_id: 'user-1',
        role: 'reviewer',
      },
    });
    operationApprovalApi.withdrawRequest.mockResolvedValue({ ...requestDetail, status: 'withdrawn' });
    const promptSpy = jest.spyOn(window, 'prompt').mockReturnValue('撤回原因');

    render(
      <MemoryRouter initialEntries={['/approvals?request_id=req-1']}>
        <ApprovalCenter />
      </MemoryRouter>
    );

    await screen.findByTestId('approval-center-withdraw');
    await user.click(screen.getByTestId('approval-center-withdraw'));

    await waitFor(() => {
      expect(operationApprovalApi.withdrawRequest).toHaveBeenCalledWith('req-1', { reason: '撤回原因' });
    });

    promptSpy.mockRestore();
  });
});
