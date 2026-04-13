import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EquipmentLifecycle from './EquipmentLifecycle';
import equipmentApi from '../features/equipment/api';

jest.mock('../features/equipment/api', () => ({
  __esModule: true,
  default: {
    listAssets: jest.fn(),
    createAsset: jest.fn(),
    acceptAsset: jest.fn(),
    commissionAsset: jest.fn(),
    retireAsset: jest.fn(),
    dispatchReminders: jest.fn(),
  },
}));

describe('EquipmentLifecycle page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    equipmentApi.listAssets.mockResolvedValue([
      {
        equipment_id: 'eq-1',
        asset_code: 'EQ-001',
        equipment_name: 'Mixer',
        owner_user_id: 'u-1',
        status: 'purchased',
      },
    ]);
    equipmentApi.createAsset.mockResolvedValue({ equipment_id: 'eq-2' });
    equipmentApi.acceptAsset.mockResolvedValue({ equipment_id: 'eq-1', status: 'accepted' });
    equipmentApi.dispatchReminders.mockResolvedValue({ count: 1, items: [{ equipment_id: 'eq-1' }] });
  });

  it('loads list, creates asset, transitions status, and dispatches reminders', async () => {
    const user = userEvent.setup();
    render(<EquipmentLifecycle />);

    expect(await screen.findByTestId('equipment-lifecycle-page')).toBeInTheDocument();
    expect(await screen.findByText('EQ-001')).toBeInTheDocument();

    await user.type(screen.getByTestId('equipment-create-asset-code'), 'EQ-002');
    await user.type(screen.getByTestId('equipment-create-name'), 'Pump');
    await user.type(screen.getByTestId('equipment-create-owner-user-id'), 'u-2');
    await user.click(screen.getByTestId('equipment-create-submit'));

    await waitFor(() => expect(equipmentApi.createAsset).toHaveBeenCalled());

    await user.click(screen.getByTestId('equipment-action-eq-1-accept'));
    await waitFor(() => expect(equipmentApi.acceptAsset).toHaveBeenCalledWith('eq-1'));

    await user.click(screen.getByTestId('equipment-dispatch-reminder'));
    await waitFor(() => expect(equipmentApi.dispatchReminders).toHaveBeenCalledWith(7));
  });
});

