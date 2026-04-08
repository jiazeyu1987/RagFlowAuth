import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AuditLogs from './AuditLogs';
import useAuditLogsPage from '../features/audit/useAuditLogsPage';

jest.mock('../features/audit/useAuditLogsPage', () => jest.fn());

describe('AuditLogs', () => {
  beforeEach(() => {
    useAuditLogsPage.mockReturnValue({
      loading: false,
      error: '',
      companies: [{ id: 1, name: 'Company A' }],
      departments: [{ id: 10, company_id: 1, name: 'Dept A', path_name: 'Company A / Dept A' }],
      filters: {
        action: '',
        company_id: '',
        department_id: '',
        username: '',
        from: '',
        to: '',
        limit: 20,
        offset: 0,
      },
      result: {
        total: 4,
        items: [
          {
            id: 'event-1',
            created_at_ms: 1712203200000,
            action: 'document_download',
            username: 'alice',
            company_name: 'Company A',
            department_name: 'Dept A',
            source: 'knowledge',
            kb_name: 'KB-1',
            filename: 'spec.pdf',
            doc_id: 'doc-1',
          },
          {
            id: 'event-2',
            created_at_ms: 1712206800000,
            action: 'notification_event_rule_upsert',
            username: 'bob',
            company_name: 'Company A',
            department_name: 'Dept A',
            source: 'RAGFlow',
            kb_name: '',
            filename: '',
            doc_id: '',
          },
          {
            id: 'event-3',
            created_at_ms: 1712210400000,
            action: 'notification_channel_recipient_map_rebuild',
            username: 'carol',
            company_name: 'Company A',
            department_name: 'Dept A',
            source: 'notification',
            kb_name: '',
            filename: '',
            doc_id: '',
          },
          {
            id: 'event-4',
            created_at_ms: 1712214000000,
            action: 'notification_channel_upsert',
            username: 'dave',
            company_name: 'Company A',
            department_name: 'Dept A',
            source: 'maintenance',
            kb_name: '',
            filename: '',
            doc_id: '',
          },
        ],
      },
      rows: [
        {
          id: 'event-1',
          created_at_ms: 1712203200000,
          action: 'document_download',
          username: 'alice',
          company_name: 'Company A',
          department_name: 'Dept A',
          source: 'knowledge',
          kb_name: 'KB-1',
          filename: 'spec.pdf',
          doc_id: 'doc-1',
        },
        {
          id: 'event-2',
          created_at_ms: 1712206800000,
          action: 'notification_event_rule_upsert',
          username: 'bob',
          company_name: 'Company A',
          department_name: 'Dept A',
          source: 'RAGFlow',
          kb_name: '',
          filename: '',
          doc_id: '',
        },
        {
          id: 'event-3',
          created_at_ms: 1712210400000,
          action: 'notification_channel_recipient_map_rebuild',
          username: 'carol',
          company_name: 'Company A',
          department_name: 'Dept A',
          source: 'notification',
          kb_name: '',
          filename: '',
          doc_id: '',
        },
        {
          id: 'event-4',
          created_at_ms: 1712214000000,
          action: 'notification_channel_upsert',
          username: 'dave',
          company_name: 'Company A',
          department_name: 'Dept A',
          source: 'maintenance',
          kb_name: '',
          filename: '',
          doc_id: '',
        },
      ],
      visibleDepartments: [
        { id: 10, company_id: 1, name: 'Dept A', path_name: 'Company A / Dept A' },
      ],
      canGoPrev: true,
      canGoNext: true,
      updateFilter: jest.fn(),
      applyFilters: jest.fn(),
      goPrev: jest.fn(),
      goNext: jest.fn(),
    });
  });

  it('renders mapped audit source and action labels and dispatches hook actions', async () => {
    const user = userEvent.setup();

    render(<AuditLogs />);

    expect(screen.getByTestId('audit-total')).toHaveTextContent('4');
    expect(screen.getByTestId('audit-row-event-1')).toBeInTheDocument();
    expect(screen.getByTestId('audit-row-event-2')).toBeInTheDocument();
    expect(screen.getByTestId('audit-row-event-3')).toBeInTheDocument();
    expect(screen.getByTestId('audit-row-event-4')).toBeInTheDocument();

    expect(within(screen.getByTestId('audit-row-event-2')).getByText('新增/更新通知事件规则')).toBeInTheDocument();
    expect(within(screen.getByTestId('audit-row-event-2')).getByText('系统')).toBeInTheDocument();
    expect(
      within(screen.getByTestId('audit-row-event-3')).getByText('重建通知通道收件人映射')
    ).toBeInTheDocument();
    expect(within(screen.getByTestId('audit-row-event-3')).getByText('通知')).toBeInTheDocument();
    expect(within(screen.getByTestId('audit-row-event-4')).getByText('新增/更新通知通道')).toBeInTheDocument();
    expect(within(screen.getByTestId('audit-row-event-4')).getByText('维护')).toBeInTheDocument();

    await user.click(screen.getByTestId('audit-apply'));
    expect(useAuditLogsPage.mock.results[0].value.applyFilters).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId('audit-prev'));
    expect(useAuditLogsPage.mock.results[0].value.goPrev).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId('audit-next'));
    expect(useAuditLogsPage.mock.results[0].value.goNext).toHaveBeenCalledTimes(1);
  });
});
