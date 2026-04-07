import { act, renderHook, waitFor } from '@testing-library/react';

import { notificationApi } from '../notification/api';
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

jest.mock('../notification/api', () => ({
  notificationApi: {
    listChannels: jest.fn(),
    rebuildDingtalkRecipientMap: jest.fn(),
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
    notificationApi.listChannels.mockResolvedValue([
      { channel_id: 'ding-main', channel_type: 'dingtalk', name: 'Main DingTalk' },
    ]);
    notificationApi.rebuildDingtalkRecipientMap.mockResolvedValue({
      channel_id: 'ding-main',
      org_user_count: 3,
      directory_entry_count: 3,
      alias_entry_count: 0,
      invalid_org_user_count: 0,
      invalid_org_users: [],
    });
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
    expect(result.current.latestOverviewAudit).toEqual(expect.objectContaining({ id: 2, action: 'rebuild' }));
    expect(result.current.canTriggerRebuild).toBe(false);
  });

  it('filters search results and expands branch keys when selecting a person result', async () => {
    const { result } = renderHook(() => useOrgDirectoryManagementPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.handleSearchInputChange({ target: { value: 'alice' } });
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

  it('runs org rebuild and dingtalk recipient map rebuild as two explicit calls', async () => {
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
    const { result } = renderHook(() => useOrgDirectoryManagementPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    const excelFile = new File(['xlsx'], 'org.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    act(() => {
      result.current.handleExcelFileChange({ target: { files: [excelFile] } });
    });

    await act(async () => {
      await result.current.handleRebuild();
    });

    expect(orgDirectoryApi.rebuildFromExcel).toHaveBeenCalledWith(excelFile);
    expect(notificationApi.listChannels).toHaveBeenCalledWith(false);
    expect(notificationApi.rebuildDingtalkRecipientMap).toHaveBeenCalledWith('ding-main');
    expect(result.current.notice).toContain('钉钉 UserID 目录已重建');
    expect(result.current.notice).toContain('手工别名已清空');
    expect(result.current.recipientMapRebuildSummary).toEqual(
      expect.objectContaining({
        channel_id: 'ding-main',
        org_user_count: 3,
        directory_entry_count: 3,
        alias_entry_count: 0,
        invalid_org_user_count: 0,
      })
    );
    expect(orgDirectoryApi.getTree).toHaveBeenCalledTimes(2);

    confirmSpy.mockRestore();
  });

  it('shows partial success when dingtalk rebuild fails after org rebuild succeeds', async () => {
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
    notificationApi.rebuildDingtalkRecipientMap.mockRejectedValue(new Error('invalidClientIdOrSecret'));
    const { result } = renderHook(() => useOrgDirectoryManagementPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    const excelFile = new File(['xlsx'], 'org.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    act(() => {
      result.current.handleExcelFileChange({ target: { files: [excelFile] } });
    });

    await act(async () => {
      await result.current.handleRebuild();
    });

    expect(orgDirectoryApi.rebuildFromExcel).toHaveBeenCalledWith(excelFile);
    expect(notificationApi.rebuildDingtalkRecipientMap).toHaveBeenCalledWith('ding-main');
    expect(result.current.error).toBe('组织架构重建成功，但钉钉 UserID 目录重建失败：invalidClientIdOrSecret');
    expect(result.current.notice).toBe(null);
    expect(result.current.recipientMapRebuildSummary).toBe(null);

    confirmSpy.mockRestore();
  });

  it('validates excel uploads before rebuild', async () => {
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
  });
});
