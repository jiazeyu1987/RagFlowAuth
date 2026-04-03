import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import InboxPage from './InboxPage';
import operationApprovalApi from '../features/operationApproval/api';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

jest.mock('../features/operationApproval/api', () => ({
  __esModule: true,
  default: {
    listInbox: jest.fn(),
    markInboxRead: jest.fn(),
    markAllInboxRead: jest.fn(),
  },
}));

describe('InboxPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('marks inbox item as read and navigates to approval detail', async () => {
    const user = userEvent.setup();
    operationApprovalApi.listInbox
      .mockResolvedValueOnce({
        items: [
          {
            inbox_id: 'inbox-1',
            title: '需要审批',
            body: '请审批申请单',
            status: 'unread',
            event_type: 'operation_approval_todo',
            created_at_ms: 1_710_000_000_000,
            payload: { request_id: 'req-1' },
          },
        ],
        unread_count: 1,
      })
      .mockResolvedValueOnce({
        items: [
          {
            inbox_id: 'inbox-1',
            title: '需要审批',
            body: '请审批申请单',
            status: 'read',
            event_type: 'operation_approval_todo',
            created_at_ms: 1_710_000_000_000,
            payload: { request_id: 'req-1' },
          },
        ],
        unread_count: 0,
      });
    operationApprovalApi.markInboxRead.mockResolvedValue({ inbox_id: 'inbox-1', status: 'read' });

    render(
      <MemoryRouter>
        <InboxPage />
      </MemoryRouter>
    );

    await screen.findByTestId('inbox-item-inbox-1');
    await user.click(screen.getByText('查看详情'));

    await waitFor(() => {
      expect(operationApprovalApi.markInboxRead).toHaveBeenCalledWith('inbox-1');
    });
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/approvals?request_id=req-1');
    });
  });

  it('marks all items as read', async () => {
    const user = userEvent.setup();
    operationApprovalApi.listInbox
      .mockResolvedValueOnce({ items: [], unread_count: 2 })
      .mockResolvedValueOnce({ items: [], unread_count: 0 });
    operationApprovalApi.markAllInboxRead.mockResolvedValue({ updated: 2, unread_count: 0 });

    render(
      <MemoryRouter>
        <InboxPage />
      </MemoryRouter>
    );

    await screen.findByTestId('inbox-mark-all-read');
    await user.click(screen.getByTestId('inbox-mark-all-read'));

    await waitFor(() => {
      expect(operationApprovalApi.markAllInboxRead).toHaveBeenCalled();
    });
  });
});
