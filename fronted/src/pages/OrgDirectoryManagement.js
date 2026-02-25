import React, { useEffect, useMemo, useState } from 'react';
import { orgDirectoryApi } from '../features/orgDirectory/api';

const tabButtonStyle = (active) => ({
  padding: '10px 16px',
  border: '1px solid #e5e7eb',
  borderBottom: active ? 'none' : '1px solid #e5e7eb',
  backgroundColor: active ? 'white' : '#f9fafb',
  cursor: 'pointer',
  borderTopLeftRadius: '8px',
  borderTopRightRadius: '8px',
  fontWeight: active ? 700 : 500,
});

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
};

const thStyle = {
  padding: '12px 16px',
  textAlign: 'left',
  borderBottom: '1px solid #e5e7eb',
  backgroundColor: '#f9fafb',
};

const tdStyle = {
  padding: '12px 16px',
  borderBottom: '1px solid #e5e7eb',
};

const OrgDirectoryManagement = () => {
  const [tab, setTab] = useState('companies'); // companies | departments | audit
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [auditError, setAuditError] = useState(null);

  const [companies, setCompanies] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);

  const [newCompanyName, setNewCompanyName] = useState('');
  const [newDepartmentName, setNewDepartmentName] = useState('');

  const [auditFilter, setAuditFilter] = useState({ entity_type: '', action: '', limit: 200 });

  const loadAll = async () => {
    try {
      setLoading(true);
      setError(null);
      setAuditError(null);
      const [c, d, a] = await Promise.allSettled([
        orgDirectoryApi.listCompanies(),
        orgDirectoryApi.listDepartments(),
        orgDirectoryApi.listAudit({ limit: 200 }),
      ]);

      if (c.status === 'fulfilled') {
        setCompanies(Array.isArray(c.value) ? c.value : []);
      } else {
        setCompanies([]);
      }

      if (d.status === 'fulfilled') {
        setDepartments(Array.isArray(d.value) ? d.value : []);
      } else {
        setDepartments([]);
      }

      if (a.status === 'fulfilled') {
        setAuditLogs(Array.isArray(a.value) ? a.value : []);
      } else {
        setAuditLogs([]);
        setAuditError(a.reason?.message || String(a.reason || '加载操作记录失败'));
      }

      if (c.status === 'rejected' || d.status === 'rejected') {
        const firstErr = c.status === 'rejected' ? c.reason : d.reason;
        setError(firstErr?.message || String(firstErr || '加载组织信息失败'));
      }
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const refreshAudit = async () => {
    setAuditError(null);
    const params = {
      limit: auditFilter.limit || 200,
    };
    if (auditFilter.entity_type) params.entity_type = auditFilter.entity_type;
    if (auditFilter.action) params.action = auditFilter.action;
    const a = await orgDirectoryApi.listAudit(params);
    setAuditLogs(Array.isArray(a) ? a : []);
  };

  const handleCreateCompany = async (e) => {
    e.preventDefault();
    try {
      await orgDirectoryApi.createCompany(newCompanyName);
      setNewCompanyName('');
      await loadAll();
    } catch (err) {
      setError(err.message || String(err));
    }
  };

  const handleCreateDepartment = async (e) => {
    e.preventDefault();
    try {
      await orgDirectoryApi.createDepartment(newDepartmentName);
      setNewDepartmentName('');
      await loadAll();
    } catch (err) {
      setError(err.message || String(err));
    }
  };

  const handleEditCompany = async (company) => {
    const name = window.prompt('修改公司名', company.name);
    if (name == null) return;
    try {
      await orgDirectoryApi.updateCompany(company.id, name);
      await loadAll();
    } catch (err) {
      setError(err.message || String(err));
    }
  };

  const handleDeleteCompany = async (company) => {
    if (!window.confirm(`确定要删除公司“${company.name}”吗？`)) return;
    try {
      await orgDirectoryApi.deleteCompany(company.id);
      await loadAll();
    } catch (err) {
      setError(err.message || String(err));
    }
  };

  const handleEditDepartment = async (dept) => {
    const name = window.prompt('修改部门名', dept.name);
    if (name == null) return;
    try {
      await orgDirectoryApi.updateDepartment(dept.id, name);
      await loadAll();
    } catch (err) {
      setError(err.message || String(err));
    }
  };

  const handleDeleteDepartment = async (dept) => {
    if (!window.confirm(`确定要删除部门“${dept.name}”吗？`)) return;
    try {
      await orgDirectoryApi.deleteDepartment(dept.id);
      await loadAll();
    } catch (err) {
      setError(err.message || String(err));
    }
  };

  const auditRows = useMemo(() => auditLogs || [], [auditLogs]);

  if (loading) return <div>Loading...</div>;

  return (
    <div data-testid="org-page">
      <h2 style={{ margin: '0 0 16px 0' }}>公司 / 部门管理</h2>

      {error ? (
        <div
          data-testid="org-error"
          style={{
            color: '#991b1b',
            backgroundColor: '#fee2e2',
            border: '1px solid #fecaca',
            borderRadius: 6,
            padding: '8px 12px',
            marginBottom: 12,
          }}
        >
          Error: {error}
        </div>
      ) : null}

      <div style={{ display: 'flex', gap: '8px', marginBottom: 0 }}>
        <button type="button" data-testid="org-tab-companies" onClick={() => setTab('companies')} style={tabButtonStyle(tab === 'companies')}>
          公司
        </button>
        <button type="button" data-testid="org-tab-departments" onClick={() => setTab('departments')} style={tabButtonStyle(tab === 'departments')}>
          部门
        </button>
        <button type="button" data-testid="org-tab-audit" onClick={() => setTab('audit')} style={tabButtonStyle(tab === 'audit')}>
          操作记录
        </button>
      </div>

      <div style={{
        backgroundColor: 'white',
        border: '1px solid #e5e7eb',
        borderRadius: '8px',
        padding: '16px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
      }}>
        {tab === 'companies' && (
          <div>
            <form onSubmit={handleCreateCompany} style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
              <input
                value={newCompanyName}
                onChange={(e) => setNewCompanyName(e.target.value)}
                data-testid="org-company-name"
                placeholder="新增公司名"
                style={{
                  flex: 1,
                  padding: '10px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                }}
              />
              <button
                type="submit"
                data-testid="org-company-add"
                style={{
                  padding: '10px 16px',
                  backgroundColor: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                }}
              >
                添加
              </button>
            </form>

            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>公司名</th>
                  <th style={{ ...thStyle, width: '220px' }}>更新时间</th>
                  <th style={{ ...thStyle, width: '160px', textAlign: 'right' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {companies.map((c) => (
                  <tr key={c.id} data-testid={`org-company-row-${c.id}`}>
                    <td style={tdStyle}>{c.name}</td>
                    <td style={{ ...tdStyle, color: '#6b7280' }}>{new Date(c.updated_at_ms).toLocaleString('zh-CN')}</td>
                    <td style={{ ...tdStyle, textAlign: 'right' }}>
                      <button
                        type="button"
                        data-testid={`org-company-edit-${c.id}`}
                        onClick={() => handleEditCompany(c)}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#8b5cf6',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          marginRight: '8px',
                        }}
                      >
                        修改
                      </button>
                      <button
                        type="button"
                        data-testid={`org-company-delete-${c.id}`}
                        onClick={() => handleDeleteCompany(c)}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#ef4444',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                        }}
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
                {companies.length === 0 && (
                  <tr>
                    <td style={{ ...tdStyle, color: '#6b7280' }} colSpan={3}>暂无公司</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'departments' && (
          <div>
            <form onSubmit={handleCreateDepartment} style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
              <input
                value={newDepartmentName}
                onChange={(e) => setNewDepartmentName(e.target.value)}
                data-testid="org-department-name"
                placeholder="新增部门名"
                style={{
                  flex: 1,
                  padding: '10px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                }}
              />
              <button
                type="submit"
                data-testid="org-department-add"
                style={{
                  padding: '10px 16px',
                  backgroundColor: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                }}
              >
                添加
              </button>
            </form>

            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>部门名</th>
                  <th style={{ ...thStyle, width: '220px' }}>更新时间</th>
                  <th style={{ ...thStyle, width: '160px', textAlign: 'right' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {departments.map((d) => (
                  <tr key={d.id} data-testid={`org-department-row-${d.id}`}>
                    <td style={tdStyle}>{d.name}</td>
                    <td style={{ ...tdStyle, color: '#6b7280' }}>{new Date(d.updated_at_ms).toLocaleString('zh-CN')}</td>
                    <td style={{ ...tdStyle, textAlign: 'right' }}>
                      <button
                        type="button"
                        data-testid={`org-department-edit-${d.id}`}
                        onClick={() => handleEditDepartment(d)}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#8b5cf6',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          marginRight: '8px',
                        }}
                      >
                        修改
                      </button>
                      <button
                        type="button"
                        data-testid={`org-department-delete-${d.id}`}
                        onClick={() => handleDeleteDepartment(d)}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#ef4444',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                        }}
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
                {departments.length === 0 && (
                  <tr>
                    <td style={{ ...tdStyle, color: '#6b7280' }} colSpan={3}>暂无部门</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'audit' && (
          <div>
            {auditError ? (
              <div
                data-testid="org-audit-error"
                style={{
                  color: '#991b1b',
                  backgroundColor: '#fee2e2',
                  border: '1px solid #fecaca',
                  borderRadius: 6,
                  padding: '8px 12px',
                  marginBottom: 12,
                }}
              >
                Error: {auditError}
              </div>
            ) : null}
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap' }}>
              <div>
                <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: '6px' }}>类型</div>
                <select
                  value={auditFilter.entity_type}
                  onChange={(e) => setAuditFilter({ ...auditFilter, entity_type: e.target.value })}
                  data-testid="org-audit-entity-type"
                  style={{ padding: '8px', borderRadius: '6px', border: '1px solid #d1d5db' }}
                >
                  <option value="">全部</option>
                  <option value="company">公司</option>
                  <option value="department">部门</option>
                </select>
              </div>
              <div>
                <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: '6px' }}>动作</div>
                <select
                  value={auditFilter.action}
                  onChange={(e) => setAuditFilter({ ...auditFilter, action: e.target.value })}
                  data-testid="org-audit-action"
                  style={{ padding: '8px', borderRadius: '6px', border: '1px solid #d1d5db' }}
                >
                  <option value="">全部</option>
                  <option value="create">新增</option>
                  <option value="update">修改</option>
                  <option value="delete">删除</option>
                </select>
              </div>
              <div>
                <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: '6px' }}>条数</div>
                <select
                  value={String(auditFilter.limit)}
                  onChange={(e) => setAuditFilter({ ...auditFilter, limit: Number(e.target.value) })}
                  data-testid="org-audit-limit"
                  style={{ padding: '8px', borderRadius: '6px', border: '1px solid #d1d5db' }}
                >
                  <option value="50">50</option>
                  <option value="200">200</option>
                  <option value="500">500</option>
                </select>
              </div>
              <button
                type="button"
                data-testid="org-audit-refresh"
                onClick={async () => {
                  try {
                    await refreshAudit();
                  } catch (err) {
                    setAuditError(err.message || String(err));
                  }
                }}
                style={{
                  padding: '10px 16px',
                  backgroundColor: '#111827',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  height: '40px',
                  marginTop: '22px',
                }}
              >
                刷新
              </button>
            </div>

            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>时间</th>
                  <th style={thStyle}>类型</th>
                  <th style={thStyle}>动作</th>
                  <th style={thStyle}>变更</th>
                  <th style={thStyle}>操作人</th>
                </tr>
              </thead>
              <tbody>
                {auditRows.map((l) => (
                  <tr key={l.id} data-testid={`org-audit-row-${l.id}`}>
                    <td style={{ ...tdStyle, color: '#6b7280', width: '220px' }}>
                      {new Date(l.created_at_ms).toLocaleString('zh-CN')}
                    </td>
                    <td style={tdStyle} data-testid={`org-audit-entity-${l.id}`}>
                      {l.entity_type === 'company' ? '公司' : l.entity_type === 'department' ? '部门' : l.entity_type}
                    </td>
                    <td style={tdStyle} data-testid={`org-audit-action-${l.id}`}>
                      {l.action === 'create' ? '新增' : l.action === 'update' ? '修改' : l.action === 'delete' ? '删除' : l.action}
                    </td>
                    <td style={tdStyle} data-testid={`org-audit-change-${l.id}`}>
                      {l.action === 'create' && <span>新增：{l.after_name}</span>}
                      {l.action === 'update' && <span>{l.before_name} → {l.after_name}</span>}
                      {l.action === 'delete' && <span>删除：{l.before_name}</span>}
                    </td>
                    <td style={tdStyle} data-testid={`org-audit-actor-${l.id}`}>{l.actor_username || l.actor_user_id}</td>
                  </tr>
                ))}
                {auditRows.length === 0 && (
                  <tr>
                    <td style={{ ...tdStyle, color: '#6b7280' }} colSpan={5}>暂无记录</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default OrgDirectoryManagement;
