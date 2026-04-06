import React from 'react';
import { render, screen } from '@testing-library/react';
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
        total: 1,
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

    expect(screen.getByTestId('audit-total')).toHaveTextContent('1');
    expect(screen.getByTestId('audit-row-event-1')).toBeInTheDocument();

    await user.click(screen.getByTestId('audit-apply'));
    expect(useAuditLogsPage.mock.results[0].value.applyFilters).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId('audit-prev'));
    expect(useAuditLogsPage.mock.results[0].value.goPrev).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId('audit-next'));
    expect(useAuditLogsPage.mock.results[0].value.goNext).toHaveBeenCalledTimes(1);
  });
});
