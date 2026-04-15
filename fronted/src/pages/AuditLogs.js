import React, { useEffect, useState } from 'react';
import useAuditLogsPage from '../features/audit/useAuditLogsPage';

const MOBILE_BREAKPOINT = 768;

const ACTION_LABELS = {
  audit_evidence_export: '导出审计证据包',
  auth_login: '登录',
  auth_logout: '退出登录',
  backup_cancel: '取消备份',
  backup_restore_drill_create: '新建恢复演练',
  backup_restore_drill_list: '查询恢复演练',
  backup_run: '执行备份',
  compliance_review_package_export: '导出审查资料包',
  credential_lockout: '凭证锁定',
  data_security_settings_update: '更新数据安全设置',
  datasets_create: '新建知识库',
  datasets_update: '修改知识库',
  datasets_delete: '删除知识库',
  document_approve: '文档审核通过',
  document_reject: '文档审核驳回',
  document_retire: '文档归档',
  document_preview: '查看/预览文档',
  document_upload: '上传文档',
  document_download: '下载文档',
  document_delete: '删除文档',
  electronic_signature_authorization_update: '更新电子签名授权',
  environment_qualification_record: '登记环境资质记录',
  global_search_execute: '全局搜索',
  operation_approval_submit: '提交操作审批',
  operation_approval_approve: '通过操作审批',
  operation_approval_reject: '驳回操作审批',
  operation_approval_withdraw: '撤回操作审批',
  operation_approval_execute_start: '开始执行操作审批',
  operation_approval_execute_success: '操作审批执行成功',
  operation_approval_execute_failed: '操作审批执行失败',
  operator_certification_create: '新增操作员认证',
  patent_kb_add: '专利添加到本地专利库',
  patent_kb_add_all: '专利批量添加到本地专利库',
  patent_item_delete: '删除专利条目',
  patent_session_delete: '删除专利会话',
  paper_kb_add: '论文添加到本地论文库',
  paper_kb_add_all: '论文批量添加到本地论文库',
  paper_item_delete: '删除论文条目',
  paper_session_delete: '删除论文会话',
  quality_system_position_assignments_update: '更新体系岗位分配',
  quality_system_file_category_create: '新增体系文件小类',
  quality_system_file_category_deactivate: '停用体系文件小类',
  retired_document_download: '下载归档文档',
  retired_record_package_export: '导出归档记录包',
  supplier_component_upsert: '新增或更新供应商组件',
  supplier_component_version_change: '变更供应商组件版本',
  smart_chat_completion: '智能对话',
  tenant_a_event: '租户 A 事件',
  tenant_b_event: '租户 B 事件',
  training_record_create: '新增培训记录',
  training_requirement_upsert: '新增或更新培训要求',
  upload_settings_update: '更新上传设置',
  user_password_reset: '重置用户密码',
  overwrite: '覆盖入库',
};

const SOURCE_LABELS = {
  audit: '审计',
  auth: '认证',
  data_security: '数据安全',
  electronic_signature: '电子签名',
  knowledge: '本地知识库',
  knowledge_retired: '归档文档',
  operation_approval: '操作审批',
  quality_system_config: '体系配置',
  ragflow: 'RAGFlow',
  global_search: '全局搜索',
  patent_download: '专利下载',
  paper_download: '论文下载',
  patent: '专利',
  paper: '论文',
  review: '文档审核',
  supplier_qualification: '供应商资质',
  smart_chat: '智能对话',
  training_compliance: '培训合规',
  users: '用户管理',
};

const EXTRA_ACTION_LABELS = {
  notification_channel_upsert: '新增/更新通知通道',
  notification_channel_recipient_map_rebuild: '重建通知通道收件人映射',
  notification_event_rule_upsert: '新增/更新通知事件规则',
  notification_job_enqueue: '通知入队',
  notification_job_dispatch: '发送通知',
  notification_job_retry: '重试通知发送',
  notification_job_resend: '重新发送通知',
  notification_inbox_read_state_update: '更新通知已读状态',
  notification_inbox_mark_all_read: '全部标记通知为已读',
};

const EXTRA_SOURCE_LABELS = {
  ragflow: '系统',
  notification: '通知',
  maintenance: '维护',
};

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
};

const thStyle = {
  padding: '10px 12px',
  textAlign: 'left',
  borderBottom: '1px solid #e5e7eb',
  backgroundColor: '#f9fafb',
  fontSize: '0.85rem',
  color: '#374151',
};

const tdStyle = {
  padding: '10px 12px',
  borderBottom: '1px solid #e5e7eb',
  verticalAlign: 'top',
  fontSize: '0.9rem',
};

const actionLabel = (value) => {
  const normalized = String(value || '').trim();
  if (!normalized) return '';
  return (
    EXTRA_ACTION_LABELS[normalized] ||
    EXTRA_ACTION_LABELS[normalized.toLowerCase()] ||
    ACTION_LABELS[normalized] ||
    ACTION_LABELS[normalized.toLowerCase()] ||
    normalized
  );
};

const sourceLabel = (value) => {
  const normalized = String(value || '').trim();
  if (!normalized) return '';
  return (
    EXTRA_SOURCE_LABELS[normalized] ||
    EXTRA_SOURCE_LABELS[normalized.toLowerCase()] ||
    SOURCE_LABELS[normalized] ||
    SOURCE_LABELS[normalized.toLowerCase()] ||
    normalized
  );
};

const ACTION_FILTER_VALUES = [
  'auth_login',
  'auth_logout',
  'credential_lockout',
  'user_password_reset',
  'document_preview',
  'document_upload',
  'document_download',
  'document_delete',
  'document_approve',
  'document_reject',
  'document_retire',
  'datasets_create',
  'datasets_update',
  'datasets_delete',
  'upload_settings_update',
  'paper_kb_add',
  'paper_kb_add_all',
  'paper_item_delete',
  'paper_session_delete',
  'quality_system_position_assignments_update',
  'quality_system_file_category_create',
  'quality_system_file_category_deactivate',
  'patent_kb_add',
  'patent_kb_add_all',
  'patent_item_delete',
  'patent_session_delete',
  'operation_approval_submit',
  'operation_approval_approve',
  'operation_approval_reject',
  'operation_approval_withdraw',
  'operation_approval_execute_start',
  'operation_approval_execute_success',
  'operation_approval_execute_failed',
  'backup_run',
  'backup_cancel',
  'backup_restore_drill_create',
  'backup_restore_drill_list',
  'data_security_settings_update',
  'training_requirement_upsert',
  'training_record_create',
  'operator_certification_create',
  'supplier_component_upsert',
  'supplier_component_version_change',
  'environment_qualification_record',
  'electronic_signature_authorization_update',
  'global_search_execute',
  'audit_evidence_export',
  'compliance_review_package_export',
  'retired_document_download',
  'retired_record_package_export',
  'smart_chat_completion',
  'overwrite',
];

const ACTION_OPTIONS = [
  { value: '', label: '全部' },
  ...ACTION_FILTER_VALUES.map((value) => ({
    value,
    label: actionLabel(value),
  })),
];

const SOURCE_FILTER_VALUES = [
  'audit',
  'auth',
  'knowledge',
  'review',
  'global_search',
  'smart_chat',
  'operation_approval',
  'quality_system_config',
  'notification',
  'maintenance',
];

const SOURCE_OPTIONS = [
  { value: '', label: '全部' },
  ...SOURCE_FILTER_VALUES.map((value) => ({
    value,
    label: sourceLabel(value),
  })),
];

const formatMs = (value) => {
  if (!value) return '';
  try {
    return new Date(value).toLocaleString();
  } catch {
    return String(value);
  }
};

const truncateText = (value, maxChars = 48) => {
  const text = String(value || '').trim();
  if (!text) return '';
  if (text.length <= maxChars) return text;
  return `${text.slice(0, maxChars)}...`;
};

const getEvidenceRefs = (item) => (
  Array.isArray(item?.evidence_refs) ? item.evidence_refs.filter((entry) => entry && typeof entry === 'object') : []
);

const summarizeAuditContext = (item) => {
  const before = item?.before && typeof item.before === 'object' ? item.before : {};
  const after = item?.after && typeof item.after === 'object' ? item.after : {};
  const meta = item?.meta && typeof item.meta === 'object' ? item.meta : {};
  const lines = [];

  if (item?.source === 'global_search') {
    if (before.question) lines.push(`查询：${truncateText(before.question)}`);
    const datasetIds = Array.isArray(before.dataset_ids)
      ? before.dataset_ids
      : (Array.isArray(meta.dataset_ids) ? meta.dataset_ids : []);
    if (datasetIds.length) {
      lines.push(`知识库：${datasetIds.slice(0, 2).join('、')}${datasetIds.length > 2 ? ' 等' : ''}`);
    }
    const resultCount = after.returned_chunks ?? meta.result_total ?? after.total;
    if (resultCount != null) lines.push(`结果：${resultCount} 条`);
  }

  if (item?.source === 'smart_chat') {
    if (before.question) lines.push(`问题：${truncateText(before.question)}`);
    if (meta.session_id || item?.resource_id) {
      lines.push(`会话：${meta.session_id || item.resource_id}`);
    }
    const sourceCount = meta.source_count ?? getEvidenceRefs(item).length;
    lines.push(`引用：${sourceCount} 条`);
  }

  if (!lines.length) {
    if (item?.event_type) lines.push(`事件：${item.event_type}`);
    if (item?.request_id) lines.push(`请求：${truncateText(item.request_id, 32)}`);
    if (item?.resource_id) lines.push(`资源：${truncateText(item.resource_id, 32)}`);
  }

  return lines.slice(0, 3);
};

const summarizeEvidence = (item) => {
  const refs = getEvidenceRefs(item);
  if (!refs.length) return ['-'];
  const first = refs[0];
  const lines = [`${refs.length} 条引用`];
  if (first?.filename) lines.push(first.filename);
  if (first?.kb_name || first?.kb_id) lines.push(first.kb_name || first.kb_id);
  return lines.slice(0, 3);
};

const AuditLogs = () => {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const {
    loading,
    exporting,
    error,
    companies,
    filters,
    result,
    rows,
    visibleDepartments,
    canGoPrev,
    canGoNext,
    updateFilter,
    applyFilters,
    goPrev,
    goNext,
    exportEvidencePackage,
  } = useAuditLogsPage();

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div data-testid="audit-logs-page" style={{ padding: isMobile ? '0 0 12px' : 0 }}>
      <div
        style={{
          backgroundColor: 'white',
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          padding: '12px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
          marginBottom: '12px',
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? '1fr' : 'repeat(6, minmax(0, 1fr))',
            gap: '10px',
            alignItems: 'end',
          }}
        >
          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>类型</div>
            <select
              value={filters.action}
              onChange={(event) => updateFilter('action', event.target.value)}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-action"
            >
              {ACTION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>来源</div>
            <select
              value={filters.source}
              onChange={(event) => updateFilter('source', event.target.value)}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-source"
            >
              {SOURCE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>事件类型</div>
            <input
              value={filters.event_type}
              onChange={(event) => updateFilter('event_type', event.target.value)}
              placeholder="如 search / completion"
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-event-type"
            />
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>请求 ID</div>
            <input
              value={filters.request_id}
              onChange={(event) => updateFilter('request_id', event.target.value)}
              placeholder="精确匹配 request_id"
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-request-id"
            />
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>资源 ID</div>
            <input
              value={filters.resource_id}
              onChange={(event) => updateFilter('resource_id', event.target.value)}
              placeholder="精确匹配 resource_id"
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-resource-id"
            />
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>公司</div>
            <select
              value={filters.company_id}
              onChange={(event) => updateFilter('company_id', event.target.value)}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-company"
            >
              <option value="">全部</option>
              {companies.map((company) => (
                <option key={company.id} value={String(company.id)}>
                  {company.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>部门</div>
            <select
              value={filters.department_id}
              onChange={(event) => updateFilter('department_id', event.target.value)}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-department"
            >
              <option value="">全部</option>
              {visibleDepartments.map((department) => (
                <option key={department.id} value={String(department.id)}>
                  {department.path_name || department.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>账号</div>
            <input
              value={filters.username}
              onChange={(event) => updateFilter('username', event.target.value)}
              placeholder="用户名精确匹配"
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-username"
            />
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>每页条数</div>
            <select
              value={String(filters.limit)}
              onChange={(event) => updateFilter('limit', Number(event.target.value))}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-limit"
            >
              <option value="1">1</option>
              <option value="20">20</option>
              <option value="50">50</option>
              <option value="200">200</option>
            </select>
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>开始时间</div>
            <input
              type="datetime-local"
              value={filters.from}
              onChange={(event) => updateFilter('from', event.target.value)}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-from"
            />
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>结束时间</div>
            <input
              type="datetime-local"
              value={filters.to}
              onChange={(event) => updateFilter('to', event.target.value)}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-to"
            />
          </div>
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: isMobile ? 'stretch' : 'center',
            flexDirection: isMobile ? 'column' : 'row',
            gap: 10,
            marginTop: 10,
          }}
        >
          <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>
            总条数{' '}
            <span data-testid="audit-total" style={{ fontWeight: 700, color: '#111827' }}>
              {result.total}
            </span>
          </div>

          <div
            style={{
              display: 'flex',
              gap: 8,
              flexDirection: isMobile ? 'column' : 'row',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            <button
              type="button"
              onClick={applyFilters}
              disabled={loading || exporting}
              style={{
                padding: '8px 12px',
                backgroundColor: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
                opacity: loading ? 0.6 : 1,
                width: isMobile ? '100%' : 'auto',
              }}
              data-testid="audit-apply"
            >
              查询
            </button>
            <button
              type="button"
              onClick={exportEvidencePackage}
              disabled={loading || exporting}
              style={{
                padding: '8px 12px',
                backgroundColor: '#111827',
                color: 'white',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
                opacity: loading || exporting ? 0.6 : 1,
                width: isMobile ? '100%' : 'auto',
              }}
              data-testid="audit-export"
            >
              {exporting ? '导出中...' : '导出证据包'}
            </button>
            <button
              type="button"
              onClick={goPrev}
              disabled={loading || exporting || !canGoPrev}
              style={{
                padding: '8px 12px',
                backgroundColor: '#f3f4f6',
                color: '#111827',
                border: '1px solid #e5e7eb',
                borderRadius: 6,
                cursor: 'pointer',
                width: isMobile ? '100%' : 'auto',
              }}
              data-testid="audit-prev"
            >
              上一页
            </button>
            <button
              type="button"
              onClick={goNext}
              disabled={loading || exporting || !canGoNext}
              style={{
                padding: '8px 12px',
                backgroundColor: '#f3f4f6',
                color: '#111827',
                border: '1px solid #e5e7eb',
                borderRadius: 6,
                cursor: 'pointer',
                width: isMobile ? '100%' : 'auto',
              }}
              data-testid="audit-next"
            >
              下一页
            </button>
          </div>
        </div>
      </div>

      {error ? <div style={{ color: '#ef4444', marginBottom: 12 }}>错误: {error}</div> : null}

      <div
        style={{
          backgroundColor: 'white',
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          overflow: 'hidden',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
        }}
      >
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{ ...tableStyle, minWidth: isMobile ? '1200px' : '100%' }}
            data-testid="audit-table"
          >
            <thead>
              <tr>
                <th style={thStyle}>时间</th>
                <th style={thStyle}>类型</th>
                <th style={thStyle}>账号</th>
                <th style={thStyle}>公司</th>
                <th style={thStyle}>部门</th>
                <th style={thStyle}>来源</th>
                <th style={thStyle}>上下文</th>
                <th style={thStyle}>证据</th>
                <th style={thStyle}>文件</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td style={tdStyle} colSpan={9}>
                    加载中...
                  </td>
                </tr>
              ) : null}
              {!loading && rows.length === 0 ? (
                <tr>
                  <td style={tdStyle} colSpan={9}>
                    暂无日志
                  </td>
                </tr>
              ) : null}
              {!loading
                ? rows.map((item) => (
                    <tr key={item.id} data-testid={`audit-row-${item.id}`}>
                      <td style={tdStyle}>{formatMs(item.created_at_ms)}</td>
                      <td style={tdStyle}>{actionLabel(item.action)}</td>
                      <td style={tdStyle}>
                        {item.full_name || item.username || item.actor}
                      </td>
                      <td style={tdStyle}>
                        {item.company_name ||
                          (item.company_id != null ? String(item.company_id) : '')}
                      </td>
                      <td style={tdStyle}>
                        {item.department_name || (item.department_id != null ? String(item.department_id) : '')}
                      </td>
                      <td style={tdStyle}>{sourceLabel(item.source)}</td>
                      <td style={tdStyle}>
                        {summarizeAuditContext(item).map((line) => (
                          <div key={line}>{line}</div>
                        ))}
                      </td>
                      <td style={tdStyle}>
                        {summarizeEvidence(item).map((line) => (
                          <div key={line}>{line}</div>
                        ))}
                      </td>
                      <td style={tdStyle}>
                        <div style={{ fontWeight: 600 }}>{item.filename || ''}</div>
                        <div style={{ color: '#6b7280', fontSize: '0.8rem' }}>
                          {item.doc_id || ''}
                        </div>
                      </td>
                    </tr>
                  ))
                : null}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AuditLogs;
