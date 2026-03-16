import React, { useEffect, useMemo, useState } from 'react';
import { orgDirectoryApi } from '../features/orgDirectory/api';

const mapEntityType = (value) => {
  if (value === 'company') return '公司';
  if (value === 'department') return '部门';
  return '未知类型';
};

const mapAction = (value) => {
  if (value === 'create') return '新增';
  if (value === 'update') return '修改';
  if (value === 'delete') return '删除';
  return '未知动作';
};

const formatDisplayError = (message, fallback) => {
  const text = String(message || '').trim();
  if (!text) return fallback;
  return /[\u4e00-\u9fff]/.test(text) ? text : fallback;
};

const OrgDirectoryManagement = () => {
  const [tab, setTab] = useState('companies');
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
      const [companyResult, departmentResult, auditResult] = await Promise.allSettled([
        orgDirectoryApi.listCompanies(),
        orgDirectoryApi.listDepartments(),
        orgDirectoryApi.listAudit({ limit: 200 }),
      ]);

      if (companyResult.status === 'fulfilled') setCompanies(Array.isArray(companyResult.value) ? companyResult.value : []);
      else setCompanies([]);

      if (departmentResult.status === 'fulfilled') setDepartments(Array.isArray(departmentResult.value) ? departmentResult.value : []);
      else setDepartments([]);

      if (auditResult.status === 'fulfilled') {
        setAuditLogs(Array.isArray(auditResult.value) ? auditResult.value : []);
      } else {
        setAuditLogs([]);
        setAuditError(formatDisplayError(auditResult.reason?.message, '加载操作记录失败'));
      }

      if (companyResult.status === 'rejected' || departmentResult.status === 'rejected') {
        const firstError = companyResult.status === 'rejected' ? companyResult.reason : departmentResult.reason;
        setError(formatDisplayError(firstError?.message, '加载组织信息失败'));
      }
    } catch (requestError) {
      setError(formatDisplayError(requestError?.message, '加载组织信息失败'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const refreshAudit = async () => {
    setAuditError(null);
    const params = { limit: auditFilter.limit || 200 };
    if (auditFilter.entity_type) params.entity_type = auditFilter.entity_type;
    if (auditFilter.action) params.action = auditFilter.action;
    const result = await orgDirectoryApi.listAudit(params);
    setAuditLogs(Array.isArray(result) ? result : []);
  };

  const handleCreateCompany = async (event) => {
    event.preventDefault();
    try {
      await orgDirectoryApi.createCompany(newCompanyName);
      setNewCompanyName('');
      await loadAll();
    } catch (requestError) {
      setError(formatDisplayError(requestError?.message, '创建公司失败'));
    }
  };

  const handleCreateDepartment = async (event) => {
    event.preventDefault();
    try {
      await orgDirectoryApi.createDepartment(newDepartmentName);
      setNewDepartmentName('');
      await loadAll();
    } catch (requestError) {
      setError(formatDisplayError(requestError?.message, '创建部门失败'));
    }
  };

  const handleEditCompany = async (company) => {
    const name = window.prompt('修改公司名称', company.name);
    if (name == null) return;
    try {
      await orgDirectoryApi.updateCompany(company.id, name);
      await loadAll();
    } catch (requestError) {
      setError(formatDisplayError(requestError?.message, '修改公司失败'));
    }
  };

  const handleDeleteCompany = async (company) => {
    if (!window.confirm(`确定要删除公司“${company.name}”吗？`)) return;
    try {
      await orgDirectoryApi.deleteCompany(company.id);
      await loadAll();
    } catch (requestError) {
      setError(formatDisplayError(requestError?.message, '删除公司失败'));
    }
  };

  const handleEditDepartment = async (department) => {
    const name = window.prompt('修改部门名称', department.name);
    if (name == null) return;
    try {
      await orgDirectoryApi.updateDepartment(department.id, name);
      await loadAll();
    } catch (requestError) {
      setError(formatDisplayError(requestError?.message, '修改部门失败'));
    }
  };

  const handleDeleteDepartment = async (department) => {
    if (!window.confirm(`确定要删除部门“${department.name}”吗？`)) return;
    try {
      await orgDirectoryApi.deleteDepartment(department.id);
      await loadAll();
    } catch (requestError) {
      setError(formatDisplayError(requestError?.message, '删除部门失败'));
    }
  };

  const auditRows = useMemo(() => auditLogs || [], [auditLogs]);

  if (loading) return <div className="medui-empty">加载中...</div>;

  return (
    <div data-testid="org-page" className="admin-med-page">
      <div className="admin-med-head">
        <h2 className="admin-med-title">公司 / 部门管理</h2>
      </div>

      {error ? <div className="admin-med-danger" data-testid="org-error">{`错误：${error}`}</div> : null}

      <div className="admin-med-tabs">
        <button type="button" data-testid="org-tab-companies" onClick={() => setTab('companies')} className={tab === 'companies' ? 'medui-btn medui-btn--primary' : 'medui-btn medui-btn--secondary'}>
          公司
        </button>
        <button type="button" data-testid="org-tab-departments" onClick={() => setTab('departments')} className={tab === 'departments' ? 'medui-btn medui-btn--primary' : 'medui-btn medui-btn--secondary'}>
          部门
        </button>
        <button type="button" data-testid="org-tab-audit" onClick={() => setTab('audit')} className={tab === 'audit' ? 'medui-btn medui-btn--primary' : 'medui-btn medui-btn--secondary'}>
          操作记录
        </button>
      </div>

      <div className="medui-surface medui-card-pad">
        {tab === 'companies' ? (
          <div>
            <form onSubmit={handleCreateCompany} className="admin-med-head" style={{ marginBottom: 14 }}>
              <input value={newCompanyName} onChange={(event) => setNewCompanyName(event.target.value)} data-testid="org-company-name" placeholder="新增公司名称" className="medui-input" style={{ flex: 1 }} />
              <button type="submit" data-testid="org-company-add" className="medui-btn medui-btn--primary">
                添加
              </button>
            </form>

            <div className="admin-med-table-scroll">
              <table className="medui-table" style={{ minWidth: 760 }}>
                <thead>
                  <tr>
                    <th>公司名称</th>
                    <th style={{ width: 220 }}>更新时间</th>
                    <th style={{ width: 220, textAlign: 'right' }}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {companies.map((company) => (
                    <tr key={company.id} data-testid={`org-company-row-${company.id}`}>
                      <td>{company.name}</td>
                      <td>{new Date(company.updated_at_ms).toLocaleString('zh-CN')}</td>
                      <td style={{ textAlign: 'right' }}>
                        <button type="button" data-testid={`org-company-edit-${company.id}`} onClick={() => handleEditCompany(company)} className="medui-btn medui-btn--secondary" style={{ marginRight: 8 }}>
                          修改
                        </button>
                        <button type="button" data-testid={`org-company-delete-${company.id}`} onClick={() => handleDeleteCompany(company)} className="medui-btn medui-btn--danger">
                          删除
                        </button>
                      </td>
                    </tr>
                  ))}
                  {companies.length === 0 ? (
                    <tr>
                      <td colSpan={3}>暂无公司</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}

        {tab === 'departments' ? (
          <div>
            <form onSubmit={handleCreateDepartment} className="admin-med-head" style={{ marginBottom: 14 }}>
              <input value={newDepartmentName} onChange={(event) => setNewDepartmentName(event.target.value)} data-testid="org-department-name" placeholder="新增部门名称" className="medui-input" style={{ flex: 1 }} />
              <button type="submit" data-testid="org-department-add" className="medui-btn medui-btn--primary">
                添加
              </button>
            </form>

            <div className="admin-med-table-scroll">
              <table className="medui-table" style={{ minWidth: 760 }}>
                <thead>
                  <tr>
                    <th>部门名称</th>
                    <th style={{ width: 220 }}>更新时间</th>
                    <th style={{ width: 220, textAlign: 'right' }}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {departments.map((department) => (
                    <tr key={department.id} data-testid={`org-department-row-${department.id}`}>
                      <td>{department.name}</td>
                      <td>{new Date(department.updated_at_ms).toLocaleString('zh-CN')}</td>
                      <td style={{ textAlign: 'right' }}>
                        <button type="button" data-testid={`org-department-edit-${department.id}`} onClick={() => handleEditDepartment(department)} className="medui-btn medui-btn--secondary" style={{ marginRight: 8 }}>
                          修改
                        </button>
                        <button type="button" data-testid={`org-department-delete-${department.id}`} onClick={() => handleDeleteDepartment(department)} className="medui-btn medui-btn--danger">
                          删除
                        </button>
                      </td>
                    </tr>
                  ))}
                  {departments.length === 0 ? (
                    <tr>
                      <td colSpan={3}>暂无部门</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}

        {tab === 'audit' ? (
          <div>
            {auditError ? <div className="admin-med-danger" data-testid="org-audit-error">{`错误：${auditError}`}</div> : null}

            <div className="admin-med-actions" style={{ alignItems: 'end', marginBottom: 14 }}>
              <div>
                <div className="admin-med-small" style={{ marginBottom: 6 }}>类型</div>
                <select value={auditFilter.entity_type} onChange={(event) => setAuditFilter({ ...auditFilter, entity_type: event.target.value })} data-testid="org-audit-entity-type" className="medui-select">
                  <option value="">全部</option>
                  <option value="company">公司</option>
                  <option value="department">部门</option>
                </select>
              </div>

              <div>
                <div className="admin-med-small" style={{ marginBottom: 6 }}>动作</div>
                <select value={auditFilter.action} onChange={(event) => setAuditFilter({ ...auditFilter, action: event.target.value })} data-testid="org-audit-action" className="medui-select">
                  <option value="">全部</option>
                  <option value="create">新增</option>
                  <option value="update">修改</option>
                  <option value="delete">删除</option>
                </select>
              </div>

              <div>
                <div className="admin-med-small" style={{ marginBottom: 6 }}>条数</div>
                <select value={String(auditFilter.limit)} onChange={(event) => setAuditFilter({ ...auditFilter, limit: Number(event.target.value) })} data-testid="org-audit-limit" className="medui-select">
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
                  } catch (requestError) {
                    setAuditError(formatDisplayError(requestError?.message, '加载操作记录失败'));
                  }
                }}
                className="medui-btn medui-btn--primary"
              >
                刷新
              </button>
            </div>

            <div className="admin-med-table-scroll">
              <table className="medui-table" style={{ minWidth: 860 }}>
                <thead>
                  <tr>
                    <th>时间</th>
                    <th>类型</th>
                    <th>动作</th>
                    <th>变更</th>
                    <th>操作人</th>
                  </tr>
                </thead>
                <tbody>
                  {auditRows.map((log) => (
                    <tr key={log.id} data-testid={`org-audit-row-${log.id}`}>
                      <td>{new Date(log.created_at_ms).toLocaleString('zh-CN')}</td>
                      <td data-testid={`org-audit-entity-${log.id}`}>{mapEntityType(log.entity_type)}</td>
                      <td data-testid={`org-audit-action-${log.id}`}>{mapAction(log.action)}</td>
                      <td data-testid={`org-audit-change-${log.id}`}>
                        {log.action === 'create' ? <span>{`新增：${log.after_name}`}</span> : null}
                        {log.action === 'update' ? <span>{`${log.before_name} → ${log.after_name}`}</span> : null}
                        {log.action === 'delete' ? <span>{`删除：${log.before_name}`}</span> : null}
                        {!['create', 'update', 'delete'].includes(log.action) ? <span>未知变更</span> : null}
                      </td>
                      <td data-testid={`org-audit-actor-${log.id}`}>{log.actor_username || log.actor_user_id}</td>
                    </tr>
                  ))}
                  {auditRows.length === 0 ? (
                    <tr>
                      <td colSpan={5}>暂无记录</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default OrgDirectoryManagement;
