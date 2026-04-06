import { act, renderHook, waitFor } from '@testing-library/react';

import { orgDirectoryApi } from './api';
import useOrgDirectoryManagementPage from './useOrgDirectoryManagementPage';

jest.mock('./api', () => ({
  orgDirectoryApi: {
    getTree: jest.fn(),
    listCompanies: jest.fn(),
    listDepartments: jest.fn(),
    listAudit: jest.fn(),
    rebuildFromExcel: jest.fn(),
  },
}));

const sampleTree = [
  {
    id: 'company-1',
    node_type: 'company',
    name: 'Acme',
    children: [
      {
        id: 'dept-1',
        node_type: 'department',
        name: 'QA',
        path_name: 'Acme / QA',
        children: [
          {
            id: 'person-1',
            node_type: 'person',
            name: 'Alice',
            employee_user_id: 'alice-1',
            path_name: 'Acme / QA / Alice',
            children: [],
          },
        ],
      },
    ],
  },
];

describe('useOrgDirectoryManagementPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    orgDirectoryApi.getTree.mockResolvedValue(sampleTree);
    orgDirectoryApi.listCompanies.mockResolvedValue([{ id: 'company-1', name: 'Acme' }]);
    orgDirectoryApi.listDepartments.mockResolvedValue([{ id: 'dept-1', name: 'QA' }]);
    orgDirectoryApi.listAudit
      .mockResolvedValueOnce([{ id: 1, action: 'update', created_at_ms: 1710000000000 }])
      .mockResolvedValueOnce([{ id: 2, action: 'rebuild', created_at_ms: 1710000001000 }]);
    orgDirectoryApi.rebuildFromExcel.mockResolvedValue({});
  });

  it('loads org data on mount and exposes derived overview state', async () => {
    const { result } = renderHook(() => useOrgDirectoryManagementPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(orgDirectoryApi.getTree).toHaveBeenCalledTimes(1);
    expect(orgDirectoryApi.listCompanies).toHaveBeenCalledTimes(1);
    expect(orgDirectoryApi.listDepartments).toHaveBeenCalledTimes(1);
    expect(orgDirectoryApi.listAudit).toHaveBeenNthCalledWith(1, { limit: 200 });
    expect(orgDirectoryApi.listAudit).toHaveBeenNthCalledWith(2, { limit: 200 });
    expect(result.current.tree).toHaveLength(1);
    expect(result.current.personCount).toBe(1);
    expect(result.current.latestOverviewAudit).toEqual(
      expect.objectContaining({ id: 2, action: 'rebuild' })
    );
    expect(result.current.canTriggerRebuild).toBe(false);
  });

  it('filters search results and expands branch keys when selecting a person result', async () => {
    const { result } = renderHook(() => useOrgDirectoryManagementPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.handleSearchInputChange({
        target: { value: 'alice' },
      });
    });

    expect(result.current.searchResults).toHaveLength(1);

    act(() => {
      result.current.handleSelectSearchResult(result.current.searchResults[0]);
    });

    expect(result.current.selectedSearchKey).toBe('person:person-1');
    expect(result.current.selectedPersonNodeKey).toBe('person:person-1');
    expect(result.current.activeTab).toBe('overview');
    expect(Array.from(result.current.expandedKeys)).toEqual(['company:company-1', 'department:dept-1']);
  });

  it('validates excel uploads and rebuilds from a supported file', async () => {
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
    const { result } = renderHook(() => useOrgDirectoryManagementPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.handleExcelFileChange({
        target: {
          files: [new File(['bad'], 'org.txt', { type: 'text/plain' })],
        },
      });
    });

    expect(result.current.selectedExcelFile).toBe(null);
    expect(result.current.error).toBe('仅支持上传 .xls 或 .xlsx 格式的组织架构文件');

    orgDirectoryApi.listAudit.mockResolvedValue([{ id: 3, action: 'rebuild', created_at_ms: 1710000002000 }]);
    const excelFile = new File(['xlsx'], 'org.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    act(() => {
      result.current.handleExcelFileChange({
        target: {
          files: [excelFile],
        },
      });
    });

    expect(result.current.selectedExcelFile).toBe(excelFile);

    await act(async () => {
      await result.current.handleRebuild();
    });

    expect(orgDirectoryApi.rebuildFromExcel).toHaveBeenCalledWith(excelFile);
    expect(orgDirectoryApi.getTree).toHaveBeenCalledTimes(2);

    confirmSpy.mockRestore();
  });
});
