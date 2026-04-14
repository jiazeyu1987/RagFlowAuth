import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';

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
      can: jest.fn((resource, action) => resource === 'quality_system' && action === 'manage'),
      isAuthorized: jest.fn(() => true),
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

  it('renders authorized module cards and quality-system queue items', async () => {
    renderPage();

    expect(await screen.findByTestId('quality-system-page')).toBeInTheDocument();
    expect(screen.getByTestId('quality-system-module-doc-control')).toBeInTheDocument();
    expect(screen.getByTestId('quality-system-module-batch-records')).toBeInTheDocument();

    await waitFor(() => {
      expect(operationApprovalApi.listInbox).toHaveBeenCalledWith({ limit: 20 });
    });

    expect(screen.getByTestId('quality-system-queue-item-queue-1')).toBeInTheDocument();
    expect(screen.queryByTestId('quality-system-queue-item-queue-2')).not.toBeInTheDocument();
  });

  it('shows an empty module hint when no modules are authorized', async () => {
    useAuth.mockReturnValue({
      user: baseUser,
      can: jest.fn(() => false),
      isAuthorized: jest.fn(() => false),
    });

    renderPage();

    expect(await screen.findByTestId('quality-system-page')).toBeInTheDocument();
    expect(await screen.findByTestId('quality-system-modules-empty')).toBeInTheDocument();
  });
});

