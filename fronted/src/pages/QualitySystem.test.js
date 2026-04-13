import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import QualitySystem from './QualitySystem';
import operationApprovalApi from '../features/operationApproval/api';
import { useAuth } from '../hooks/useAuth';

jest.mock('../features/operationApproval/api', () => ({
  __esModule: true,
  default: {
    listInbox: jest.fn(),
  },
}));

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('./ChangeControl', () => ({
  __esModule: true,
  default: () => <div data-testid="change-control-page" />,
}));

const baseUser = {
  user_id: 'sub-1',
  username: 'quality-sub',
  role: 'sub_admin',
};

const renderPage = (initialEntries = ['/quality-system']) => render(
  <MemoryRouter initialEntries={initialEntries}>
    <QualitySystem />
  </MemoryRouter>
);

describe('QualitySystem', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      user: baseUser,
      can: jest.fn((resource, action) => resource === 'quality_system' && action === 'view'),
    });
    operationApprovalApi.listInbox.mockResolvedValue({
      items: [
        {
          inbox_id: 'queue-1',
          status: 'unread',
          title: 'Training review',
          link_path: '/quality-system/training?request_id=req-1',
        },
        {
          inbox_id: 'queue-2',
          status: 'read',
          title: 'Other area',
          link_path: '/approvals?request_id=req-2',
        },
      ],
      count: 2,
      unreadCount: 1,
    });
  });

  it('renders module cards and quality-system-scoped queue items on the root shell', async () => {
    renderPage();

    expect(await screen.findByTestId('quality-system-page')).toBeInTheDocument();
    expect(screen.getByTestId('quality-system-module-doc-control')).toBeInTheDocument();
    expect(screen.getByTestId('quality-system-module-training')).toBeInTheDocument();

    await waitFor(() => {
      expect(operationApprovalApi.listInbox).toHaveBeenCalledWith({ limit: 20 });
    });

    expect(screen.getByTestId('quality-system-queue-item-queue-1')).toBeInTheDocument();
    expect(screen.queryByTestId('quality-system-queue-item-queue-2')).not.toBeInTheDocument();
  });

  it('renders selected child-route context and filters queue items to the current module', async () => {
    renderPage(['/quality-system/training']);

    expect(await screen.findByTestId('quality-system-selected-module')).toBeInTheDocument();
    expect(screen.getByTestId('quality-system-selected-title')).toHaveTextContent('\u57f9\u8bad');

    await waitFor(() => {
      expect(screen.getByTestId('quality-system-queue-item-queue-1')).toBeInTheDocument();
    });
  });

  it('navigates to module routes and back to the shell root', async () => {
    const user = userEvent.setup();

    renderPage();

    await user.click(await screen.findByTestId('quality-system-open-training'));
    expect(await screen.findByTestId('quality-system-selected-title')).toHaveTextContent('\u57f9\u8bad');

    await user.click(screen.getByTestId('quality-system-return-root'));
    await waitFor(() => {
      expect(screen.queryByTestId('quality-system-selected-module')).not.toBeInTheDocument();
    });
  });

  it('shows a queue error without hiding the shell when inbox loading fails', async () => {
    operationApprovalApi.listInbox.mockRejectedValue(new Error('operation_approval_service_unavailable'));

    renderPage();

    expect(await screen.findByTestId('quality-system-page')).toBeInTheDocument();
    expect(await screen.findByTestId('quality-system-queue-error')).toBeInTheDocument();
    expect(screen.getByTestId('quality-system-module-audit')).toBeInTheDocument();
  });

  it('renders WS04 page directly on change-control subroute', async () => {
    renderPage(['/quality-system/change-control']);

    expect(await screen.findByTestId('change-control-page')).toBeInTheDocument();
    expect(screen.queryByTestId('quality-system-page')).not.toBeInTheDocument();
  });
});
