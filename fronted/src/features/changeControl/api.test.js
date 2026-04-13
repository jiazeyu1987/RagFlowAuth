import changeControlApi from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('changeControlApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('covers request lifecycle endpoints', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ items: [{ request_id: 'cc-1' }] })
      .mockResolvedValueOnce({ request_id: 'cc-1', status: 'initiated' })
      .mockResolvedValueOnce({ request_id: 'cc-1', status: 'evaluated' })
      .mockResolvedValueOnce({ request_id: 'cc-1', status: 'evaluated' })
      .mockResolvedValueOnce({ request_id: 'cc-1', status: 'planned' })
      .mockResolvedValueOnce({ request_id: 'cc-1', status: 'executing' })
      .mockResolvedValueOnce({ request_id: 'cc-1', status: 'pending_confirmation' })
      .mockResolvedValueOnce({ request_id: 'cc-1', status: 'confirmed' })
      .mockResolvedValueOnce({ window_days: 7, count: 1, items: [] })
      .mockResolvedValueOnce({ request_id: 'cc-1', status: 'closed' });

    await expect(changeControlApi.listRequests({ limit: 10 })).resolves.toEqual([{ request_id: 'cc-1' }]);
    await expect(changeControlApi.createRequest({ title: 'a' })).resolves.toEqual({
      request_id: 'cc-1',
      status: 'initiated',
    });
    await expect(changeControlApi.evaluateRequest('cc-1', { evaluation_summary: 'ok' })).resolves.toEqual({
      request_id: 'cc-1',
      status: 'evaluated',
    });
    await expect(changeControlApi.createPlanItem('cc-1', { title: 'p1' })).resolves.toEqual({
      request_id: 'cc-1',
      status: 'evaluated',
    });
    await expect(changeControlApi.markPlanned('cc-1', { plan_summary: 'planned' })).resolves.toEqual({
      request_id: 'cc-1',
      status: 'planned',
    });
    await expect(changeControlApi.startExecution('cc-1')).resolves.toEqual({
      request_id: 'cc-1',
      status: 'executing',
    });
    await expect(changeControlApi.completeExecution('cc-1', { execution_summary: 'done' })).resolves.toEqual({
      request_id: 'cc-1',
      status: 'pending_confirmation',
    });
    await expect(changeControlApi.confirmDepartment('cc-1', { department_code: 'qa' })).resolves.toEqual({
      request_id: 'cc-1',
      status: 'confirmed',
    });
    await expect(changeControlApi.dispatchReminders(7)).resolves.toEqual({
      window_days: 7,
      count: 1,
      items: [],
    });
    await expect(
      changeControlApi.closeRequest('cc-1', {
        close_summary: 'done',
        close_outcome: 'effective',
        ledger_writeback_ref: 'L-1',
        closed_controlled_revisions: ['DOC-1'],
      })
    ).resolves.toEqual({
      request_id: 'cc-1',
      status: 'closed',
    });
  });
});
