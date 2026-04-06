import { act, renderHook, waitFor } from '@testing-library/react';
import operationApprovalApi from './api';
import useDashboardPage from './useDashboardPage';
import { useAuth } from '../../hooks/useAuth';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

jest.mock('./api', () => ({
  __esModule: true,
  default: {
    getStats: jest.fn(),
  },
}));

jest.mock('../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

describe('useDashboardPage', () => {
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
        if (resource === 'kb_documents' && action === 'upload') return false;
        return false;
      },
    });
    operationApprovalApi.getStats.mockResolvedValue({
      in_approval_count: 3,
      executed_count: 7,
      rejected_count: 2,
      execution_failed_count: 1,
    });
  });

  it('loads approval stats and exposes filtered quick actions', async () => {
    const { result } = renderHook(() => useDashboardPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(operationApprovalApi.getStats).toHaveBeenCalledTimes(1);
    expect(result.current.cards.map((card) => [card.key, card.value])).toEqual([
      ['in_approval', 3],
      ['executed', 7],
      ['rejected', 2],
      ['execution_failed', 1],
    ]);
    expect(result.current.quickActions.map((action) => action.key)).toEqual([
      'approvals',
      'document-history',
      'browser',
    ]);
  });

  it('routes card and quick action clicks through navigate', async () => {
    const { result } = renderHook(() => useDashboardPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.cards[0].onClick();
      result.current.quickActions[0].onClick();
    });

    expect(mockNavigate).toHaveBeenNthCalledWith(1, '/approvals?status=in_approval');
    expect(mockNavigate).toHaveBeenNthCalledWith(2, '/approvals');
  });
});
