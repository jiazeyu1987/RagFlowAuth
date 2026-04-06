import { act, renderHook, waitFor } from '@testing-library/react';
import operationApprovalApi from './api';
import useInboxPage from './useInboxPage';
import { publishInboxUnreadCount } from '../notification/inboxUnreadSync';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

jest.mock('./api', () => ({
  __esModule: true,
  default: {
    listInbox: jest.fn(),
    markInboxRead: jest.fn(),
    markAllInboxRead: jest.fn(),
  },
}));

jest.mock('../notification/inboxUnreadSync', () => ({
  publishInboxUnreadCount: jest.fn(),
}));

describe('useInboxPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    operationApprovalApi.listInbox.mockResolvedValue({
      items: [
        {
          inbox_id: 'inbox-1',
          title: '需要审批',
          status: 'unread',
          event_type: 'operation_approval_todo',
          payload: { request_id: 'req-1' },
        },
      ],
      count: 1,
      unreadCount: 1,
    });
    operationApprovalApi.markInboxRead.mockResolvedValue({
      inbox_id: 'inbox-1',
      status: 'read',
    });
    operationApprovalApi.markAllInboxRead.mockResolvedValue({
      updated: 1,
      unread_count: 0,
    });
  });

  it('loads inbox items and publishes unread count updates', async () => {
    const { result } = renderHook(() => useInboxPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(operationApprovalApi.listInbox).toHaveBeenCalledWith({
      unreadOnly: false,
      limit: 100,
    });
    expect(result.current.unreadCount).toBe(1);
    expect(result.current.items).toHaveLength(1);
    expect(publishInboxUnreadCount).toHaveBeenCalledWith(1);
  });

  it('marks unread items as read and navigates to approval detail', async () => {
    const { result } = renderHook(() => useInboxPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.handleOpen(result.current.items[0]);
    });

    expect(operationApprovalApi.markInboxRead).toHaveBeenCalledWith('inbox-1');
    expect(result.current.unreadCount).toBe(0);
    expect(mockNavigate).toHaveBeenCalledWith('/approvals?request_id=req-1');
    expect(publishInboxUnreadCount).toHaveBeenLastCalledWith(0);
  });
});
