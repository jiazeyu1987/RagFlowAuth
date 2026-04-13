import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MetrologyManagement from './MetrologyManagement';
import metrologyApi from '../features/metrology/api';

jest.mock('../features/metrology/api', () => ({
  __esModule: true,
  default: {
    listRecords: jest.fn(),
    createRecord: jest.fn(),
    recordResult: jest.fn(),
    confirmRecord: jest.fn(),
    approveRecord: jest.fn(),
    dispatchReminders: jest.fn(),
  },
}));

describe('MetrologyManagement page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    metrologyApi.listRecords.mockResolvedValue([
      {
        record_id: 'mt-1',
        equipment_id: 'eq-1',
        status: 'planned',
        planned_due_date: '2026-04-20',
        summary: 'monthly check',
      },
    ]);
    metrologyApi.createRecord.mockResolvedValue({ record_id: 'mt-2' });
    metrologyApi.recordResult.mockResolvedValue({ record_id: 'mt-1', status: 'recorded' });
    metrologyApi.dispatchReminders.mockResolvedValue({ count: 1, items: [{ record_id: 'mt-1' }] });
  });

  it('loads list, creates record, records result, and dispatches reminders', async () => {
    const user = userEvent.setup();
    render(<MetrologyManagement />);

    expect(await screen.findByTestId('metrology-management-page')).toBeInTheDocument();
    expect(await screen.findByText('mt-1')).toBeInTheDocument();

    await user.type(screen.getByTestId('metrology-create-equipment-id'), 'eq-2');
    await user.type(screen.getByTestId('metrology-create-responsible-user-id'), 'u-2');
    await user.type(screen.getByTestId('metrology-create-planned-due-date'), '2026-04-21');
    await user.type(screen.getByTestId('metrology-create-summary'), 'new check');
    await user.click(screen.getByTestId('metrology-create-submit'));

    await waitFor(() => expect(metrologyApi.createRecord).toHaveBeenCalled());

    await user.click(screen.getByTestId('metrology-action-mt-1-record'));
    await waitFor(() => expect(metrologyApi.recordResult).toHaveBeenCalled());

    await user.click(screen.getByTestId('metrology-dispatch-reminder'));
    await waitFor(() => expect(metrologyApi.dispatchReminders).toHaveBeenCalledWith(7));
  });
});

