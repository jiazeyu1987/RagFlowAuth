import React from 'react';
import { render, screen } from '@testing-library/react';
import Messages from './Messages';
import useMessagesPage from '../features/notification/messages/useMessagesPage';

jest.mock('../features/notification/messages/useMessagesPage', () => jest.fn());

describe('Messages', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders unread counts and message rows from the feature hook', () => {
    useMessagesPage.mockReturnValue({
      loading: false,
      error: '',
      items: [
        {
          job_id: 11,
          event_type: 'operation_approval_todo',
          created_at_ms: 1710000000000,
          read_at_ms: null,
          payload: {
            filename: 'demo.txt',
            current_step_name: '审核中',
          },
        },
      ],
      total: 1,
      unreadCount: 1,
      unreadOnly: false,
      busyMap: {},
      markAllBusy: false,
      handleToggleUnreadOnly: jest.fn(),
      handleToggleRead: jest.fn(),
      handleMarkAllRead: jest.fn(),
    });

    render(<Messages />);

    expect(screen.getByTestId('messages-page')).toBeInTheDocument();
    expect(screen.getByTestId('messages-unread-count')).toHaveTextContent('未读 1');
    expect(screen.getByTestId('messages-total')).toHaveTextContent('共 1 条');
    expect(screen.getByTestId('messages-row-11')).toHaveTextContent('demo.txt');
    expect(screen.getByTestId('messages-row-11')).toHaveTextContent('审核中');
  });

  it('renders loading and error states from the feature hook', () => {
    useMessagesPage.mockReturnValue({
      loading: true,
      error: '',
      items: [],
      total: 0,
      unreadCount: 0,
      unreadOnly: false,
      busyMap: {},
      markAllBusy: false,
      handleToggleUnreadOnly: jest.fn(),
      handleToggleRead: jest.fn(),
      handleMarkAllRead: jest.fn(),
    });

    const { rerender } = render(<Messages />);
    expect(screen.getByText('正在加载站内信...')).toBeInTheDocument();

    useMessagesPage.mockReturnValue({
      loading: false,
      error: '加载失败',
      items: [],
      total: 0,
      unreadCount: 0,
      unreadOnly: false,
      busyMap: {},
      markAllBusy: false,
      handleToggleUnreadOnly: jest.fn(),
      handleToggleRead: jest.fn(),
      handleMarkAllRead: jest.fn(),
    });

    rerender(<Messages />);
    expect(screen.getByTestId('messages-error')).toHaveTextContent('加载失败');
  });
});
