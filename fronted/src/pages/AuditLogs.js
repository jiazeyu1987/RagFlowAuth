import React, { useEffect, useMemo, useState } from 'react';
import { auditApi } from '../features/audit/api';
import { orgDirectoryApi } from '../features/orgDirectory/api';

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
  auth_login: '\u767b\u5f55',
  auth_logout: '\u9000\u51fa\u767b\u5f55',
  auth_session_kick: '\u4f1a\u8bdd\u8e22\u51fa',
  document_preview: '\u67e5\u770b/\u9884\u89c8\u6587\u6863',
  document_upload: '\u4e0a\u4f20\u6587\u6863',
  document_download: '\u4e0b\u8f7d\u6587\u6863',
  document_delete: '\u5220\u9664\u6587\u6863',
  patent_kb_add: '\u4e13\u5229\u6dfb\u52a0\u5230\u672c\u5730\u4e13\u5229',
  patent_kb_add_all: '\u4e13\u5229\u6279\u91cf\u6dfb\u52a0\u5230\u672c\u5730\u4e13\u5229',
  patent_item_delete: '\u5220\u9664\u4e13\u5229\u6761\u76ee',
  patent_session_delete: '\u5220\u9664\u4e13\u5229\u4f1a\u8bdd',
  paper_kb_add: '\u8bba\u6587\u6dfb\u52a0\u5230\u672c\u5730\u8bba\u6587',
  paper_kb_add_all: '\u8bba\u6587\u6279\u91cf\u6dfb\u52a0\u5230\u672c\u5730\u8bba\u6587',
  paper_item_delete: '\u5220\u9664\u8bba\u6587\u6761\u76ee',
  paper_session_delete: '\u5220\u9664\u8bba\u6587\u4f1a\u8bdd',
  datasets_create: '\u65b0\u5efa\u77e5\u8bc6\u5e93',
  datasets_update: '\u4fee\u6539\u77e5\u8bc6\u5e93',
  datasets_delete: '\u5220\u9664\u77e5\u8bc6\u5e93',
  overwrite: '\u8986\u76d6\u5165\u5e93',
};

const SOURCE_LABELS = {
  auth: '\u8ba4\u8bc1',
  knowledge: '\u672c\u5730\u77e5\u8bc6\u5e93',
  ragflow: 'RAGFlow',
  patent_download: '\u4e13\u5229\u4e0b\u8f7d',
  paper_download: '\u8bba\u6587\u4e0b\u8f7d',
  patent: '\u4e13\u5229',
  paper: '\u8bba\u6587',
};

const actionLabel = (value) => ACTION_LABELS[String(value || '').trim()] || String(value || '');
const sourceLabel = (value) => SOURCE_LABELS[String(value || '').trim()] || String(value || '');

const ACTION_OPTIONS = [
  { value: '', label: '\u5168\u90e8' },
  { value: 'auth_login', label: '\u767b\u5f55' },
  { value: 'auth_logout', label: '\u9000\u51fa\u767b\u5f55' },
  { value: 'auth_session_kick', label: '\u4f1a\u8bdd\u8e22\u51fa' },
  { value: 'document_preview', label: '\u67e5\u770b/\u9884\u89c8\u6587\u6863' },
  { value: 'document_upload', label: '\u4e0a\u4f20\u6587\u6863' },
  { value: 'document_download', label: '\u4e0b\u8f7d\u6587\u6863' },
  { value: 'document_delete', label: '\u5220\u9664\u6587\u6863' },
  { value: 'patent_kb_add', label: '\u4e13\u5229\u6dfb\u52a0\u5230\u672c\u5730\u4e13\u5229' },
  { value: 'patent_kb_add_all', label: '\u4e13\u5229\u6279\u91cf\u6dfb\u52a0\u5230\u672c\u5730\u4e13\u5229' },
  { value: 'patent_item_delete', label: '\u5220\u9664\u4e13\u5229\u6761\u76ee' },
  { value: 'patent_session_delete', label: '\u5220\u9664\u4e13\u5229\u4f1a\u8bdd' },
  { value: 'paper_kb_add', label: '\u8bba\u6587\u6dfb\u52a0\u5230\u672c\u5730\u8bba\u6587' },
  { value: 'paper_kb_add_all', label: '\u8bba\u6587\u6279\u91cf\u6dfb\u52a0\u5230\u672c\u5730\u8bba\u6587' },
  { value: 'paper_item_delete', label: '\u5220\u9664\u8bba\u6587\u6761\u76ee' },
  { value: 'paper_session_delete', label: '\u5220\u9664\u8bba\u6587\u4f1a\u8bdd' },
  { value: 'datasets_create', label: '\u65b0\u5efa\u77e5\u8bc6\u5e93' },
  { value: 'datasets_update', label: '\u4fee\u6539\u77e5\u8bc6\u5e93' },
  { value: 'datasets_delete', label: '\u5220\u9664\u77e5\u8bc6\u5e93' },
  { value: 'overwrite', label: '\u8986\u76d6\u5165\u5e93' },
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

  const rows = useMemo(() => result.items || [], [result.items]);

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
    <div data-testid="audit-logs-page">
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
            gridTemplateColumns: 'repeat(6, minmax(0, 1fr))',
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
              {departments.map((d) => (
                <option key={d.id} value={String(d.id)}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 4 }}>账号</div>
            <input
              value={filters.username}
              onChange={(e) => setFilters((s) => ({ ...s, username: e.target.value }))}
              placeholder="账号精确匹配"
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

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
          <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>
            总条数： <span data-testid="audit-total" style={{ fontWeight: 700, color: '#111827' }}>{result.total}</span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
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
        <table style={tableStyle} data-testid="audit-table">
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
                <td style={tdStyle}>{r.username || r.actor}</td>
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
  );
};

export default AuditLogs;


