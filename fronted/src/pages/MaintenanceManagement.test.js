import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MaintenanceManagement from './MaintenanceManagement';
import maintenanceApi from '../features/maintenance/api';

jest.mock('../features/maintenance/api', () => ({
  __esModule: true,
  default: {
    listRecords: jest.fn(),
    createRecord: jest.fn(),
    recordExecution: jest.fn(),
    approveRecord: jest.fn(),
    dispatchReminders: jest.fn(),
  },
}));

describe('MaintenanceManagement page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    maintenanceApi.listRecords.mockResolvedValue([
      {
        record_id: 'ma-1',
        equipment_id: 'eq-1',
        maintenance_type: 'preventive',
        status: 'planned',
      },
    ]);
    maintenanceApi.createRecord.mockResolvedValue({ record_id: 'ma-2' });
    maintenanceApi.recordExecution.mockResolvedValue({ record_id: 'ma-1', status: 'recorded' });
    maintenanceApi.dispatchReminders.mockResolvedValue({ count: 1, items: [{ record_id: 'ma-1' }] });
  });

  it('loads list, creates record, records execution, and dispatches reminders', async () => {
    const user = userEvent.setup();
    render(<MaintenanceManagement />);

    expect(await screen.findByTestId('maintenance-management-page')).toBeInTheDocument();
    expect(await screen.findByText('ma-1')).toBeInTheDocument();

    await user.type(screen.getByTestId('maintenance-create-equipment-id'), 'eq-2');
    await user.type(screen.getByTestId('maintenance-create-responsible-user-id'), 'u-2');
    await user.type(screen.getByTestId('maintenance-create-planned-due-date'), '2026-04-21');
    await user.type(screen.getByTestId('maintenance-create-summary'), 'new maintenance');
    await user.click(screen.getByTestId('maintenance-create-submit'));

    await waitFor(() => expect(maintenanceApi.createRecord).toHaveBeenCalled());

    await user.click(screen.getByTestId('maintenance-action-ma-1-record'));
    await waitFor(() => expect(maintenanceApi.recordExecution).toHaveBeenCalled());

    await user.click(screen.getByTestId('maintenance-dispatch-reminder'));
    await waitFor(() => expect(maintenanceApi.dispatchReminders).toHaveBeenCalledWith(7));
  });
});

