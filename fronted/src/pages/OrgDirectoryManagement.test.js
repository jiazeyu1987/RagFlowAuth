import React from 'react';
import { render, screen } from '@testing-library/react';

import OrgDirectoryManagement from './OrgDirectoryManagement';
import useOrgDirectoryManagementPage from '../features/orgDirectory/useOrgDirectoryManagementPage';

jest.mock('../features/orgDirectory/useOrgDirectoryManagementPage', () => jest.fn());

const buildPageState = (overrides = {}) => ({
  excelFileInputRef: { current: null },
  isMobile: false,
  activeTab: 'overview',
  setActiveTab: jest.fn(),
  loading: false,
  rebuilding: false,
  error: '',
  notice: '',
  auditError: '',
  tree: [],
  companies: [],
  departments: [],
  auditLogs: [],
  latestOverviewAudit: null,
  auditFilter: { entity_type: '', action: '', limit: 200 },
  setAuditFilter: jest.fn(),
  searchTerm: '',
  selectedSearchKey: null,
  selectedPersonNodeKey: null,
  selectedPersonEntry: null,
  highlightedNodeKey: null,
  expandedKeys: new Set(),
  selectedExcelFile: null,
  recipientMapRebuildSummary: null,
  personColumnCount: 4,
  personCount: 0,
  isMissingPersonNodes: false,
  canTriggerRebuild: false,
  trimmedSearchTerm: '',
  totalSearchMatches: 0,
  searchResults: [],
  registerNodeRef: jest.fn(),
  refreshAudit: jest.fn(),
  handleSearchInputChange: jest.fn(),
  handleClearSearch: jest.fn(),
  handleSelectSearchResult: jest.fn(),
  handleSelectPerson: jest.fn(),
  handleToggleBranch: jest.fn(),
  handleChooseExcelFile: jest.fn(),
  handleClearExcelFile: jest.fn(),
  handleExcelFileChange: jest.fn(),
  handleRebuild: jest.fn(),
  ...overrides,
});

describe('OrgDirectoryManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useOrgDirectoryManagementPage.mockReturnValue(buildPageState());
  });

  it('renders the overview shell from the page hook contract', () => {
    useOrgDirectoryManagementPage.mockReturnValue(
      buildPageState({
        error: '组织架构重建成功，但钉钉 UserID 目录重建失败：invalidClientIdOrSecret',
        notice: '组织架构重建成功，钉钉 UserID 目录已重建：组织人员 3 人，目录写入 3 条，手工别名已清空。',
        recipientMapRebuildSummary: {
          channel_id: 'ding-main',
          org_user_count: 3,
          directory_entry_count: 3,
          alias_entry_count: 0,
          invalid_org_user_count: 1,
          invalid_org_users: [
            { employee_user_id: 'ding-bob', full_name: 'Bob', reason: 'employee_user_id_duplicate' },
          ],
        },
      })
    );

    render(<OrgDirectoryManagement />);

    expect(screen.getByTestId('org-page')).toBeInTheDocument();
    expect(screen.getByTestId('org-error')).toHaveTextContent('钉钉 UserID 目录重建失败');
    expect(screen.getByTestId('org-notice')).toHaveTextContent('钉钉 UserID 目录已重建');
    expect(screen.getByTestId('org-dingtalk-rebuild-summary')).toHaveTextContent('ding-main');
    expect(screen.getByTestId('org-dingtalk-invalid-ding-bob')).toHaveTextContent('Bob');
    expect(screen.getByTestId('org-tree')).toBeInTheDocument();
    expect(screen.getByTestId('org-search-input')).toBeInTheDocument();
    expect(screen.getByTestId('org-excel-file-name')).toBeInTheDocument();
  });

  it('renders the audit panel from the page hook contract', () => {
    useOrgDirectoryManagementPage.mockReturnValue(
      buildPageState({
        activeTab: 'audit',
        auditLogs: [
          {
            id: 11,
            entity_type: 'company',
            action: 'update',
            created_at_ms: 1710000000000,
            actor_username: 'alice',
          },
        ],
      })
    );

    render(<OrgDirectoryManagement />);

    expect(screen.getByTestId('org-audit-refresh')).toBeInTheDocument();
    expect(screen.getByTestId('org-audit-row-11')).toBeInTheDocument();
  });
});
