import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import Dashboard from './Dashboard';
import operationApprovalApi from '../features/operationApproval/api';
import { useAuth } from '../hooks/useAuth';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

jest.mock('../features/operationApproval/api', () => ({
  __esModule: true,
  default: {
    getStats: jest.fn(),
  },
}));

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

describe('Dashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      user: {
        username: 'alice',
        full_name: 'Alice',
        role: 'manager',
      },
      can: (resource, action) => {
        if (resource === 'ragflow_documents' && action === 'view') return true;
        if (resource === 'kb_documents' && action === 'view') return true;
        if (resource === 'kb_documents' && action === 'upload') return true;
        return false;
      },
    });
    operationApprovalApi.getStats.mockResolvedValue({
      in_approval_count: 4,
      executed_count: 8,
      rejected_count: 1,
      execution_failed_count: 2,
    });
  });

  it('renders approval stats and quick actions from the feature hook state', async () => {
    const user = userEvent.setup();

    render(<Dashboard />);

    expect(await screen.findByTestId('dashboard-page')).toBeInTheDocument();
    expect(await screen.findByText('控制台')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByTestId('dashboard-quick-upload')).toBeInTheDocument();

    await user.click(screen.getByTestId('dashboard-card-in_approval'));
    await user.click(screen.getByTestId('dashboard-quick-browser'));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenNthCalledWith(1, '/approvals?status=in_approval');
    });
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenNthCalledWith(2, '/browser');
    });
  });
});
