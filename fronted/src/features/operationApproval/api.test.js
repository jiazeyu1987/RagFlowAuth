import operationApprovalApi from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('operationApprovalApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('normalizes approval list endpoints to stable arrays and inbox state', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ items: [{ operation_type: 'knowledge_file_upload' }], count: 1 })
      .mockResolvedValueOnce({ items: [{ request_id: 'req-1' }], count: 1 })
      .mockResolvedValueOnce({ items: [{ request_id: 'req-2' }], count: 1 })
      .mockResolvedValueOnce({ items: [{ inbox_id: 'inbox-1' }], count: 1, unread_count: 1 });

    await expect(operationApprovalApi.listWorkflows()).resolves.toEqual([
      { operation_type: 'knowledge_file_upload' },
    ]);
    await expect(operationApprovalApi.listRequests({ view: 'todo', status: 'rejected', limit: 20 })).resolves.toEqual([
      { request_id: 'req-1' },
    ]);
    await expect(operationApprovalApi.listTodos({ limit: 10 })).resolves.toEqual([
      { request_id: 'req-2' },
    ]);
    await expect(operationApprovalApi.listInbox({ unreadOnly: true, limit: 30 })).resolves.toEqual({
      items: [{ inbox_id: 'inbox-1' }],
      count: 1,
      unreadCount: 1,
    });

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/operation-approvals/workflows',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/operation-approvals/requests?view=todo&status=rejected&limit=20',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      3,
      'http://auth.local/api/operation-approvals/todos?limit=10',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      4,
      'http://auth.local/api/inbox?unread_only=true&limit=30',
      { method: 'GET' }
    );
  });

  it('normalizes detail and mutation endpoints to explicit result objects', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ request_id: 'req/1' })
      .mockResolvedValueOnce({ in_approval_count: 3 })
      .mockResolvedValueOnce({
        result: {
          message: 'operation_approval_workflow_updated',
          operation_type: 'knowledge/file',
        },
      })
      .mockResolvedValueOnce({
        result: {
          message: 'operation_approval_request_approved',
          request_id: 'req/1',
          status: 'approved',
        },
      })
      .mockResolvedValueOnce({
        result: {
          message: 'operation_approval_request_rejected',
          request_id: 'req/1',
          status: 'rejected',
        },
      })
      .mockResolvedValueOnce({
        result: {
          message: 'operation_approval_request_withdrawn',
          request_id: 'req/1',
          status: 'withdrawn',
        },
      })
      .mockResolvedValueOnce({
        result: {
          message: 'inbox_notification_marked_read',
          inbox_id: 'inbox/1',
          status: 'read',
        },
      })
      .mockResolvedValueOnce({
        result: {
          message: 'inbox_notifications_marked_read',
          updated: 2,
          unread_count: 0,
        },
      });

    await expect(operationApprovalApi.getRequest('req/1')).resolves.toEqual({ request_id: 'req/1' });
    await expect(operationApprovalApi.getStats()).resolves.toEqual({ in_approval_count: 3 });
    await expect(operationApprovalApi.updateWorkflow('knowledge/file', { name: 'demo' })).resolves.toEqual({
      message: 'operation_approval_workflow_updated',
      operation_type: 'knowledge/file',
    });
    await expect(operationApprovalApi.approveRequest('req/1', { notes: 'ok' })).resolves.toEqual({
      message: 'operation_approval_request_approved',
      request_id: 'req/1',
      status: 'approved',
    });
    await expect(operationApprovalApi.rejectRequest('req/1', { notes: 'no' })).resolves.toEqual({
      message: 'operation_approval_request_rejected',
      request_id: 'req/1',
      status: 'rejected',
    });
    await expect(operationApprovalApi.withdrawRequest('req/1', { reason: 'changed' })).resolves.toEqual({
      message: 'operation_approval_request_withdrawn',
      request_id: 'req/1',
      status: 'withdrawn',
    });
    await expect(operationApprovalApi.markInboxRead('inbox/1')).resolves.toEqual({
      message: 'inbox_notification_marked_read',
      inbox_id: 'inbox/1',
      status: 'read',
    });
    await expect(operationApprovalApi.markAllInboxRead()).resolves.toEqual({
      message: 'inbox_notifications_marked_read',
      updated: 2,
      unread_count: 0,
    });

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/operation-approvals/requests/req%2F1',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/operation-approvals/stats',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      3,
      'http://auth.local/api/operation-approvals/workflows/knowledge%2Ffile',
      {
        method: 'PUT',
        body: JSON.stringify({ name: 'demo' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      4,
      'http://auth.local/api/operation-approvals/requests/req%2F1/approve',
      {
        method: 'POST',
        body: JSON.stringify({ notes: 'ok' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      5,
      'http://auth.local/api/operation-approvals/requests/req%2F1/reject',
      {
        method: 'POST',
        body: JSON.stringify({ notes: 'no' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      6,
      'http://auth.local/api/operation-approvals/requests/req%2F1/withdraw',
      {
        method: 'POST',
        body: JSON.stringify({ reason: 'changed' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      7,
      'http://auth.local/api/inbox/inbox%2F1/read',
      {
        method: 'POST',
        body: JSON.stringify({}),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      8,
      'http://auth.local/api/inbox/read-all',
      {
        method: 'POST',
        body: JSON.stringify({}),
      }
    );
  });

  it('fails fast when normalized list payloads are invalid', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ count: 0 })
      .mockResolvedValueOnce({ items: [], count: '0', unread_count: 0 })
      .mockResolvedValueOnce(null);

    await expect(operationApprovalApi.listWorkflows()).rejects.toThrow(
      'operation_approval_workflows_list_invalid_payload'
    );
    await expect(operationApprovalApi.listInbox()).rejects.toThrow(
      'operation_approval_inbox_list_invalid_payload'
    );
    await expect(operationApprovalApi.getRequest('req-1')).rejects.toThrow(
      'operation_approval_request_get_invalid_payload'
    );
  });

  it('fails fast when mutation result payloads are invalid', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ result: { message: 'operation_approval_workflow_updated' } })
      .mockResolvedValueOnce({ result: { message: 'operation_approval_request_approved', status: 'approved' } })
      .mockResolvedValueOnce({ result: { message: 'inbox_notification_marked_read', status: 'read' } })
      .mockResolvedValueOnce({ result: { message: 'inbox_notifications_marked_read', updated: 1 } });

    await expect(operationApprovalApi.updateWorkflow('knowledge/file', { name: 'demo' })).rejects.toThrow(
      'operation_approval_workflow_update_invalid_payload'
    );
    await expect(operationApprovalApi.approveRequest('req-1', { notes: 'ok' })).rejects.toThrow(
      'operation_approval_request_approve_invalid_payload'
    );
    await expect(operationApprovalApi.markInboxRead('inbox-1')).rejects.toThrow(
      'operation_approval_inbox_read_invalid_payload'
    );
    await expect(operationApprovalApi.markAllInboxRead()).rejects.toThrow(
      'operation_approval_inbox_read_all_invalid_payload'
    );
  });
});
