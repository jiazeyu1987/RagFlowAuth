import React, { useEffect, useMemo, useState } from 'react';
import { auditApi } from '../features/audit/api';
import { orgDirectoryApi } from '../features/orgDirectory/api';

const MOBILE_BREAKPOINT = 768;

const parseDateTimeLocalToMs = (value) => {
  if (!value) return null;
  const ms = Date.parse(value);
  return Number.isFinite(ms) ? ms : null;
};

const formatMs = (ms) => {
  if (!ms) return '';
  try {
    return new Date(ms).toLocaleString();
  } catch {
    return String(ms);
  }
};

const ACTION_LABELS = {
  auth_login: '登录',
  auth_logout: '退出登录',
  document_preview: '查看/预览文档',
  document_upload: '上传文档',
  document_download: '下载文档',
  document_delete: '删除文档',
  patent_kb_add: '专利添加到本地专利',
  patent_kb_add_all: '专利批量添加到本地专利',
  patent_item_delete: '删除专利条目',
  patent_session_delete: '删除专利会话',
  paper_kb_add: '论文添加到本地论文',
  paper_kb_add_all: '论文批量添加到本地论文',
  paper_item_delete: '删除论文条目',
  paper_session_delete: '删除论文会话',
  datasets_create: '新建知识库',
  datasets_update: '修改知识库',
  datasets_delete: '删除知识库',
  overwrite: '覆盖入库',
};

const SOURCE_LABELS = {
  auth: '认证',
  knowledge: '本地知识库',
  ragflow: 'RAGFlow',
  patent_download: '专利下载',
  paper_download: '论文下载',
  patent: '专利',
  paper: '论文',
};

const actionLabel = (value) => ACTION_LABELS[String(value || '').trim()] || String(value || '');
const sourceLabel = (value) => SOURCE_LABELS[String(value || '').trim()] || String(value || '');

const ACTION_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'auth_login', label: '登录' },
  { value: 'auth_logout', label: '退出登录' },
  { value: 'document_preview', label: '查看/预览文档' },
  { value: 'document_upload', label: '上传文档' },
  { value: 'document_download', label: '下载文档' },
  { value: 'document_delete', label: '删除文档' },
  { value: 'patent_kb_add', label: '专利添加到本地专利' },
  { value: 'patent_kb_add_all', label: '专利批量添加到本地专利' },
  { value: 'patent_item_delete', label: '删除专利条目' },
  { value: 'patent_session_delete', label: '删除专利会话' },
  { value: 'paper_kb_add', label: '论文添加到本地论文' },
  { value: 'paper_kb_add_all', label: '论文批量添加到本地论文' },
  { value: 'paper_item_delete', label: '删除论文条目' },
  { value: 'paper_session_delete', label: '删除论文会话' },
  { value: 'datasets_create', label: '新建知识库' },
  { value: 'datasets_update', label: '修改知识库' },
  { value: 'datasets_delete', label: '删除知识库' },
  { value: 'overwrite', label: '覆盖入库' },
];

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

const AuditLogs = () => {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [companies, setCompanies] = useState([]);
  const [departments, setDepartments] = useState([]);

  const [filters, setFilters] = useState({
    action: '',
    company_id: '',
    department_id: '',
    username: '',
    from: '',
    to: '',
    limit: 200,
    offset: 0,
  });

  const [result, setResult] = useState({ total: 0, items: [] });

  const loadDirectory = async () => {
    const [c, d] = await Promise.all([orgDirectoryApi.listCompanies(), orgDirectoryApi.listDepartments()]);
    setCompanies(Array.isArray(c) ? c : []);
    setDepartments(Array.isArray(d) ? d : []);
  };

  const loadLogs = async (nextFilters) => {
    const f = nextFilters || filters;
    setLoading(true);
    setError(null);
    try {
      const params = {
        limit: f.limit || 200,
        offset: f.offset || 0,
      };
      if (f.action) params.action = f.action;
      if (f.username) params.username = f.username;
      if (f.company_id) params.company_id = f.company_id;
      if (f.department_id) params.department_id = f.department_id;

      const fromMs = parseDateTimeLocalToMs(f.from);
      const toMs = parseDateTimeLocalToMs(f.to);
      if (fromMs != null) params.from_ms = String(fromMs);
      if (toMs != null) params.to_ms = String(toMs);

      const data = await auditApi.listEvents(params);
      setResult({
        total: data?.total || 0,
        items: Array.isArray(data?.items) ? data.items : [],
      });
    } catch (e) {
      setError(e.message || String(e));
      setResult({ total: 0, items: [] });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    (async () => {
      try {
        await loadDirectory();
      } catch {
        // best effort
      }
      await loadLogs(filters);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const rows = useMemo(() => result.items || [], [result.items]);
  const visibleDepartments = useMemo(() => {
    const companyId = filters.company_id ? Number(filters.company_id) : null;
    if (companyId == null) return departments;
    return departments.filter((department) => department.company_id == null || department.company_id === companyId);
  }, [departments, filters.company_id]);

  const onApply = async () => {
    const next = { ...filters, offset: 0 };
    setFilters(next);
    await loadLogs(next);
  };

  const onPrev = async () => {
    const nextOffset = Math.max(0, (filters.offset || 0) - (filters.limit || 200));
    const next = { ...filters, offset: nextOffset };
    setFilters(next);
    await loadLogs(next);
  };

  const onNext = async () => {
    const nextOffset = (filters.offset || 0) + (filters.limit || 200);
    const next = { ...filters, offset: nextOffset };
    setFilters(next);
    await loadLogs(next);
  };

  return (
    <div data-testid="audit-logs-page" style={{ padding: isMobile ? '0 0 12px' : 0 }}>
      <h2 style={{ margin: '0 0 12px 0' }}>操作日志</h2>

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
              onChange={(e) => setFilters((s) => ({ ...s, action: e.target.value }))}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-action"
            >
              {ACTION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>公司</div>
            <select
              value={filters.company_id}
              onChange={(e) => setFilters((s) => ({ ...s, company_id: e.target.value }))}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-company"
            >
              <option value="">全部</option>
              {companies.map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>部门</div>
            <select
              value={filters.department_id}
              onChange={(e) => setFilters((s) => ({ ...s, department_id: e.target.value }))}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-department"
            >
              <option value="">全部</option>
              {visibleDepartments.map((d) => (
                <option key={d.id} value={String(d.id)}>
                  {d.path_name || d.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>账号</div>
            <input
              value={filters.username}
              onChange={(e) => setFilters((s) => ({ ...s, username: e.target.value }))}
              placeholder="用户名精确匹配"
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-username"
            />
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>开始时间</div>
            <input
              type="datetime-local"
              value={filters.from}
              onChange={(e) => setFilters((s) => ({ ...s, from: e.target.value }))}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-from"
            />
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>结束时间</div>
            <input
              type="datetime-local"
              value={filters.to}
              onChange={(e) => setFilters((s) => ({ ...s, to: e.target.value }))}
              style={{ width: '100%', padding: '8px', border: '1px solid #d1d5db', borderRadius: 6 }}
              data-testid="audit-filter-to"
            />
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: isMobile ? 'stretch' : 'center', flexDirection: isMobile ? 'column' : 'row', gap: 10, marginTop: 10 }}>
          <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>
            总条数: <span data-testid="audit-total" style={{ fontWeight: 700, color: '#111827' }}>{result.total}</span>
          </div>
          <div style={{ display: 'flex', gap: 8, flexDirection: isMobile ? 'column' : 'row', width: isMobile ? '100%' : 'auto' }}>
            <button
              type="button"
              onClick={onApply}
              disabled={loading}
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
              onClick={onPrev}
              disabled={loading || (filters.offset || 0) <= 0}
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
              onClick={onNext}
              disabled={loading || (filters.offset || 0) + rows.length >= result.total}
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

      {error && <div style={{ color: '#ef4444', marginBottom: 12 }}>错误：{error}</div>}

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
          <table style={{ ...tableStyle, minWidth: isMobile ? '900px' : '100%' }} data-testid="audit-table">
            <thead>
              <tr>
                <th style={thStyle}>时间</th>
                <th style={thStyle}>类型</th>
                <th style={thStyle}>账号</th>
                <th style={thStyle}>公司</th>
                <th style={thStyle}>部门</th>
                <th style={thStyle}>来源</th>
                <th style={thStyle}>知识库</th>
                <th style={thStyle}>文件</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td style={tdStyle} colSpan={8}>加载中...</td>
                </tr>
              )}
              {!loading && rows.length === 0 && (
                <tr>
                  <td style={tdStyle} colSpan={8}>暂无日志</td>
                </tr>
              )}
              {!loading && rows.map((r) => (
                <tr key={r.id}>
                  <td style={tdStyle}>{formatMs(r.created_at_ms)}</td>
                  <td style={tdStyle}>{actionLabel(r.action)}</td>
                  <td style={tdStyle}>{r.full_name || r.username || r.actor}</td>
                  <td style={tdStyle}>{r.company_name || (r.company_id != null ? String(r.company_id) : '')}</td>
                  <td style={tdStyle}>{r.department_name || (r.department_id != null ? String(r.department_id) : '')}</td>
                  <td style={tdStyle}>{sourceLabel(r.source)}</td>
                  <td style={tdStyle}>{r.kb_name || r.kb_id || ''}</td>
                  <td style={tdStyle}>
                    <div style={{ fontWeight: 600 }}>{r.filename || ''}</div>
                    <div style={{ color: '#6b7280', fontSize: '0.8rem' }}>{r.doc_id || ''}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AuditLogs;
