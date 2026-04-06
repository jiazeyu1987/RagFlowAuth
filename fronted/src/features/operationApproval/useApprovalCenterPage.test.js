import React from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import operationApprovalApi from './api';
import useApprovalCenterPage from './useApprovalCenterPage';
import { useAuth } from '../../hooks/useAuth';
import { useSignaturePrompt } from './useSignaturePrompt';

jest.mock('./api', () => ({
  __esModule: true,
  default: {
    listRequests: jest.fn(),
    getRequest: jest.fn(),
    approveRequest: jest.fn(),
    rejectRequest: jest.fn(),
    withdrawRequest: jest.fn(),
  },
}));

jest.mock('../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('./useSignaturePrompt', () => ({
  useSignaturePrompt: jest.fn(),
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
  applicant_full_name: 'Applicant User',
  applicant_username: 'user1',
};

const requestDetail = {
  ...requestBrief,
  summary: {
    filename: 'demo.txt',
    kb_id: 'hidden-kb-id',
  },
  steps: [
    {
      request_step_id: 'step-1',
      step_no: 1,
      step_name: '第一层',
      status: 'active',
      approvers: [
        {
          approver_user_id: 'approver-1',
          approver_full_name: 'Approver User',
          approver_username: 'approver1',
          status: 'pending',
        },
      ],
    },
  ],
  events: [
    {
      event_id: 'evt-hidden',
      event_type: 'notification_external_skipped',
      created_at_ms: 1_710_000_000_000,
    },
    {
      event_id: 'evt-visible',
      event_type: 'request_submitted',
      actor_full_name: 'Applicant User',
      created_at_ms: 1_710_000_000_000,
    },
  ],
};

const signaturePromptState = {
  closeSignaturePrompt: jest.fn(),
  promptSignature: jest.fn(),
  signatureError: null,
  signaturePrompt: null,
  signatureSubmitting: false,
  submitSignaturePrompt: jest.fn(),
};

const wrapperWithEntry = (initialEntry = '/approvals?request_id=req-1') =>
  function Wrapper({ children }) {
    return <MemoryRouter initialEntries={[initialEntry]}>{children}</MemoryRouter>;
  };

describe('useApprovalCenterPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      user: {
        user_id: 'approver-1',
        username: 'approver-1',
        role: 'reviewer',
      },
    });
    useSignaturePrompt.mockReturnValue(signaturePromptState);
    operationApprovalApi.listRequests.mockResolvedValue([requestBrief]);
    operationApprovalApi.getRequest.mockResolvedValue(requestDetail);
    operationApprovalApi.withdrawRequest.mockResolvedValue({
      ...requestDetail,
      status: 'withdrawn',
    });
  });

  it('loads requests and derived approval detail state from router params', async () => {
    const { result } = renderHook(
      () =>
        useApprovalCenterPage({
          getOperationLabel: (item) => item?.operation_label || item?.operation_type || '-',
        }),
      {
        wrapper: wrapperWithEntry('/approvals?view=mine&request_id=req-1'),
      }
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    await waitFor(() => expect(result.current.detailLoading).toBe(false));

    expect(operationApprovalApi.listRequests).toHaveBeenCalledWith({
      view: 'mine',
      status: 'all',
      limit: 100,
    });
    expect(operationApprovalApi.getRequest).toHaveBeenCalledWith('req-1');
    expect(result.current.currentPendingApprover).toBe(true);
    expect(result.current.withdrawable).toBe(false);
    expect(result.current.visibleSummaryEntries).toEqual([['filename', 'demo.txt']]);
    expect(result.current.visibleEvents).toEqual([
      expect.objectContaining({
        event_id: 'evt-visible',
      }),
    ]);
    expect(result.current.trainingRecordPath).toBe(
      '/training-compliance?tab=records&user_id=approver-1&controlled_action=document_review'
    );
  });

  it('refreshes list state when the status filter changes', async () => {
    const { result } = renderHook(
      () =>
        useApprovalCenterPage({
          getOperationLabel: (item) => item?.operation_label || item?.operation_type || '-',
        }),
      {
        wrapper: wrapperWithEntry(),
      }
    );

    await waitFor(() => expect(result.current.loading).toBe(false));

    operationApprovalApi.listRequests.mockResolvedValueOnce([
      { ...requestBrief, request_id: 'req-rejected', status: 'rejected' },
    ]);
    operationApprovalApi.getRequest.mockResolvedValueOnce({
      ...requestDetail,
      request_id: 'req-rejected',
      status: 'rejected',
    });

    await act(async () => {
      result.current.handleChangeStatus('rejected');
    });

    await waitFor(() => {
      expect(operationApprovalApi.listRequests).toHaveBeenLastCalledWith({
        view: 'todo',
        status: 'rejected',
        limit: 100,
      });
    });
  });

  it('withdraws requests through the feature api for the applicant user', async () => {
    const promptSpy = jest.spyOn(window, 'prompt').mockReturnValue('撤回原因');

    useAuth.mockReturnValue({
      user: {
        user_id: 'user-1',
        username: 'user1',
        role: 'reviewer',
      },
    });

    const { result } = renderHook(
      () =>
        useApprovalCenterPage({
          getOperationLabel: (item) => item?.operation_label || item?.operation_type || '-',
        }),
      {
        wrapper: wrapperWithEntry(),
      }
    );

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.handleWithdraw();
    });

    expect(operationApprovalApi.withdrawRequest).toHaveBeenCalledWith('req-1', {
      reason: '撤回原因',
    });

    promptSpy.mockRestore();
  });
});
