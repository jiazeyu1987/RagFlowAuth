import { act, renderHook, waitFor } from '@testing-library/react';
import useDocumentControlPage from './useDocumentControlPage';
import documentControlApi from './api';
import operationApprovalApi from '../operationApproval/api';
import trainingComplianceApi from '../trainingCompliance/api';

jest.mock('./api', () => ({
  __esModule: true,
  default: {
    listDocuments: jest.fn(),
    getDocument: jest.fn(),
    createDocument: jest.fn(),
    createRevision: jest.fn(),
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

jest.mock('../operationApproval/api', () => ({
  __esModule: true,
  default: {
    getRequest: jest.fn(),
  },
}));

jest.mock('../trainingCompliance/api', () => ({
  __esModule: true,
  default: {
    getRevisionGate: jest.fn(),
    upsertRevisionGate: jest.fn(),
    listAssignments: jest.fn(),
    generateAssignments: jest.fn(),
  },
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
  target_kb_id: 'kb-quality',
  target_kb_name: 'Quality KB',
  current_revision: {
    controlled_revision_id: 'rev-1',
    revision_no: 1,
    status: 'draft',
    filename: 'urs.md',
  },
  effective_revision: null,
  revisions: [
    {
      controlled_revision_id: 'rev-1',
      revision_no: 1,
      status: 'draft',
      filename: 'urs.md',
      file_path: '/tmp/urs.md',
    },
  ],
};

describe('useDocumentControlPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    operationApprovalApi.getRequest.mockResolvedValue({
      request_id: 'req-1',
      status: 'in_approval',
      current_step_name: 'cosign',
      current_step_no: 1,
      steps: [],
      events: [],
    });
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
    documentControlApi.getDistributionDepartments.mockResolvedValue([]);
    documentControlApi.setDistributionDepartments.mockResolvedValue([]);
    documentControlApi.publishRevision.mockResolvedValue(detailResponse);
    documentControlApi.listRevisionDepartmentAcks.mockResolvedValue([]);
    documentControlApi.confirmRevisionDepartmentAck.mockResolvedValue({ ack_id: 'ack-1', status: 'confirmed' });
    documentControlApi.remindOverdueRevisionDepartmentAcks.mockResolvedValue({ reminded_count: 1 });
    documentControlApi.initiateObsoleteRevision.mockResolvedValue(detailResponse);
    documentControlApi.approveObsoleteRevision.mockResolvedValue(detailResponse);
    documentControlApi.confirmRevisionDestruction.mockResolvedValue(detailResponse);
    documentControlApi.listRetiredDocuments.mockResolvedValue([]);
    documentControlApi.listDocuments.mockResolvedValue(listResponse);
    documentControlApi.getDocument.mockResolvedValue(detailResponse);
    documentControlApi.createDocument.mockResolvedValue({
      ...detailResponse,
      controlled_document_id: 'doc-2',
      doc_code: 'DOC-002',
    });
    documentControlApi.createRevision.mockResolvedValue({
      ...detailResponse,
      current_revision: {
        controlled_revision_id: 'rev-2',
        revision_no: 2,
        status: 'draft',
        filename: 'urs-v2.md',
      },
      revisions: [
        {
          controlled_revision_id: 'rev-2',
          revision_no: 2,
          status: 'draft',
          filename: 'urs-v2.md',
          file_path: '/tmp/urs-v2.md',
        },
        {
          controlled_revision_id: 'rev-1',
          revision_no: 1,
          status: 'effective',
          filename: 'urs.md',
          file_path: '/tmp/urs.md',
        },
      ],
    });
    documentControlApi.submitRevisionForApproval.mockResolvedValue({
      ...detailResponse,
      current_revision: {
        controlled_revision_id: 'rev-1',
        revision_no: 1,
        status: 'approval_in_progress',
        filename: 'urs.md',
        approval_request_id: 'req-1',
        approval_round: 1,
        current_approval_step_name: 'cosign',
        current_approval_step_no: 1,
      },
      revisions: [
        {
          ...detailResponse.revisions[0],
          status: 'approval_in_progress',
        },
      ],
    });
    documentControlApi.approveRevisionStep.mockResolvedValue({
      ...detailResponse,
      current_revision: {
        controlled_revision_id: 'rev-1',
        revision_no: 1,
        status: 'approved_pending_effective',
        filename: 'urs.md',
        approval_request_id: null,
        approval_round: 1,
        current_approval_step_name: null,
        current_approval_step_no: null,
      },
      revisions: [
        {
          ...detailResponse.revisions[0],
          status: 'approved_pending_effective',
        },
      ],
    });
    documentControlApi.rejectRevisionStep.mockResolvedValue({
      ...detailResponse,
      current_revision: {
        controlled_revision_id: 'rev-1',
        revision_no: 1,
        status: 'approval_rejected',
        filename: 'urs.md',
        approval_request_id: null,
        approval_round: 1,
      },
      revisions: [
        {
          ...detailResponse.revisions[0],
          status: 'approval_rejected',
        },
      ],
    });
    documentControlApi.addSignRevisionStep.mockResolvedValue({
      ...detailResponse,
      current_revision: {
        ...detailResponse.current_revision,
        status: 'approval_in_progress',
        approval_request_id: 'req-1',
        approval_round: 1,
        current_approval_step_name: 'cosign',
        current_approval_step_no: 1,
      },
    });
  });

  it('loads list and detail state, then reloads with search filters', async () => {
    const { result } = renderHook(() => useDocumentControlPage());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.documents).toHaveLength(1);
    expect(result.current.selectedDocument?.controlled_document_id).toBe('doc-1');
    expect(documentControlApi.listDocuments).toHaveBeenCalledWith({
      limit: 100,
      query: '',
      docCode: '',
      title: '',
      documentType: '',
      productName: '',
      registrationRef: '',
      status: '',
    });
    expect(documentControlApi.getDocument).toHaveBeenCalledWith('doc-1');

    act(() => {
      result.current.handleFilterChange('query', 'URS');
    });

    await act(async () => {
      await result.current.handleSearch();
    });

    expect(documentControlApi.listDocuments).toHaveBeenLastCalledWith({
      limit: 100,
      query: 'URS',
      docCode: '',
      title: '',
      documentType: '',
      productName: '',
      registrationRef: '',
      status: '',
    });
  });

  it('fails fast on missing files and updates state after create and workflow actions', async () => {
    const { result } = renderHook(() => useDocumentControlPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.handleCreateDocument();
    });
    expect(result.current.error).toBe('product_name_required');

    act(() => {
      result.current.setDocumentForm((previous) => ({
        ...previous,
        doc_code: 'DOC-002',
        title: 'Controlled SRS',
        document_type: 'srs',
        target_kb_id: 'Quality KB',
        product_name: 'Product B',
        registration_ref: 'REG-002',
        file: new File(['hello'], 'srs.md', { type: 'text/markdown' }),
      }));
    });

    await act(async () => {
      await result.current.handleCreateDocument();
    });
    expect(documentControlApi.createDocument).toHaveBeenCalled();
    expect(result.current.success).toBe('Controlled document created');

    act(() => {
      result.current.setRevisionForm((previous) => ({
        ...previous,
        change_summary: 'rev 2',
        file: new File(['hello'], 'srs-v2.md', { type: 'text/markdown' }),
      }));
    });

    await act(async () => {
      await result.current.handleCreateRevision();
    });
    expect(documentControlApi.createRevision).toHaveBeenCalled();
    expect(result.current.success).toBe('Revision created');

    await act(async () => {
      await result.current.handleSubmitRevisionForApproval('rev-1');
    });
    expect(documentControlApi.submitRevisionForApproval).toHaveBeenCalledWith('rev-1', { note: null });
    expect(result.current.success).toBe('Revision submitted for approval');

    await act(async () => {
      await result.current.handleApproveRevisionStep('rev-1');
    });
    expect(documentControlApi.approveRevisionStep).toHaveBeenCalledWith('rev-1', { note: null });
    expect(result.current.success).toBe('Approval recorded');

    await act(async () => {
      await result.current.handleRejectRevisionStep('rev-1');
    });
    expect(documentControlApi.rejectRevisionStep).toHaveBeenCalledWith('rev-1', { note: null });
    expect(result.current.success).toBe('Rejection recorded');

    await act(async () => {
      await result.current.handleAddSignRevisionStep('rev-1', {});
    });
    expect(documentControlApi.addSignRevisionStep).not.toHaveBeenCalled();
    expect(result.current.error).toBe('approver_user_id_required');

    await act(async () => {
      await result.current.handleAddSignRevisionStep('rev-1', { approverUserId: 'user-2' });
    });
    expect(documentControlApi.addSignRevisionStep).toHaveBeenCalledWith('rev-1', {
      approver_user_id: 'user-2',
      note: null,
    });
    expect(result.current.success).toBe('Additional approver added');

    await act(async () => {
      await result.current.handleGenerateTrainingAssignments('rev-1', { assigneeUserIds: [] });
    });
    expect(trainingComplianceApi.generateAssignments).not.toHaveBeenCalled();
    expect(result.current.error).toBe('training_assignment_assignees_required');

    trainingComplianceApi.generateAssignments.mockResolvedValueOnce([
      { assignment_id: 'a-1', controlled_revision_id: 'rev-1', status: 'pending' },
    ]);
    await act(async () => {
      await result.current.handleGenerateTrainingAssignments('rev-1', {
        assigneeUserIds: ['u-2'],
        departmentIds: [10],
        minReadMinutes: 15,
      });
    });
    expect(trainingComplianceApi.generateAssignments).toHaveBeenCalledWith({
      controlled_revision_id: 'rev-1',
      assignee_user_ids: ['u-2'],
      department_ids: [10],
      min_read_minutes: 15,
      note: null,
    });
    expect(result.current.success).toBe('Training assignments generated (1)');
    expect(result.current.generatedTrainingAssignments).toHaveLength(1);

    await act(async () => {
      await result.current.handleSetTrainingGate('rev-1', {
        trainingRequired: true,
        departmentIds: [10],
      });
    });
    expect(trainingComplianceApi.upsertRevisionGate).toHaveBeenCalledWith('rev-1', {
      training_required: true,
      department_ids: [10],
    });
    expect(result.current.success).toBe('Training gate saved');
  });

  it('derives workflow workspace state for training, department acks, and retention', async () => {
    documentControlApi.getDocument.mockResolvedValueOnce({
      ...detailResponse,
      current_revision: {
        ...detailResponse.current_revision,
        controlled_revision_id: 'rev-obsolete-1',
        status: 'obsolete',
        kb_doc_id: 'kb-doc-1',
      },
    });
    trainingComplianceApi.listAssignments.mockResolvedValueOnce([
      {
        assignment_id: 'a-1',
        controlled_revision_id: 'rev-obsolete-1',
        status: 'pending',
        required_read_ms: 60000,
        read_progress_ms: 0,
      },
      { assignment_id: 'a-2', controlled_revision_id: 'rev-other', status: 'acknowledged' },
    ]);
    documentControlApi.getDistributionDepartments.mockResolvedValueOnce([10]);
    documentControlApi.listRevisionDepartmentAcks.mockResolvedValueOnce([
      {
        ack_id: 'ack-1',
        department_id: 10,
        status: 'pending',
        due_at_ms: 999,
      },
    ]);
    documentControlApi.listRetiredDocuments.mockResolvedValueOnce([
      { doc_id: 'kb-doc-1', filename: 'urs.md', retention_until_ms: 123, retirement_reason: 'superseded' },
    ]);

    const { result } = renderHook(() => useDocumentControlPage());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await waitFor(() => expect(result.current.trainingAssignments).toHaveLength(1));
    expect(result.current.trainingAssignments[0].assignment_id).toBe('a-1');

    await waitFor(() => expect(result.current.departmentAcks).toHaveLength(1));
    expect(result.current.departmentAcks[0].ack_id).toBe('ack-1');
    expect(result.current.distributionDepartmentIds).toEqual([10]);

    await waitFor(() => expect(result.current.retentionRecord?.doc_id).toBe('kb-doc-1'));
  });
});
