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
        error: '加载失败',
      })
    );

    render(<OrgDirectoryManagement />);

    expect(screen.getByTestId('org-page')).toBeInTheDocument();
    expect(screen.getByTestId('org-error')).toHaveTextContent('加载失败');
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
