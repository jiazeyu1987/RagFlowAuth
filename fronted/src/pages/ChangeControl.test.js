import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChangeControl from './ChangeControl';
import changeControlApi from '../features/changeControl/api';

jest.mock('../features/changeControl/api', () => ({
  __esModule: true,
  default: {
    listRequests: jest.fn(),
    createRequest: jest.fn(),
    evaluateRequest: jest.fn(),
    createPlanItem: jest.fn(),
    markPlanned: jest.fn(),
    startExecution: jest.fn(),
    completeExecution: jest.fn(),
    confirmDepartment: jest.fn(),
    closeRequest: jest.fn(),
    dispatchReminders: jest.fn(),
  },
}));

const baselineRequest = {
  request_id: 'cc-1',
  title: 'CC request',
  reason: 'Need control',
  status: 'initiated',
  owner_user_id: 'owner-1',
  plan_items: [],
};

describe('ChangeControl page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    changeControlApi.listRequests.mockResolvedValue([baselineRequest]);
    changeControlApi.createRequest.mockResolvedValue(baselineRequest);
    changeControlApi.evaluateRequest.mockResolvedValue({ ...baselineRequest, status: 'evaluated' });
    changeControlApi.createPlanItem.mockResolvedValue({ ...baselineRequest, status: 'evaluated' });
    changeControlApi.markPlanned.mockResolvedValue({ ...baselineRequest, status: 'planned' });
    changeControlApi.startExecution.mockResolvedValue({ ...baselineRequest, status: 'executing' });
    changeControlApi.completeExecution.mockResolvedValue({ ...baselineRequest, status: 'pending_confirmation' });
    changeControlApi.confirmDepartment.mockResolvedValue({ ...baselineRequest, status: 'confirmed' });
    changeControlApi.closeRequest.mockResolvedValue({ ...baselineRequest, status: 'closed' });
    changeControlApi.dispatchReminders.mockResolvedValue({ count: 1, items: [] });
  });

  it('loads list, creates a request, and triggers key workflow actions', async () => {
    const user = userEvent.setup();
    render(<ChangeControl />);

    expect(await screen.findByTestId('change-control-page')).toBeInTheDocument();
    expect(await screen.findByTestId('change-control-row-cc-1')).toBeInTheDocument();

    await user.type(screen.getByTestId('change-control-create-title'), 'New title');
    await user.type(screen.getByTestId('change-control-create-reason'), 'New reason');
    await user.type(screen.getByTestId('change-control-create-owner-user-id'), 'owner-1');
    await user.type(screen.getByTestId('change-control-create-evaluator-user-id'), 'eval-1');
    await user.click(screen.getByTestId('change-control-create-submit'));

    await waitFor(() => expect(changeControlApi.createRequest).toHaveBeenCalled());

    await user.click(screen.getByTestId('change-control-dispatch-reminder'));
    await waitFor(() => expect(changeControlApi.dispatchReminders).toHaveBeenCalledWith(7));

    await user.click(screen.getByTestId('change-control-evaluate'));
    await user.click(screen.getByTestId('change-control-add-plan-item'));
    await user.click(screen.getByTestId('change-control-mark-planned'));
    await user.click(screen.getByTestId('change-control-start-execution'));
    await user.click(screen.getByTestId('change-control-complete-execution'));
    await user.click(screen.getByTestId('change-control-confirm-qa'));
    await user.click(screen.getByTestId('change-control-close'));

    await waitFor(() => {
      expect(changeControlApi.evaluateRequest).toHaveBeenCalled();
      expect(changeControlApi.createPlanItem).toHaveBeenCalled();
      expect(changeControlApi.markPlanned).toHaveBeenCalled();
      expect(changeControlApi.startExecution).toHaveBeenCalled();
      expect(changeControlApi.completeExecution).toHaveBeenCalled();
      expect(changeControlApi.confirmDepartment).toHaveBeenCalled();
      expect(changeControlApi.closeRequest).toHaveBeenCalled();
    });
  });
});
