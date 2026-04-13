import metrologyApi from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('metrologyApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('calls metrology endpoints and normalizes payloads', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ items: [{ record_id: 'mt-1' }] })
      .mockResolvedValueOnce({ record_id: 'mt-1', status: 'planned' })
      .mockResolvedValueOnce({ record_id: 'mt-1', status: 'recorded' })
      .mockResolvedValueOnce({ record_id: 'mt-1', status: 'confirmed' })
      .mockResolvedValueOnce({ record_id: 'mt-1', status: 'approved' })
      .mockResolvedValueOnce({ count: 1, items: [{ record_id: 'mt-1' }] });

    await expect(metrologyApi.listRecords({ limit: 10, status: 'planned' })).resolves.toEqual([
      { record_id: 'mt-1' },
    ]);
    await expect(metrologyApi.createRecord({ equipment_id: 'eq-1' })).resolves.toEqual({
      record_id: 'mt-1',
      status: 'planned',
    });
    await expect(metrologyApi.recordResult('mt-1', {})).resolves.toEqual({
      record_id: 'mt-1',
      status: 'recorded',
    });
    await expect(metrologyApi.confirmRecord('mt-1', {})).resolves.toEqual({
      record_id: 'mt-1',
      status: 'confirmed',
    });
    await expect(metrologyApi.approveRecord('mt-1', {})).resolves.toEqual({
      record_id: 'mt-1',
      status: 'approved',
    });
    await expect(metrologyApi.dispatchReminders(7)).resolves.toEqual({
      count: 1,
      items: [{ record_id: 'mt-1' }],
    });
  });
});

