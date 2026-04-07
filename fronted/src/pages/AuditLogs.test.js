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
        total: 2,
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
            action: 'operation_approval_execute_failed',
            username: 'bob',
            company_name: 'Company A',
            department_name: 'Dept A',
            source: 'operation_approval',
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
          action: 'operation_approval_execute_failed',
          username: 'bob',
          company_name: 'Company A',
          department_name: 'Dept A',
          source: 'operation_approval',
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

  it('renders audit rows and dispatches hook actions from the page controls', async () => {
    const user = userEvent.setup();

    render(<AuditLogs />);

    expect(screen.getByTestId('audit-total')).toHaveTextContent('2');
    expect(screen.getByTestId('audit-row-event-1')).toBeInTheDocument();
    expect(screen.getByTestId('audit-row-event-2')).toBeInTheDocument();
    expect(within(screen.getByTestId('audit-row-event-1')).getByText('下载文档')).toBeInTheDocument();
    expect(within(screen.getByTestId('audit-row-event-1')).getByText('本地知识库')).toBeInTheDocument();
    expect(
      within(screen.getByTestId('audit-row-event-2')).getByText('操作审批执行失败')
    ).toBeInTheDocument();
    expect(within(screen.getByTestId('audit-row-event-2')).getByText('操作审批')).toBeInTheDocument();
    expect(screen.getByRole('option', { name: '导出审计证据包' })).toBeInTheDocument();

    await user.click(screen.getByTestId('audit-apply'));
    expect(useAuditLogsPage.mock.results[0].value.applyFilters).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId('audit-prev'));
    expect(useAuditLogsPage.mock.results[0].value.goPrev).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId('audit-next'));
    expect(useAuditLogsPage.mock.results[0].value.goNext).toHaveBeenCalledTimes(1);
  });
});
