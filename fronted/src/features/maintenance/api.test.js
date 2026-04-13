import maintenanceApi from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('maintenanceApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('calls maintenance endpoints and normalizes payloads', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ items: [{ record_id: 'ma-1' }] })
      .mockResolvedValueOnce({ record_id: 'ma-1', status: 'planned' })
      .mockResolvedValueOnce({ record_id: 'ma-1', status: 'recorded' })
      .mockResolvedValueOnce({ record_id: 'ma-1', status: 'approved' })
      .mockResolvedValueOnce({ count: 1, items: [{ record_id: 'ma-1' }] });

    await expect(maintenanceApi.listRecords({ limit: 10, status: 'planned' })).resolves.toEqual([
      { record_id: 'ma-1' },
    ]);
    await expect(maintenanceApi.createRecord({ equipment_id: 'eq-1' })).resolves.toEqual({
      record_id: 'ma-1',
      status: 'planned',
    });
    await expect(maintenanceApi.recordExecution('ma-1', {})).resolves.toEqual({
      record_id: 'ma-1',
      status: 'recorded',
    });
    await expect(maintenanceApi.approveRecord('ma-1', {})).resolves.toEqual({
      record_id: 'ma-1',
      status: 'approved',
    });
    await expect(maintenanceApi.dispatchReminders(7)).resolves.toEqual({
      count: 1,
      items: [{ record_id: 'ma-1' }],
    });
  });
});

