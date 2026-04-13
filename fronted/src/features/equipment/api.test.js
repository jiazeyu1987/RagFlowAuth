import equipmentApi from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('equipmentApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('calls equipment endpoints and normalizes payloads', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ items: [{ equipment_id: 'eq-1' }] })
      .mockResolvedValueOnce({ equipment_id: 'eq-1' })
      .mockResolvedValueOnce({ equipment_id: 'eq-2' })
      .mockResolvedValueOnce({ equipment_id: 'eq-2', status: 'accepted' })
      .mockResolvedValueOnce({ equipment_id: 'eq-2', status: 'in_service' })
      .mockResolvedValueOnce({ equipment_id: 'eq-2', status: 'retired' })
      .mockResolvedValueOnce({ count: 1, items: [{ equipment_id: 'eq-2' }] });

    await expect(equipmentApi.listAssets({ limit: 20, status: 'purchased' })).resolves.toEqual([
      { equipment_id: 'eq-1' },
    ]);
    await expect(equipmentApi.getAsset('eq-1')).resolves.toEqual({ equipment_id: 'eq-1' });
    await expect(equipmentApi.createAsset({ asset_code: 'EQ-002' })).resolves.toEqual({
      equipment_id: 'eq-2',
    });
    await expect(equipmentApi.acceptAsset('eq-2')).resolves.toEqual({
      equipment_id: 'eq-2',
      status: 'accepted',
    });
    await expect(equipmentApi.commissionAsset('eq-2')).resolves.toEqual({
      equipment_id: 'eq-2',
      status: 'in_service',
    });
    await expect(equipmentApi.retireAsset('eq-2')).resolves.toEqual({
      equipment_id: 'eq-2',
      status: 'retired',
    });
    await expect(equipmentApi.dispatchReminders(7)).resolves.toEqual({
      count: 1,
      items: [{ equipment_id: 'eq-2' }],
    });
  });
});

