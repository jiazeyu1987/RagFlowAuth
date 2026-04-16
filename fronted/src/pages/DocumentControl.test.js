import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DocumentControl from './DocumentControl';
import documentControlApi from '../features/documentControl/api';
import operationApprovalApi from '../features/operationApproval/api';
import qualitySystemConfigApi from '../features/qualitySystemConfig/api';
import { useAuth } from '../hooks/useAuth';

jest.mock('../features/documentControl/api', () => ({
  __esModule: true,
  default: {
    listDocuments: jest.fn(),
    getDocument: jest.fn(),
    createDocument: jest.fn(),
    createRevision: jest.fn(),
    previewRevisionApprovalMatrix: jest.fn(),
    submitRevisionForApproval: jest.fn(),
    approveRevisionStep: jest.fn(),
    rejectRevisionStep: jest.fn(),
    addSignRevisionStep: jest.fn(),
    getDistributionDepartments: jest.fn(),
    setDistributionDepartments: jest.fn(),
    publishRevision: jest.fn(),
    listRevisionDepartmentAcks: jest.fn(),
    confirmRevisionDepartmentAck: jest.fn(),
    remindOverdueRevisionDepartmentAcks: jest.fn(),
    initiateObsoleteRevision: jest.fn(),
    approveObsoleteRevision: jest.fn(),
    confirmRevisionDestruction: jest.fn(),
    listRetiredDocuments: jest.fn(),
  },
}));

jest.mock('../features/qualitySystemConfig/api', () => ({
  __esModule: true,
  default: {
    getConfig: jest.fn(),
  },
}));

jest.mock('../features/operationApproval/api', () => ({
  __esModule: true,
  default: {
    getRequest: jest.fn(),
  },
}));

jest.mock('../features/trainingCompliance/api', () => ({
  __esModule: true,
  default: {
    getRevisionGate: jest.fn(),
    upsertRevisionGate: jest.fn(),
    listAssignments: jest.fn(),
    generateAssignments: jest.fn(),
  },
}));

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

const listResponse = [
  {
    controlled_document_id: 'doc-1',
    doc_code: 'DOC-001',
    title: 'Controlled URS',
    current_revision: {
      controlled_revision_id: 'rev-1',
      revision_no: 1,
      status: 'draft',
      filename: 'urs.md',
    },
  },
];

const detailResponse = {
  controlled_document_id: 'doc-1',
  doc_code: 'DOC-001',
  title: 'Controlled URS',
  document_type: 'urs',
  file_subtype: '设计验证方案/报告',
  product_name: 'Product A',
  registration_ref: 'REG-001',
  target_kb_id: 'kb-quality',
  target_kb_name: 'Quality KB',
  current_revision: {
    controlled_revision_id: 'rev-1',
    revision_no: 1,
    status: 'draft',
    filename: 'urs.md',
    file_subtype: '设计验证方案/报告',
    matrix_snapshot: { file_subtype: '设计验证方案/报告' },
    position_snapshot: { QA: [{ user_id: 'u-2' }] },
  },
  effective_revision: null,
  revisions: [
    {
      controlled_revision_id: 'rev-1',
      revision_no: 1,
      status: 'draft',
      filename: 'urs.md',
      file_path: '/tmp/urs.md',
      change_summary: 'initial baseline',
    },
  ],
};

describe('DocumentControl page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const isAuthorized = jest.fn((options = {}) => {
      const resource = options?.permission?.resource;
      if (resource === 'document_control') {
        return true;
      }
      const anyPermissions = Array.isArray(options?.anyPermissions) ? options.anyPermissions : [];
      if (anyPermissions.some((item) => item?.resource === 'document_control')) {
        return true;
      }
      return false;
    });
    useAuth.mockReturnValue({
      loading: false,
      user: { user_id: 'u-1', role: 'admin' },
      isAuthorized,
    });

    operationApprovalApi.getRequest.mockResolvedValue({
      request_id: 'req-1',
      status: 'in_approval',
      current_step_name: 'cosign',
      current_step_no: 1,
      workflow_snapshot: {
        steps: [
          {
            step_no: 1,
            step_semantic: 'signoff',
            position_name: 'QA',
            members: [{ user_id: 'u-2', full_name: 'Bob Reviewer' }],
          },
        ],
      },
      steps: [
        {
          request_step_id: 'step-1',
          step_no: 1,
          step_name: 'cosign',
          status: 'active',
          approvers: [
            {
              approver_user_id: 'u-2',
              approver_username: 'bob',
              approver_full_name: 'Bob Reviewer',
              status: 'pending',
            },
          ],
        },
      ],
      events: [],
    });
    qualitySystemConfigApi.getConfig.mockResolvedValue({
      file_categories: [
        { id: 1, name: '设计验证方案/报告' },
        { id: 2, name: '工艺流程图' },
      ],
    });
    const trainingComplianceApi = require('../features/trainingCompliance/api').default;
    trainingComplianceApi.getRevisionGate.mockResolvedValue({
      controlled_revision_id: 'rev-1',
      training_required: false,
      configured: false,
      department_ids: [],
      gate_status: 'not_required',
      blocking: false,
    });
    trainingComplianceApi.upsertRevisionGate.mockResolvedValue({
      controlled_revision_id: 'rev-1',
      training_required: true,
      configured: true,
      department_ids: [10],
      gate_status: 'pending_assignment',
      blocking: true,
    });
    trainingComplianceApi.listAssignments.mockResolvedValue([]);
    trainingComplianceApi.generateAssignments.mockResolvedValue([]);

    documentControlApi.listDocuments.mockResolvedValue(listResponse);
    documentControlApi.getDocument.mockResolvedValue(detailResponse);
    documentControlApi.getDistributionDepartments.mockResolvedValue([]);
    documentControlApi.setDistributionDepartments.mockResolvedValue([]);
    documentControlApi.publishRevision.mockResolvedValue(detailResponse);
    documentControlApi.listRevisionDepartmentAcks.mockResolvedValue([]);
    documentControlApi.confirmRevisionDepartmentAck.mockResolvedValue({ ack_id: 'ack-1', status: 'confirmed' });
    documentControlApi.remindOverdueRevisionDepartmentAcks.mockResolvedValue({ reminded_count: 1 });
    documentControlApi.initiateObsoleteRevision.mockResolvedValue(detailResponse);
    documentControlApi.approveObsoleteRevision.mockResolvedValue(detailResponse);
    documentControlApi.confirmRevisionDestruction.mockResolvedValue(detailResponse);
    documentControlApi.previewRevisionApprovalMatrix.mockResolvedValue({
      file_subtype: '设计验证方案/报告',
      compiler_check: { position_name: '项目负责人' },
      signoff_steps: [{ position_name: 'QA', approvers: [{ user_id: 'u-2', full_name: 'Bob Reviewer' }] }],
      approval_steps: [{ position_name: '编制部门负责人或授权代表', approvers: [{ user_id: 'u-3', full_name: 'Alice Approver' }] }],
    });
    documentControlApi.createDocument.mockResolvedValue({
      ...detailResponse,
      controlled_document_id: 'doc-2',
      doc_code: 'DOC-002',
      title: 'Controlled SRS',
    });
    documentControlApi.createRevision.mockResolvedValue({
      ...detailResponse,
      current_revision: {
        controlled_revision_id: 'rev-2',
        revision_no: 2,
        status: 'draft',
        filename: 'urs-v2.md',
        file_subtype: '设计验证方案/报告',
      },
      revisions: [
        {
          controlled_revision_id: 'rev-2',
          revision_no: 2,
          status: 'draft',
          filename: 'urs-v2.md',
          file_path: '/tmp/urs-v2.md',
          change_summary: 'rev 2',
        },
        detailResponse.revisions[0],
      ],
    });
    documentControlApi.submitRevisionForApproval.mockResolvedValue({
      ...detailResponse,
      current_revision: {
        controlled_revision_id: 'rev-2',
        revision_no: 2,
        status: 'approval_in_progress',
        filename: 'urs-v2.md',
        file_subtype: '设计验证方案/报告',
        approval_request_id: 'req-2',
        approval_round: 1,
        current_approval_step_name: 'cosign',
        current_approval_step_no: 1,
      },
      revisions: [
        {
          ...detailResponse.revisions[0],
          controlled_revision_id: 'rev-2',
          revision_no: 2,
          filename: 'urs-v2.md',
          status: 'approval_in_progress',
        },
        detailResponse.revisions[0],
      ],
    });
  });

  it('loads list and detail content for controlled documents', async () => {
    render(<DocumentControl />);

    expect(await screen.findByTestId('document-control-page')).toBeInTheDocument();
    expect(await screen.findByText('Controlled URS')).toBeInTheDocument();
    expect(await screen.findByTestId('document-control-detail-doc-code')).toHaveTextContent(
      'DOC-001'
    );
    expect(await screen.findByTestId('document-control-matrix-preview-compiler')).toHaveTextContent(
      '项目负责人'
    );
  });

  it('supports search, document creation, revision creation, and approval submit actions', async () => {
    const user = userEvent.setup();
    render(<DocumentControl />);

    await screen.findByTestId('document-control-page');
    expect(screen.queryByText(/Move to/i)).not.toBeInTheDocument();

    await user.type(screen.getByTestId('document-control-filter-query'), 'URS');
    await user.click(screen.getByTestId('document-control-search'));
    await waitFor(() =>
      expect(documentControlApi.listDocuments).toHaveBeenLastCalledWith(
        expect.objectContaining({ query: 'URS', limit: 100 })
      )
    );

    await user.type(screen.getByTestId('document-control-create-doc-code'), 'DOC-002');
    await user.type(screen.getByTestId('document-control-create-title'), 'Controlled SRS');
    await user.type(screen.getByTestId('document-control-create-document-type'), 'srs');
    await user.selectOptions(screen.getByTestId('document-control-create-file-subtype'), '设计验证方案/报告');
    await user.type(screen.getByTestId('document-control-create-target-kb'), 'Quality KB');
    await user.type(screen.getByTestId('document-control-create-product-name'), 'Product B');
    await user.upload(
      screen.getByTestId('document-control-create-file'),
      new File(['hello'], 'srs.pdf', { type: 'application/pdf' })
    );
    await user.click(screen.getByTestId('document-control-create-submit'));

    await waitFor(() => expect(documentControlApi.createDocument).toHaveBeenCalled());
    expect(await screen.findByTestId('document-control-success')).toHaveTextContent(
      'Controlled document created'
    );

    await user.upload(
      screen.getByTestId('document-control-revision-file'),
      new File(['rev2'], 'urs-v2.pdf', { type: 'application/pdf' })
    );
    await user.click(screen.getByTestId('document-control-revision-submit'));

    await waitFor(() => expect(documentControlApi.createRevision).toHaveBeenCalled());
    expect(await screen.findByTestId('document-control-success')).toHaveTextContent('Revision created');

    await user.click(screen.getByTestId('document-control-approval-submit'));
    await waitFor(() =>
      expect(documentControlApi.submitRevisionForApproval).toHaveBeenCalledWith('rev-2', { note: null })
    );

    await waitFor(() => expect(operationApprovalApi.getRequest).toHaveBeenCalledWith('req-2'));
    expect(await screen.findByTestId('document-control-approval-pending-approvers')).toHaveTextContent(
      'Bob Reviewer'
    );
    expect(await screen.findByTestId('document-control-approval-step-semantic')).toHaveTextContent(
      'signoff'
    );
    expect(await screen.findByTestId('document-control-approval-step-position')).toHaveTextContent(
      'QA'
    );
    expect(await screen.findByTestId('document-control-approval-step-approvers')).toHaveTextContent(
      'Bob Reviewer'
    );
  });

  it('requires product name before creating a document', async () => {
    const user = userEvent.setup();
    render(<DocumentControl />);

    await screen.findByTestId('document-control-page');

    await user.type(screen.getByTestId('document-control-create-doc-code'), 'DOC-003');
    await user.type(screen.getByTestId('document-control-create-title'), 'Controlled WI');
    await user.type(screen.getByTestId('document-control-create-document-type'), 'wi');
    await user.type(screen.getByTestId('document-control-create-target-kb'), 'Quality KB');
    await user.upload(
      screen.getByTestId('document-control-create-file'),
      new File(['hello'], 'wi.pdf', { type: 'application/pdf' })
    );
    await user.click(screen.getByTestId('document-control-create-submit'));

    expect(documentControlApi.createDocument).not.toHaveBeenCalled();
    expect(await screen.findByTestId('document-control-error')).toHaveTextContent(
      'Please provide the product name.'
    );
  });

  it('requires file subtype before creating a document', async () => {
    const user = userEvent.setup();
    render(<DocumentControl />);

    await screen.findByTestId('document-control-page');

    await user.type(screen.getByTestId('document-control-create-doc-code'), 'DOC-004');
    await user.type(screen.getByTestId('document-control-create-title'), 'Controlled Matrix Doc');
    await user.type(screen.getByTestId('document-control-create-document-type'), 'urs');
    await user.type(screen.getByTestId('document-control-create-target-kb'), 'Quality KB');
    await user.type(screen.getByTestId('document-control-create-product-name'), 'Product A');
    await user.type(screen.getByTestId('document-control-create-registration-ref'), 'REG-003');
    await user.upload(
      screen.getByTestId('document-control-create-file'),
      new File(['hello'], 'matrix.pdf', { type: 'application/pdf' })
    );
    await user.click(screen.getByTestId('document-control-create-submit'));

    expect(documentControlApi.createDocument).not.toHaveBeenCalled();
    expect(await screen.findByTestId('document-control-error')).toHaveTextContent(
      'Please select a file subtype.'
    );
  });
});
