import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ApprovalCenter from './ApprovalCenter';
import documentsApi from '../features/documents/api';
import { electronicSignatureApi } from '../features/electronicSignature/api';
import operationApprovalApi from '../features/operationApproval/api';
import { useAuth } from '../hooks/useAuth';

jest.mock('react-markdown', () => ({
  __esModule: true,
  default: ({ children }) => <div>{children}</div>,
}));

jest.mock('remark-gfm', () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock('rehype-raw', () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock('rehype-sanitize', () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock('../features/electronicSignature/api', () => ({
  __esModule: true,
  electronicSignatureApi: {
    requestSignatureChallenge: jest.fn(),
  },
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

jest.mock('../features/documents/api', () => ({
  __esModule: true,
  default: {
    preview: jest.fn(),
    onlyofficeEditorConfig: jest.fn(),
    downloadBlob: jest.fn(),
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
  applicant_full_name: 'Applicant User',
  applicant_username: 'user1',
  summary: {
    filename: 'demo.txt',
    kb_id: 'ffce75402fd111f1a24e3efb393b44db',
    kb_name: 'ICE',
    kb_ref: 'ICE',
    mime_type: 'text/markdown; charset=utf-8',
  },
};

const requestDetail = {
  ...requestBrief,
  artifacts: [
    {
      artifact_id: 'artifact-1',
      artifact_type: 'knowledge_file_upload',
      file_name: 'demo.txt',
      file_path: '/tmp/demo.txt',
      mime_type: 'text/markdown; charset=utf-8',
      size_bytes: 12,
    },
  ],
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
      event_id: 'evt-hidden-1',
      event_type: 'notification_external_skipped',
      actor_user_id: 'system',
      actor_username: 'system',
      step_no: 1,
      created_at_ms: 1_710_000_000_000,
    },
    {
      event_id: 'evt-hidden-2',
      event_type: 'notification_inbox_created',
      actor_user_id: 'system',
      actor_username: 'system',
      step_no: 1,
      created_at_ms: 1_710_000_000_000,
    },
    {
      event_id: 'evt-1',
      event_type: 'request_submitted',
      actor_user_id: 'user-1',
      actor_full_name: 'Applicant User',
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
        username: 'approver-1',
        role: 'reviewer',
      },
    });
    operationApprovalApi.listRequests.mockResolvedValue([requestBrief]);
    operationApprovalApi.getRequest.mockResolvedValue(requestDetail);
    documentsApi.preview.mockResolvedValue({
      type: 'text',
      filename: 'demo.txt',
      content: 'preview content',
    });
  });

  it('submits approve action with electronic signature', async () => {
    const user = userEvent.setup();
    electronicSignatureApi.requestSignatureChallenge.mockResolvedValue({ sign_token: 'sign-token-1' });
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
      expect(electronicSignatureApi.requestSignatureChallenge).toHaveBeenCalledWith('SignPass123');
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

  it('renders full names in request detail when available', async () => {
    render(
      <MemoryRouter initialEntries={['/approvals?request_id=req-1']}>
        <ApprovalCenter />
      </MemoryRouter>
    );

    expect(await screen.findByText('申请人：Applicant User')).toBeInTheDocument();
    expect(screen.getByText(/Approver User/)).toBeInTheDocument();
    expect(screen.getByText(/操作人：Applicant User/)).toBeInTheDocument();
    expect(screen.queryByText('申请人：user1')).not.toBeInTheDocument();
    expect(screen.queryByText(/操作人：user1/)).not.toBeInTheDocument();
  });

  it('hides internal summary fields, request id, and notification-only timeline events', async () => {
    render(
      <MemoryRouter initialEntries={['/approvals?request_id=req-1']}>
        <ApprovalCenter />
      </MemoryRouter>
    );

    await screen.findByText('filename:');
    expect(screen.getAllByText('demo.txt').length).toBeGreaterThan(0);
    expect(screen.queryByText('kb_id:')).not.toBeInTheDocument();
    expect(screen.queryByText('kb_name:')).not.toBeInTheDocument();
    expect(screen.queryByText('kb_ref:')).not.toBeInTheDocument();
    expect(screen.queryByText('mime_type:')).not.toBeInTheDocument();
    expect(screen.queryByText('ffce75402fd111f1a24e3efb393b44db')).not.toBeInTheDocument();
    expect(screen.queryByText('text/markdown; charset=utf-8')).not.toBeInTheDocument();
    expect(screen.queryByText(/申请单号/)).not.toBeInTheDocument();
    expect(screen.queryByText('未配置外部通知渠道')).not.toBeInTheDocument();
    expect(screen.queryByText('站内信已生成')).not.toBeInTheDocument();
    expect(screen.queryByText(/操作人：system/)).not.toBeInTheDocument();
  });

  it('shows reject signature prompt in Chinese', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/approvals?request_id=req-1']}>
        <ApprovalCenter />
      </MemoryRouter>
    );

    await screen.findByTestId('approval-center-reject');
    await user.click(screen.getByTestId('approval-center-reject'));

    expect(screen.getByText('电子签名')).toBeInTheDocument();
    expect(screen.getByText('驳回申请单 req-1（文件上传）')).toBeInTheDocument();
    expect(screen.getByText('当前密码')).toBeInTheDocument();
    expect(screen.getByText('签名含义')).toBeInTheDocument();
    expect(screen.getByText('原因')).toBeInTheDocument();
    expect(screen.getByDisplayValue('操作审批驳回')).toBeInTheDocument();
    expect(screen.getByDisplayValue('审批后驳回该操作申请')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '签名并驳回' })).toBeInTheDocument();
  });

  it('submits reject action with electronic signature once', async () => {
    const user = userEvent.setup();
    electronicSignatureApi.requestSignatureChallenge.mockResolvedValue({ sign_token: 'sign-token-reject-1' });
    operationApprovalApi.rejectRequest.mockResolvedValue({ ...requestDetail, status: 'rejected' });

    render(
      <MemoryRouter initialEntries={['/approvals?request_id=req-1']}>
        <ApprovalCenter />
      </MemoryRouter>
    );

    await screen.findByTestId('approval-center-reject');
    await user.click(screen.getByTestId('approval-center-reject'));

    await user.type(screen.getByTestId('review-signature-password'), 'RejectPass123');
    await user.clear(screen.getByTestId('review-signature-meaning'));
    await user.type(screen.getByTestId('review-signature-meaning'), 'Reject request');
    await user.clear(screen.getByTestId('review-signature-reason'));
    await user.type(screen.getByTestId('review-signature-reason'), 'Need changes');
    await user.click(screen.getByTestId('review-signature-submit'));

    await waitFor(() => {
      expect(electronicSignatureApi.requestSignatureChallenge).toHaveBeenCalledWith('RejectPass123');
    });
    await waitFor(() => {
      expect(operationApprovalApi.rejectRequest).toHaveBeenCalledWith(
        'req-1',
        expect.objectContaining({
          sign_token: 'sign-token-reject-1',
          signature_meaning: 'Reject request',
          signature_reason: 'Need changes',
          notes: 'Need changes',
        })
      );
    });
    expect(operationApprovalApi.rejectRequest).toHaveBeenCalledTimes(1);
  });

  it('shows translated training compliance error when approval is blocked', async () => {
    const user = userEvent.setup();
    electronicSignatureApi.requestSignatureChallenge.mockResolvedValue({ sign_token: 'sign-token-training-1' });
    operationApprovalApi.approveRequest.mockRejectedValue(new Error('training_record_missing'));

    render(
      <MemoryRouter initialEntries={['/approvals?request_id=req-1']}>
        <ApprovalCenter />
      </MemoryRouter>
    );

    await screen.findByTestId('approval-center-approve');
    await user.click(screen.getByTestId('approval-center-approve'));

    await user.type(screen.getByTestId('review-signature-password'), 'SignPass123');
    await user.click(screen.getByTestId('review-signature-submit'));

    expect(await screen.findByTestId('approval-center-error')).toHaveTextContent(
      '当前审批账号缺少审批培训记录，请先补录培训记录后再审批或驳回。'
    );
    expect(screen.getByTestId('approval-center-training-help')).toHaveTextContent('当前审批账号：approver-1');
    expect(screen.getByText('请联系管理员在“培训合规管理”中为当前账号补录培训记录并授予上岗认证。')).toBeInTheDocument();
  });

  it('shows admin shortcut links to training compliance when approval is blocked by training gate', async () => {
    const user = userEvent.setup();
    useAuth.mockReturnValue({
      user: {
        user_id: 'admin-1',
        username: 'admin',
        role: 'admin',
      },
    });
    operationApprovalApi.getRequest.mockResolvedValue({
      ...requestDetail,
      steps: [
        {
          ...requestDetail.steps[0],
          approvers: [
            {
              approver_user_id: 'admin-1',
              approver_username: 'admin',
              status: 'pending',
            },
          ],
        },
      ],
    });
    electronicSignatureApi.requestSignatureChallenge.mockResolvedValue({ sign_token: 'sign-token-training-admin-1' });
    operationApprovalApi.approveRequest.mockRejectedValue(new Error('training_record_missing'));

    render(
      <MemoryRouter initialEntries={['/approvals?request_id=req-1']}>
        <ApprovalCenter />
      </MemoryRouter>
    );

    await screen.findByTestId('approval-center-approve');
    await user.click(screen.getByTestId('approval-center-approve'));
    await user.type(screen.getByTestId('review-signature-password'), 'SignPass123');
    await user.click(screen.getByTestId('review-signature-submit'));

    expect(await screen.findByTestId('approval-center-training-record-link')).toHaveAttribute(
      'href',
      '/training-compliance?tab=records&user_id=admin-1&controlled_action=document_review'
    );
    expect(screen.getByTestId('approval-center-training-certification-link')).toHaveAttribute(
      'href',
      '/training-compliance?tab=certifications&user_id=admin-1&controlled_action=document_review'
    );
  });

  it('renders different request statuses with different colors', async () => {
    useAuth.mockReturnValue({
      user: {
        user_id: 'user-1',
        role: 'reviewer',
      },
    });
    operationApprovalApi.listRequests.mockResolvedValue([
        {
          ...requestBrief,
          request_id: 'req-withdrawn',
          status: 'withdrawn',
          current_step_name: '第一层',
        },
        {
          ...requestBrief,
          request_id: 'req-approval',
          status: 'in_approval',
        },
      ]);
    operationApprovalApi.getRequest.mockResolvedValue({
      ...requestDetail,
      request_id: 'req-withdrawn',
      status: 'withdrawn',
      applicant_user_id: 'user-1',
      applicant_username: 'user1',
    });

    render(
      <MemoryRouter initialEntries={['/approvals?request_id=req-withdrawn']}>
        <ApprovalCenter />
      </MemoryRouter>
    );

    expect(await screen.findByTestId('approval-center-list-status-req-withdrawn')).toHaveStyle({ color: '#6b7280' });
    expect(screen.getByTestId('approval-center-list-status-req-approval')).toHaveStyle({ color: '#2563eb' });
    expect(await screen.findByTestId('approval-center-detail-status')).toHaveStyle({ color: '#6b7280' });
    expect(screen.getByTestId('approval-center-detail-status')).toHaveTextContent('已撤回');
  });

  it('filters requests by selected status', async () => {
    const user = userEvent.setup();
    operationApprovalApi.listRequests.mockImplementation(({ status }) => {
      if (status === 'rejected') {
        return Promise.resolve([
            {
              ...requestBrief,
              request_id: 'req-rejected',
              status: 'rejected',
              current_step_name: '第一层',
            },
          ]);
      }
      return Promise.resolve([requestBrief]);
    });
    operationApprovalApi.getRequest
      .mockResolvedValueOnce(requestDetail)
      .mockResolvedValueOnce({
        ...requestDetail,
        request_id: 'req-rejected',
        status: 'rejected',
      });

    render(
      <MemoryRouter initialEntries={['/approvals?request_id=req-1']}>
        <ApprovalCenter />
      </MemoryRouter>
    );

    await screen.findByTestId('approval-center-status-filter');
    await user.selectOptions(screen.getByTestId('approval-center-status-filter'), 'rejected');

    await waitFor(() => {
      expect(operationApprovalApi.listRequests).toHaveBeenLastCalledWith({
        view: 'todo',
        status: 'rejected',
        limit: 100,
      });
    });
    expect(await screen.findByTestId('approval-center-list-status-req-rejected')).toHaveTextContent('已驳回');
    expect(screen.queryByTestId('approval-center-list-status-req-1')).not.toBeInTheDocument();
  });

  it('hides approve and reject actions for withdrawn requests', async () => {
    operationApprovalApi.getRequest.mockResolvedValue({
      ...requestDetail,
      status: 'withdrawn',
    });

    render(
      <MemoryRouter initialEntries={['/approvals?request_id=req-1']}>
        <ApprovalCenter />
      </MemoryRouter>
    );

    await screen.findByTestId('approval-center-detail-status');
    expect(screen.queryByTestId('approval-center-approve')).not.toBeInTheDocument();
    expect(screen.queryByTestId('approval-center-reject')).not.toBeInTheDocument();
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

  it('reads the mine view from query params', async () => {
    render(
      <MemoryRouter initialEntries={['/approvals?view=mine&request_id=req-1']}>
        <ApprovalCenter />
      </MemoryRouter>
    );

    await screen.findByTestId('approval-center-tab-mine');
    expect(operationApprovalApi.listRequests).toHaveBeenCalledWith({
      view: 'mine',
      status: 'all',
      limit: 100,
    });
  });

  it('opens document preview from filename summary entry when upload artifact exists', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/approvals?request_id=req-1']}>
        <ApprovalCenter />
      </MemoryRouter>
    );

    await screen.findByTestId('approval-summary-preview-filename');
    await user.click(screen.getByTestId('approval-summary-preview-filename'));

    await waitFor(() => {
      expect(documentsApi.preview).toHaveBeenCalledWith(
        expect.objectContaining({
          source: 'operation_approval_artifact',
          docId: 'artifact-1',
          requestId: 'req-1',
        })
      );
    });
    expect(await screen.findByTestId('document-preview-modal')).toBeInTheDocument();
    expect(screen.getByText('preview content')).toBeInTheDocument();
  });
});
