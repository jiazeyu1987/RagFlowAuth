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
      exporting: false,
      error: '',
      companies: [{ id: 1, name: 'Company A' }],
      departments: [{ id: 10, company_id: 1, name: 'Dept A', path_name: 'Company A / Dept A' }],
      filters: {
        action: '',
        source: '',
        event_type: '',
        request_id: '',
        resource_id: '',
        company_id: '',
        department_id: '',
        username: '',
        from: '',
        to: '',
        limit: 20,
        offset: 0,
      },
      result: {
        total: 5,
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
          {
            id: 'event-3',
            created_at_ms: 1712210400000,
            action: 'notification_event_rule_upsert',
            username: 'carol',
            company_name: 'Company A',
            department_name: 'Dept A',
            source: 'RAGFlow',
            kb_name: '',
            filename: '',
            doc_id: '',
          },
          {
            id: 'event-4',
            created_at_ms: 1712214000000,
            action: 'global_search_execute',
            username: 'dave',
            company_name: 'Company A',
            department_name: 'Dept A',
            source: 'global_search',
            filename: 'search-hit.pdf',
            doc_id: 'doc-search',
            request_id: 'rid-search',
            before: { question: '设备点检规范', dataset_ids: ['KB-1'] },
            after: { returned_chunks: 2 },
            evidence_refs: [{ resource_id: 'doc-search', filename: 'search-hit.pdf', kb_name: 'KB-1' }],
          },
          {
            id: 'event-5',
            created_at_ms: 1712217600000,
            action: 'smart_chat_completion',
            username: 'erin',
            company_name: 'Company A',
            department_name: 'Dept A',
            source: 'smart_chat',
            filename: 'citation-spec.pdf',
            doc_id: 'doc-chat',
            resource_id: 'session-1',
            before: { question: '这份记录为什么要复核？' },
            meta: { session_id: 'session-1', source_count: 1 },
            evidence_refs: [{ resource_id: 'doc-chat', filename: 'citation-spec.pdf', kb_name: 'KB-2' }],
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
        {
          id: 'event-3',
          created_at_ms: 1712210400000,
          action: 'notification_event_rule_upsert',
          username: 'carol',
          company_name: 'Company A',
          department_name: 'Dept A',
          source: 'RAGFlow',
          kb_name: '',
          filename: '',
          doc_id: '',
        },
        {
          id: 'event-4',
          created_at_ms: 1712214000000,
          action: 'global_search_execute',
          username: 'dave',
          company_name: 'Company A',
          department_name: 'Dept A',
          source: 'global_search',
          filename: 'search-hit.pdf',
          doc_id: 'doc-search',
          request_id: 'rid-search',
          before: { question: '设备点检规范', dataset_ids: ['KB-1'] },
          after: { returned_chunks: 2 },
          evidence_refs: [{ resource_id: 'doc-search', filename: 'search-hit.pdf', kb_name: 'KB-1' }],
        },
        {
          id: 'event-5',
          created_at_ms: 1712217600000,
          action: 'smart_chat_completion',
          username: 'erin',
          company_name: 'Company A',
          department_name: 'Dept A',
          source: 'smart_chat',
          filename: 'citation-spec.pdf',
          doc_id: 'doc-chat',
          resource_id: 'session-1',
          before: { question: '这份记录为什么要复核？' },
          meta: { session_id: 'session-1', source_count: 1 },
          evidence_refs: [{ resource_id: 'doc-chat', filename: 'citation-spec.pdf', kb_name: 'KB-2' }],
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
      exportEvidencePackage: jest.fn(),
    });
  });

  it('renders mapped audit source and action labels and dispatches hook actions', async () => {
    const user = userEvent.setup();

    render(<AuditLogs />);

    expect(screen.getByTestId('audit-total')).toHaveTextContent('5');
    expect(screen.getByTestId('audit-row-event-1')).toBeInTheDocument();
    expect(screen.getByTestId('audit-row-event-2')).toBeInTheDocument();
    expect(screen.getByTestId('audit-row-event-3')).toBeInTheDocument();
    expect(screen.getByTestId('audit-row-event-4')).toBeInTheDocument();
    expect(screen.getByTestId('audit-row-event-5')).toBeInTheDocument();

    expect(within(screen.getByTestId('audit-row-event-3')).getByText('新增/更新通知事件规则')).toBeInTheDocument();
    expect(within(screen.getByTestId('audit-row-event-3')).getByText('系统')).toBeInTheDocument();
    expect(within(screen.getByTestId('audit-row-event-4')).getAllByText('全局搜索')).toHaveLength(2);
    expect(within(screen.getByTestId('audit-row-event-4')).getByText('查询：设备点检规范')).toBeInTheDocument();
    expect(within(screen.getByTestId('audit-row-event-5')).getAllByText('智能对话')).toHaveLength(2);
    expect(within(screen.getByTestId('audit-row-event-5')).getByText('问题：这份记录为什么要复核？')).toBeInTheDocument();

    await user.click(screen.getByTestId('audit-apply'));
    expect(useAuditLogsPage.mock.results[0].value.applyFilters).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId('audit-export'));
    expect(useAuditLogsPage.mock.results[0].value.exportEvidencePackage).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId('audit-prev'));
    expect(useAuditLogsPage.mock.results[0].value.goPrev).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId('audit-next'));
    expect(useAuditLogsPage.mock.results[0].value.goNext).toHaveBeenCalledTimes(1);
  });

  it('renders quality system config audit labels', () => {
    useAuditLogsPage.mockReturnValue({
      loading: false,
      exporting: false,
      error: '',
      companies: [],
      departments: [],
      filters: {
        action: '',
        source: '',
        event_type: '',
        request_id: '',
        resource_id: '',
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
            id: 'event-quality-1',
            created_at_ms: 1712220000000,
            action: 'quality_system_position_assignments_update',
            username: 'admin1',
            company_name: '',
            department_name: '',
            source: 'quality_system_config',
            resource_id: 'QA',
            before: { assigned_users: [] },
            after: { assigned_users: [{ user_id: 'u-1' }] },
          },
        ],
      },
      rows: [
        {
          id: 'event-quality-1',
          created_at_ms: 1712220000000,
          action: 'quality_system_position_assignments_update',
          username: 'admin1',
          company_name: '',
          department_name: '',
          source: 'quality_system_config',
          resource_id: 'QA',
          before: { assigned_users: [] },
          after: { assigned_users: [{ user_id: 'u-1' }] },
        },
      ],
      visibleDepartments: [],
      canGoPrev: false,
      canGoNext: false,
      updateFilter: jest.fn(),
      applyFilters: jest.fn(),
      goPrev: jest.fn(),
      goNext: jest.fn(),
      exportEvidencePackage: jest.fn(),
    });

    render(<AuditLogs />);

    expect(screen.getByTestId('audit-row-event-quality-1')).toBeInTheDocument();
    expect(
      within(screen.getByTestId('audit-row-event-quality-1')).getByText('更新体系岗位分配')
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId('audit-row-event-quality-1')).getByText('体系配置')
    ).toBeInTheDocument();
  });
});
