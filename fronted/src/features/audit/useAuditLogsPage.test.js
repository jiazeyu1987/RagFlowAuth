import { act, renderHook, waitFor } from '@testing-library/react';
import { auditApi } from './api';
import useAuditLogsPage from './useAuditLogsPage';
import { orgDirectoryApi } from '../orgDirectory/api';

jest.mock('./api', () => ({
  __esModule: true,
  auditApi: {
    listEvents: jest.fn(),
  },
}));

jest.mock('../orgDirectory/api', () => ({
  __esModule: true,
  orgDirectoryApi: {
    listCompanies: jest.fn(),
    listDepartments: jest.fn(),
  },
}));

describe('useAuditLogsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    orgDirectoryApi.listCompanies.mockResolvedValue([
      { id: 1, name: 'Company A' },
      { id: 2, name: 'Company B' },
    ]);
    orgDirectoryApi.listDepartments.mockResolvedValue([
      { id: 10, company_id: 1, name: 'Dept A', path_name: 'Company A / Dept A' },
      { id: 20, company_id: 2, name: 'Dept B', path_name: 'Company B / Dept B' },
      { id: 30, company_id: null, name: 'Shared', path_name: 'Shared' },
    ]);
    auditApi.listEvents.mockResolvedValue({
      total: 3,
      items: [
        {
          id: 'event-1',
          action: 'document_download',
          username: 'alice',
        },
      ],
    });
  });

  it('loads directory data and audit rows into stable hook state', async () => {
    const { result } = renderHook(() => useAuditLogsPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(orgDirectoryApi.listCompanies).toHaveBeenCalledTimes(1);
    expect(orgDirectoryApi.listDepartments).toHaveBeenCalledTimes(1);
    expect(auditApi.listEvents).toHaveBeenCalledWith({
      limit: 200,
      offset: 0,
    });
    expect(result.current.companies).toHaveLength(2);
    expect(result.current.rows).toEqual([
      expect.objectContaining({
        id: 'event-1',
      }),
    ]);

    act(() => {
      result.current.updateFilter('company_id', '1');
    });

    expect(result.current.visibleDepartments.map((item) => item.id)).toEqual([10, 30]);
  });

  it('applies filters and paginates through audit events via the feature api', async () => {
    const { result } = renderHook(() => useAuditLogsPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      result.current.updateFilter('action', 'document_download');
      result.current.updateFilter('company_id', '1');
      result.current.updateFilter('department_id', '10');
      result.current.updateFilter('username', 'alice');
      result.current.updateFilter('from', '2026-04-01T09:00');
      result.current.updateFilter('to', '2026-04-02T10:30');
      result.current.updateFilter('limit', 20);
    });

    await act(async () => {
      await result.current.applyFilters();
    });

    expect(auditApi.listEvents).toHaveBeenLastCalledWith({
      action: 'document_download',
      company_id: '1',
      department_id: '10',
      from_ms: String(Date.parse('2026-04-01T09:00')),
      limit: 20,
      offset: 0,
      to_ms: String(Date.parse('2026-04-02T10:30')),
      username: 'alice',
    });

    auditApi.listEvents.mockResolvedValueOnce({
      total: 41,
      items: new Array(20).fill(null).map((_, index) => ({ id: `next-${index}` })),
    });

    await act(async () => {
      await result.current.goNext();
    });

    expect(auditApi.listEvents).toHaveBeenLastCalledWith(
      expect.objectContaining({
        limit: 20,
        offset: 20,
      })
    );

    auditApi.listEvents.mockResolvedValueOnce({
      total: 41,
      items: [{ id: 'prev-1' }],
    });

    await act(async () => {
      await result.current.goPrev();
    });

    expect(auditApi.listEvents).toHaveBeenLastCalledWith(
      expect.objectContaining({
        limit: 20,
        offset: 0,
      })
    );
  });
});
