import documentControlApi from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('documentControlApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('normalizes list and document envelopes for all document-control endpoints', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ items: [{ controlled_document_id: 'doc-1' }] })
      .mockResolvedValueOnce({ document: { controlled_document_id: 'doc-1', title: 'URS' } })
      .mockResolvedValueOnce({ document: { controlled_document_id: 'doc-2' } })
      .mockResolvedValueOnce({ document: { controlled_document_id: 'doc-1', current_revision_id: 'rev-2' } })
      .mockResolvedValueOnce({ document: { controlled_document_id: 'doc-1', approval_request_id: 'req-1' } })
      .mockResolvedValueOnce({ document: { controlled_document_id: 'doc-1', approval_step: 'cosign' } })
      .mockResolvedValueOnce({ document: { controlled_document_id: 'doc-1', approval_step: 'approve' } })
      .mockResolvedValueOnce({ document: { controlled_document_id: 'doc-1', approval_step: 'standardize_review' } })
      .mockResolvedValueOnce({ department_ids: [10, 20] })
      .mockResolvedValueOnce({ department_ids: [10, 20] })
      .mockResolvedValueOnce({ document: { controlled_document_id: 'doc-1', effective_revision_id: 'rev-2' } })
      .mockResolvedValueOnce({ items: [{ ack_id: 'ack-1' }], count: 1 })
      .mockResolvedValueOnce({ ack: { ack_id: 'ack-1', status: 'confirmed' } })
      .mockResolvedValueOnce({ result: { reminded_count: 1 } })
      .mockResolvedValueOnce({ document: { controlled_document_id: 'doc-1', current_revision_id: 'rev-2' } })
      .mockResolvedValueOnce({ document: { controlled_document_id: 'doc-1', current_revision_id: 'rev-2' } })
      .mockResolvedValueOnce({ document: { controlled_document_id: 'doc-1', current_revision_id: 'rev-2' } })
      .mockResolvedValueOnce({ items: [{ doc_id: 'kb-doc-1' }], count: 1 });

    await expect(
      documentControlApi.listDocuments({
        limit: 20,
        docCode: 'DOC-1',
        title: 'URS',
        documentType: 'urs',
        productName: 'Product A',
        registrationRef: 'REG-001',
        status: 'draft',
        query: 'validation',
      })
    ).resolves.toEqual([{ controlled_document_id: 'doc-1' }]);

    await expect(documentControlApi.getDocument('doc-1')).resolves.toEqual({
      controlled_document_id: 'doc-1',
      title: 'URS',
    });

    const createPayload = {
      doc_code: 'DOC-002',
      title: 'SRS',
      document_type: 'srs',
      target_kb_id: 'Quality KB',
      file: new File(['hello'], 'srs.md', { type: 'text/markdown' }),
    };
    await expect(documentControlApi.createDocument(createPayload)).resolves.toEqual({
      controlled_document_id: 'doc-2',
    });

    const revisionPayload = {
      change_summary: 'rev 2',
      file: new File(['rev2'], 'srs-v2.md', { type: 'text/markdown' }),
    };
    await expect(documentControlApi.createRevision('doc-1', revisionPayload)).resolves.toEqual({
      controlled_document_id: 'doc-1',
      current_revision_id: 'rev-2',
    });

    await expect(documentControlApi.submitRevisionForApproval('rev-2', { note: 'submit' })).resolves.toEqual({
      controlled_document_id: 'doc-1',
      approval_request_id: 'req-1',
    });

    await expect(documentControlApi.approveRevisionStep('rev-2', { note: 'ok' })).resolves.toEqual({
      controlled_document_id: 'doc-1',
      approval_step: 'cosign',
    });

    await expect(documentControlApi.rejectRevisionStep('rev-2', { note: 'no' })).resolves.toEqual({
      controlled_document_id: 'doc-1',
      approval_step: 'approve',
    });

    await expect(documentControlApi.addSignRevisionStep('rev-2', { approver_user_id: 'user-2' })).resolves.toEqual({
      controlled_document_id: 'doc-1',
      approval_step: 'standardize_review',
    });

    await expect(documentControlApi.getDistributionDepartments('doc-1')).resolves.toEqual([10, 20]);

    await expect(
      documentControlApi.setDistributionDepartments('doc-1', { department_ids: [10, 20] })
    ).resolves.toEqual([10, 20]);

    await expect(
      documentControlApi.publishRevision('rev-2', { release_mode: 'manual_by_doc_control' })
    ).resolves.toEqual({
      controlled_document_id: 'doc-1',
      effective_revision_id: 'rev-2',
    });

    await expect(documentControlApi.listRevisionDepartmentAcks('rev-2')).resolves.toEqual([{ ack_id: 'ack-1' }]);

    await expect(
      documentControlApi.confirmRevisionDepartmentAck('rev-2', 10, { notes: 'ok' })
    ).resolves.toEqual({
      ack_id: 'ack-1',
      status: 'confirmed',
    });

    await expect(
      documentControlApi.remindOverdueRevisionDepartmentAcks('rev-2', { note: 'remind' })
    ).resolves.toEqual({
      reminded_count: 1,
    });

    await expect(
      documentControlApi.initiateObsoleteRevision('rev-2', {
        retirement_reason: 'obsolete',
        retention_until_ms: 123,
      })
    ).resolves.toEqual({
      controlled_document_id: 'doc-1',
      current_revision_id: 'rev-2',
    });

    await expect(documentControlApi.approveObsoleteRevision('rev-2', { note: 'approve' })).resolves.toEqual({
      controlled_document_id: 'doc-1',
      current_revision_id: 'rev-2',
    });

    await expect(
      documentControlApi.confirmRevisionDestruction('rev-2', { destruction_notes: 'offline done' })
    ).resolves.toEqual({
      controlled_document_id: 'doc-1',
      current_revision_id: 'rev-2',
    });

    await expect(documentControlApi.listRetiredDocuments({ kbId: 'kb-1', limit: 20 })).resolves.toEqual([
      { doc_id: 'kb-doc-1' },
    ]);

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/quality-system/doc-control/documents?limit=20&doc_code=DOC-1&title=URS&document_type=urs&product_name=Product+A&registration_ref=REG-001&status=draft&query=validation',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/quality-system/doc-control/documents/doc-1',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      3,
      'http://auth.local/api/quality-system/doc-control/documents',
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      })
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      4,
      'http://auth.local/api/quality-system/doc-control/documents/doc-1/revisions',
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      })
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      5,
      'http://auth.local/api/quality-system/doc-control/revisions/rev-2/approval/submit',
      {
        method: 'POST',
        body: JSON.stringify({ note: 'submit' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      6,
      'http://auth.local/api/quality-system/doc-control/revisions/rev-2/approval/approve',
      {
        method: 'POST',
        body: JSON.stringify({ note: 'ok' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      7,
      'http://auth.local/api/quality-system/doc-control/revisions/rev-2/approval/reject',
      {
        method: 'POST',
        body: JSON.stringify({ note: 'no' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      8,
      'http://auth.local/api/quality-system/doc-control/revisions/rev-2/approval/add-sign',
      {
        method: 'POST',
        body: JSON.stringify({ approver_user_id: 'user-2' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      9,
      'http://auth.local/api/quality-system/doc-control/documents/doc-1/distribution-departments',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      10,
      'http://auth.local/api/quality-system/doc-control/documents/doc-1/distribution-departments',
      {
        method: 'PUT',
        body: JSON.stringify({ department_ids: [10, 20] }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      11,
      'http://auth.local/api/quality-system/doc-control/revisions/rev-2/publish',
      {
        method: 'POST',
        body: JSON.stringify({ release_mode: 'manual_by_doc_control' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      12,
      'http://auth.local/api/quality-system/doc-control/revisions/rev-2/department-acks',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      13,
      'http://auth.local/api/quality-system/doc-control/revisions/rev-2/department-acks/10/confirm',
      {
        method: 'POST',
        body: JSON.stringify({ notes: 'ok' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      14,
      'http://auth.local/api/quality-system/doc-control/revisions/rev-2/department-acks/remind-overdue',
      {
        method: 'POST',
        body: JSON.stringify({ note: 'remind' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      15,
      'http://auth.local/api/quality-system/doc-control/revisions/rev-2/obsolete/initiate',
      {
        method: 'POST',
        body: JSON.stringify({ retirement_reason: 'obsolete', retention_until_ms: 123 }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      16,
      'http://auth.local/api/quality-system/doc-control/revisions/rev-2/obsolete/approve',
      {
        method: 'POST',
        body: JSON.stringify({ note: 'approve' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      17,
      'http://auth.local/api/quality-system/doc-control/revisions/rev-2/obsolete/destruction/confirm',
      {
        method: 'POST',
        body: JSON.stringify({ destruction_notes: 'offline done' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      18,
      'http://auth.local/api/retired-documents?kb_id=kb-1&limit=20',
      { method: 'GET' }
    );
  });

  it('fails fast when payload shapes do not match the page contract', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ count: 1 })
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce({ item: {} })
      .mockResolvedValueOnce({ result: {} })
      .mockResolvedValueOnce({ document: [] })
      .mockResolvedValueOnce({ document: [] })
      .mockResolvedValueOnce({ document: [] })
      .mockResolvedValueOnce({ document: [] })
      .mockResolvedValueOnce({ count: 1 })
      .mockResolvedValueOnce({ count: 1 })
      .mockResolvedValueOnce({ document: [] })
      .mockResolvedValueOnce({ count: 1 })
      .mockResolvedValueOnce({ ack: [] })
      .mockResolvedValueOnce({ result: [] })
      .mockResolvedValueOnce({ document: [] })
      .mockResolvedValueOnce({ document: [] })
      .mockResolvedValueOnce({ document: [] })
      .mockResolvedValueOnce({ count: 1 });

    await expect(documentControlApi.listDocuments()).rejects.toThrow(
      'document_control_documents_list_invalid_payload'
    );
    await expect(documentControlApi.getDocument('doc-1')).rejects.toThrow(
      'document_control_document_get_invalid_payload'
    );
    await expect(documentControlApi.createDocument({})).rejects.toThrow(
      'document_control_document_create_invalid_payload'
    );
    await expect(documentControlApi.createRevision('doc-1', {})).rejects.toThrow(
      'document_control_revision_create_invalid_payload'
    );
    await expect(documentControlApi.submitRevisionForApproval('rev-1', {})).rejects.toThrow(
      'document_control_revision_approval_submit_invalid_payload'
    );
    await expect(documentControlApi.approveRevisionStep('rev-1', {})).rejects.toThrow(
      'document_control_revision_approval_approve_invalid_payload'
    );
    await expect(documentControlApi.rejectRevisionStep('rev-1', {})).rejects.toThrow(
      'document_control_revision_approval_reject_invalid_payload'
    );
    await expect(documentControlApi.addSignRevisionStep('rev-1', {})).rejects.toThrow(
      'document_control_revision_approval_add_sign_invalid_payload'
    );
    await expect(documentControlApi.getDistributionDepartments('doc-1')).rejects.toThrow(
      'document_control_distribution_departments_get_invalid_payload'
    );
    await expect(documentControlApi.setDistributionDepartments('doc-1', {})).rejects.toThrow(
      'document_control_distribution_departments_set_invalid_payload'
    );
    await expect(documentControlApi.publishRevision('rev-1', {})).rejects.toThrow(
      'document_control_revision_publish_invalid_payload'
    );
    await expect(documentControlApi.listRevisionDepartmentAcks('rev-1')).rejects.toThrow(
      'document_control_department_acks_list_invalid_payload'
    );
    await expect(documentControlApi.confirmRevisionDepartmentAck('rev-1', 10, {})).rejects.toThrow(
      'document_control_department_ack_confirm_invalid_payload'
    );
    await expect(documentControlApi.remindOverdueRevisionDepartmentAcks('rev-1', {})).rejects.toThrow(
      'document_control_department_ack_remind_invalid_payload'
    );
    await expect(documentControlApi.initiateObsoleteRevision('rev-1', {})).rejects.toThrow(
      'document_control_obsolete_initiate_invalid_payload'
    );
    await expect(documentControlApi.approveObsoleteRevision('rev-1', {})).rejects.toThrow(
      'document_control_obsolete_approve_invalid_payload'
    );
    await expect(documentControlApi.confirmRevisionDestruction('rev-1', {})).rejects.toThrow(
      'document_control_destruction_confirm_invalid_payload'
    );
    await expect(documentControlApi.listRetiredDocuments()).rejects.toThrow(
      'document_control_retired_documents_list_invalid_payload'
    );
  });
});
