import { act, renderHook, waitFor } from '@testing-library/react';
import useMessagesPage from './useMessagesPage';
import { notificationApi } from '../api';
import { publishInboxUnreadCount } from '../inboxUnreadSync';

jest.mock('../api', () => ({
  notificationApi: {
    listMyMessages: jest.fn(),
    updateMyMessageReadState: jest.fn(),
    markAllMyMessagesRead: jest.fn(),
  },
}));

jest.mock('../inboxUnreadSync', () => ({
  publishInboxUnreadCount: jest.fn(),
}));

describe('useMessagesPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    notificationApi.listMyMessages.mockResolvedValue({
      items: [
        {
          job_id: 11,
          event_type: 'approval',
          created_at_ms: 1710000000000,
          read_at_ms: null,
          payload: { filename: 'demo.txt', current_step_name: '审核中' },
        },
      ],
      total: 1,
      unread_count: 1,
    });
    notificationApi.updateMyMessageReadState.mockResolvedValue({});
    notificationApi.markAllMyMessagesRead.mockResolvedValue({});
  });

  it('loads messages and unread counters on mount', async () => {
    const { result } = renderHook(() => useMessagesPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(notificationApi.listMyMessages).toHaveBeenCalledWith({ limit: 100, offset: 0, unreadOnly: false });
    expect(result.current.items).toHaveLength(1);
    expect(result.current.total).toBe(1);
    expect(result.current.unreadCount).toBe(1);
    expect(publishInboxUnreadCount).toHaveBeenCalledWith(1);
  });

  it('reloads using unread filter and removes rows when marking unread-only items as read', async () => {
    const { result } = renderHook(() => useMessagesPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    notificationApi.listMyMessages.mockResolvedValueOnce({
      items: [
        {
          job_id: 11,
          event_type: 'approval',
          created_at_ms: 1710000000000,
          read_at_ms: null,
          payload: {},
        },
      ],
      total: 1,
      unread_count: 1,
    });

    await act(async () => {
      result.current.handleToggleUnreadOnly();
    });

    await waitFor(() => {
      expect(notificationApi.listMyMessages).toHaveBeenLastCalledWith({ limit: 100, offset: 0, unreadOnly: true });
    });

    await act(async () => {
      await result.current.handleToggleRead(result.current.items[0]);
    });

    expect(notificationApi.updateMyMessageReadState).toHaveBeenCalledWith(11, true);
    expect(result.current.items).toHaveLength(0);
    expect(result.current.total).toBe(0);
    expect(result.current.unreadCount).toBe(0);
    expect(publishInboxUnreadCount).toHaveBeenLastCalledWith(0);
  });

  it('marks all rows as read and clears the unread counter', async () => {
    const { result } = renderHook(() => useMessagesPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.handleMarkAllRead();
    });

    expect(notificationApi.markAllMyMessagesRead).toHaveBeenCalledTimes(1);
    expect(result.current.unreadCount).toBe(0);
    expect(result.current.items[0].read_at_ms).toBeTruthy();
    expect(publishInboxUnreadCount).toHaveBeenLastCalledWith(0);
  });
});
