import React, { useEffect, useMemo, useRef, useState } from 'react';
import { orgDirectoryApi } from '../features/orgDirectory/api';

const MOBILE_BREAKPOINT = 768;
const SEARCH_RESULT_LIMIT = 50;
const OVERVIEW_TAB = 'overview';
const AUDIT_TAB = 'audit';
const SUPPORTED_EXCEL_EXTENSIONS = ['.xls', '.xlsx'];
const panelStyle = {
  backgroundColor: '#ffffff',
  border: '1px solid #e5e7eb',
  borderRadius: '14px',
  boxShadow: '0 1px 3px rgba(15, 23, 42, 0.08)',
};

const treeButtonStyle = {
  width: 18,
  height: 18,
  border: '1px solid #d1d5db',
  borderRadius: 5,
  backgroundColor: '#ffffff',
  color: '#111827',
  fontSize: '0.72rem',
  fontWeight: 700,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  flexShrink: 0,
};

const thStyle = {
  padding: '10px 12px',
  textAlign: 'left',
  borderBottom: '1px solid #e5e7eb',
  backgroundColor: '#f8fafc',
  fontSize: '0.82rem',
};

const tdStyle = {
  padding: '10px 12px',
  borderBottom: '1px solid #e5e7eb',
  verticalAlign: 'top',
  fontSize: '0.84rem',
};

const treeBranchStyle = {
  marginLeft: 14,
  paddingLeft: 10,
  borderLeft: '1px solid #e5e7eb',
  display: 'grid',
  gap: 3,
};

const toNodeKey = (node) => `${node.node_type}:${node.id}`;
const toSearchResultTestId = (entry) => `org-search-result-${entry.key.replace(/[^a-zA-Z0-9_-]/g, '-')}`;

const entityLabel = (entityType) => {
  if (entityType === 'company') return '公司';
  if (entityType === 'department') return '部门';
  if (entityType === 'org_structure') return '组织重建';
  return entityType || '-';
};

const actionLabel = (action) => {
  if (action === 'create') return '新增';
  if (action === 'update') return '更新';
  if (action === 'delete') return '删除';
  if (action === 'rebuild') return '重建';
  return action || '-';
};

const searchTypeLabel = (nodeType) => {
  if (nodeType === 'company') return '公司';
  if (nodeType === 'department') return '部门';
  if (nodeType === 'person') return '人员';
  return nodeType || '-';
};

const formatDateTime = (value) => {
  if (!value) return '-';
  try {
    return new Date(value).toLocaleString('zh-CN');
  } catch {
    return String(value);
  }
};

const countNodeType = (nodes, nodeType) => {
  let count = 0;
  const stack = [...(Array.isArray(nodes) ? nodes : [])];
  while (stack.length > 0) {
    const current = stack.shift();
    if (!current) continue;
    if (current.node_type === nodeType) count += 1;
    if (Array.isArray(current.children) && current.children.length > 0) {
      stack.unshift(...current.children);
    }
  }
  return count;
};

const collectBranchKeys = (nodes) => {
  const keys = [];
  const walk = (items) => {
    items.forEach((node) => {
      if (!node || node.node_type === 'person') return;
      const children = Array.isArray(node.children) ? node.children : [];
      const branchChildren = children.filter((child) => child && child.node_type !== 'person');
      if (node.node_type === 'company' || branchChildren.length > 0) {
        keys.push(toNodeKey(node));
      }
      if (branchChildren.length > 0) {
        walk(branchChildren);
      }
    });
  };
  walk(Array.isArray(nodes) ? nodes : []);
  return keys;
};

const flattenSearchEntries = (nodes) => {
  const entries = [];
  const walk = (items, branchPathKeys = []) => {
    items.forEach((node) => {
      const key = toNodeKey(node);
      const nextBranchPathKeys = node.node_type === 'person' ? branchPathKeys : [...branchPathKeys, key];

      entries.push({
        key,
        node,
        nodeType: node.node_type,
        name: String(node.name || ''),
        pathName: String(node.path_name || node.name || ''),
        employeeUserId: String(node.employee_user_id || ''),
        branchPathKeys: nextBranchPathKeys,
      });

      if (Array.isArray(node.children) && node.children.length > 0) {
        walk(node.children, nextBranchPathKeys);
      }
    });
  };
  walk(Array.isArray(nodes) ? nodes : []);
  return entries;
};

const matchesSearchTerm = (entry, searchTerm) => {
  const haystack = [entry.name, entry.pathName, entry.employeeUserId].join(' ').toLowerCase();
  return haystack.includes(searchTerm);
};

const buildAuditParams = (filter) => {
  const params = { limit: filter.limit || 200 };
  if (filter.entity_type) params.entity_type = filter.entity_type;
  if (filter.action) params.action = filter.action;
  return params;
};

const chunkItems = (items, size) => {
  const normalizedSize = Math.max(1, Number(size) || 1);
  const rows = [];
  for (let idx = 0; idx < items.length; idx += normalizedSize) {
    rows.push(items.slice(idx, idx + normalizedSize));
  }
  return rows;
};

const isSupportedExcelFilename = (filename) => {
  const normalizedName = String(filename || '').trim().toLowerCase();
  return SUPPORTED_EXCEL_EXTENSIONS.some((extension) => normalizedName.endsWith(extension));
};

const AuditChangeText = ({ log }) => {
  if (log.action === 'rebuild') {
    return (
      <div>
        <div style={{ fontWeight: 600 }}>{log.after_name || '组织架构已重建'}</div>
        {log.before_name ? (
          <div style={{ marginTop: 4, color: '#6b7280', fontSize: '0.8rem' }}>
            Excel: {log.before_name}
          </div>
        ) : null}
      </div>
    );
  }

  if (log.action === 'create') return <span>新增：{log.after_name || '-'}</span>;
  if (log.action === 'update') return <span>{log.before_name || '-'} {'->'} {log.after_name || '-'}</span>;
  if (log.action === 'delete') return <span>删除：{log.before_name || '-'}</span>;
  return <span>{log.after_name || log.before_name || '-'}</span>;
};

const TabButton = ({ active, children, dataTestId, onClick }) => (
  <button
    type="button"
    data-testid={dataTestId}
    onClick={onClick}
    style={{
      padding: '10px 12px',
      borderRadius: 10,
      border: `1px solid ${active ? '#93c5fd' : '#d1d5db'}`,
      backgroundColor: active ? '#eff6ff' : '#ffffff',
      color: active ? '#1d4ed8' : '#374151',
      fontWeight: 700,
      cursor: 'pointer',
      width: '100%',
    }}
  >
    {children}
  </button>
);

const TreeNode = ({
  node,
  depth,
  expandedKeys,
  onToggleBranch,
  onSelectPerson,
  highlightedNodeKey,
  selectedPersonNodeKey,
  personColumnCount,
  registerNodeRef,
}) => {
  const nodeKey = toNodeKey(node);
  const children = Array.isArray(node.children) ? node.children : [];
  const branchChildren = children.filter((item) => item.node_type !== 'person');
  const peopleChildren = children.filter((item) => item.node_type === 'person');
  const sortedPeopleChildren = [...peopleChildren].sort((left, right) => {
    const leftManager = left.is_department_manager ? 1 : 0;
    const rightManager = right.is_department_manager ? 1 : 0;
    if (leftManager !== rightManager) return rightManager - leftManager;
    if ((left.sort_order || 0) !== (right.sort_order || 0)) {
      return (left.sort_order || 0) - (right.sort_order || 0);
    }
    return String(left.name || '').localeCompare(String(right.name || ''), 'zh-CN');
  });
  const peopleRows = chunkItems(sortedPeopleChildren, personColumnCount);
  const hasChildren = children.length > 0;
  const branchExpanded = node.node_type === 'person' ? false : expandedKeys.has(nodeKey);
  const isHighlighted = highlightedNodeKey === nodeKey;
  const isCompany = node.node_type === 'company';
  const isPerson = node.node_type === 'person';
  const badgeLabel = isCompany ? '公司' : '部门';
  const metaText = isPerson
    ? [
        node.employee_user_id ? `员工UserID ${node.employee_user_id}` : null,
        node.employee_no ? `工号 ${node.employee_no}` : null,
        node.email ? node.email : null,
      ]
        .filter(Boolean)
        .join(' · ') || '-'
    : `更新时间 ${formatDateTime(node.updated_at_ms)}`;

  return (
    <div style={{ marginTop: depth === 0 ? 0 : 2 }}>
      <div
        ref={(element) => registerNodeRef(nodeKey, element)}
        data-node-key={nodeKey}
        data-testid={`org-tree-node-${node.node_type}-${node.id}`}
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 8,
          padding: isCompany ? '5px 8px' : '4px 8px',
          borderRadius: 10,
          backgroundColor: isHighlighted ? '#dbeafe' : isCompany ? '#f8fbff' : '#ffffff',
          border: `1px solid ${isHighlighted ? '#60a5fa' : isCompany ? '#dbeafe' : '#edf2f7'}`,
        }}
      >
        <div style={{ width: 18, marginTop: 1 }}>
          {!isPerson && hasChildren ? (
            <button
              type="button"
              onClick={() => onToggleBranch(nodeKey)}
              aria-label={branchExpanded ? '收起分支' : '展开分支'}
              style={treeButtonStyle}
            >
              {branchExpanded ? '-' : '+'}
            </button>
          ) : (
            <div style={{ width: 18 }} />
          )}
        </div>

        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            {!isPerson ? (
              <span
                style={{
                  fontSize: '0.68rem',
                  lineHeight: 1.2,
                  padding: '2px 7px',
                  borderRadius: 999,
                  backgroundColor: isCompany ? '#dbeafe' : '#f3f4f6',
                  color: '#1f2937',
                  fontWeight: 700,
                }}
              >
                {badgeLabel}
              </span>
            ) : null}
            <span
              style={{
                fontSize: isCompany ? '0.87rem' : '0.82rem',
                fontWeight: 700,
                color: '#111827',
                wordBreak: 'break-word',
              }}
            >
              {node.name}
            </span>
            {!isCompany && !isPerson ? (
              <span style={{ fontSize: '0.72rem', color: '#64748b' }}>L{node.level_no}</span>
            ) : null}
          </div>

          {node.path_name && node.path_name !== node.name ? (
            <div style={{ marginTop: 3, color: '#6b7280', fontSize: '0.74rem', wordBreak: 'break-word' }}>
              {node.path_name}
            </div>
          ) : null}

          <div style={{ marginTop: 3, color: '#64748b', fontSize: '0.73rem', wordBreak: 'break-word' }}>
            {metaText}
          </div>
        </div>
      </div>

      {!isPerson && branchExpanded ? (
        <div style={treeBranchStyle}>
          {branchChildren.map((child) => (
            <TreeNode
              key={toNodeKey(child)}
              node={child}
              depth={depth + 1}
              expandedKeys={expandedKeys}
              onToggleBranch={onToggleBranch}
              onSelectPerson={onSelectPerson}
              highlightedNodeKey={highlightedNodeKey}
              selectedPersonNodeKey={selectedPersonNodeKey}
              personColumnCount={personColumnCount}
              registerNodeRef={registerNodeRef}
            />
          ))}
          {sortedPeopleChildren.length > 0 ? (
            <div style={{ marginTop: 4, overflowX: 'auto' }}>
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  tableLayout: 'fixed',
                  backgroundColor: '#ffffff',
                  border: '1px solid #e5e7eb',
                  borderRadius: 10,
                }}
              >
                <tbody>
                  {peopleRows.map((row, rowIndex) => (
                    <tr key={`person-row-${nodeKey}-${rowIndex}`}>
                      {row.map((child, columnIndex) => {
                        const childNodeKey = toNodeKey(child);
                        const isSelectedPerson = selectedPersonNodeKey === childNodeKey;
                        const isHighlightedPerson = highlightedNodeKey === childNodeKey;
                        return (
                          <td
                            key={childNodeKey}
                            style={{
                              width: `${100 / personColumnCount}%`,
                              borderBottom:
                                rowIndex === peopleRows.length - 1
                                  ? 'none'
                                  : '1px solid #e5e7eb',
                              borderRight: columnIndex === row.length - 1 ? 'none' : '1px solid #e5e7eb',
                              padding: 0,
                            }}
                          >
                            <button
                              ref={(element) => registerNodeRef(childNodeKey, element)}
                              type="button"
                              data-node-key={childNodeKey}
                              data-testid={`org-tree-node-person-${child.id}`}
                              onClick={() => onSelectPerson(child)}
                              style={{
                                width: '100%',
                                padding: '8px 10px',
                                border: 'none',
                                backgroundColor: isSelectedPerson || isHighlightedPerson ? '#eff6ff' : '#ffffff',
                                color: child.is_department_manager ? '#15803d' : '#111827',
                                fontSize: '0.8rem',
                                fontWeight: child.is_department_manager ? 700 : 500,
                                textAlign: 'left',
                                cursor: 'pointer',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                              }}
                              title={child.name}
                            >
                              {child.name}
                            </button>
                          </td>
                        );
                      })}
                      {Array.from({ length: Math.max(0, personColumnCount - row.length) }).map((_, fillerIndex) => (
                        <td
                          key={`person-empty-${nodeKey}-${rowIndex}-${fillerIndex}`}
                          style={{
                            width: `${100 / personColumnCount}%`,
                            borderBottom:
                              rowIndex === peopleRows.length - 1
                                ? 'none'
                                : '1px solid #e5e7eb',
                            borderRight:
                              fillerIndex === personColumnCount - row.length - 1 ? 'none' : '1px solid #e5e7eb',
                          }}
                        />
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
};

const OrgDirectoryManagement = () => {
  const nodeRefs = useRef(new Map());
  const excelFileInputRef = useRef(null);
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const [activeTab, setActiveTab] = useState(OVERVIEW_TAB);
  const [loading, setLoading] = useState(true);
  const [rebuilding, setRebuilding] = useState(false);
  const [error, setError] = useState(null);
  const [auditError, setAuditError] = useState(null);
  const [tree, setTree] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [overviewAuditLogs, setOverviewAuditLogs] = useState([]);
  const [auditFilter, setAuditFilter] = useState({ entity_type: '', action: '', limit: 200 });
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSearchKey, setSelectedSearchKey] = useState(null);
  const [selectedPersonNodeKey, setSelectedPersonNodeKey] = useState(null);
  const [highlightedNodeKey, setHighlightedNodeKey] = useState(null);
  const [expandedKeys, setExpandedKeys] = useState(new Set());
  const [selectedExcelFile, setSelectedExcelFile] = useState(null);

  const personColumnCount = isMobile ? 2 : 4;
  const personCount = useMemo(() => countNodeType(tree, 'person'), [tree]);
  const latestOverviewAudit = useMemo(
    () => (overviewAuditLogs.length > 0 ? overviewAuditLogs[0] : null),
    [overviewAuditLogs],
  );
  const hasOrgData = tree.length > 0 || companies.length > 0 || departments.length > 0;
  const isMissingPersonNodes = hasOrgData && personCount === 0;
  const canTriggerRebuild = !!selectedExcelFile && !rebuilding;
  const searchEntries = useMemo(() => flattenSearchEntries(tree), [tree]);
  const selectedPersonEntry = useMemo(
    () =>
      searchEntries.find((entry) => entry.key === selectedPersonNodeKey && entry.nodeType === 'person') || null,
    [searchEntries, selectedPersonNodeKey],
  );
  const trimmedSearchTerm = searchTerm.trim().toLowerCase();
  const totalSearchMatches = useMemo(() => {
    if (!trimmedSearchTerm) return 0;
    return searchEntries.filter((entry) => matchesSearchTerm(entry, trimmedSearchTerm)).length;
  }, [searchEntries, trimmedSearchTerm]);
  const searchResults = useMemo(() => {
    if (!trimmedSearchTerm) return [];
    return searchEntries.filter((entry) => matchesSearchTerm(entry, trimmedSearchTerm)).slice(0, SEARCH_RESULT_LIMIT);
  }, [searchEntries, trimmedSearchTerm]);

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    setAuditError(null);

    try {
      const [treeResult, companyResult, departmentResult, tableAuditResult, overviewAuditResult] =
        await Promise.allSettled([
          orgDirectoryApi.getTree(),
          orgDirectoryApi.listCompanies(),
          orgDirectoryApi.listDepartments(),
          orgDirectoryApi.listAudit(buildAuditParams(auditFilter)),
          orgDirectoryApi.listAudit({ limit: 200 }),
        ]);

      if (treeResult.status === 'fulfilled') {
        setTree(Array.isArray(treeResult.value) ? treeResult.value : []);
      } else {
        setTree([]);
      }

      if (companyResult.status === 'fulfilled') {
        setCompanies(Array.isArray(companyResult.value) ? companyResult.value : []);
      } else {
        setCompanies([]);
      }

      if (departmentResult.status === 'fulfilled') {
        setDepartments(Array.isArray(departmentResult.value) ? departmentResult.value : []);
      } else {
        setDepartments([]);
      }

      if (tableAuditResult.status === 'fulfilled') {
        setAuditLogs(Array.isArray(tableAuditResult.value) ? tableAuditResult.value : []);
      } else {
        setAuditLogs([]);
        setAuditError(
          tableAuditResult.reason?.message || String(tableAuditResult.reason || '加载组织审计失败'),
        );
      }

      if (overviewAuditResult.status === 'fulfilled') {
        setOverviewAuditLogs(Array.isArray(overviewAuditResult.value) ? overviewAuditResult.value : []);
      } else {
        setOverviewAuditLogs([]);
      }

      if (
        treeResult.status === 'rejected' ||
        companyResult.status === 'rejected' ||
        departmentResult.status === 'rejected'
      ) {
        const firstError =
          treeResult.status === 'rejected'
            ? treeResult.reason
            : companyResult.status === 'rejected'
              ? companyResult.reason
              : departmentResult.reason;
        setError(firstError?.message || String(firstError || '加载组织架构失败'));
      }
    } finally {
      setLoading(false);
    }
  };

  const refreshAudit = async (nextFilter = auditFilter) => {
    setAuditError(null);
    try {
      const data = await orgDirectoryApi.listAudit(buildAuditParams(nextFilter));
      setAuditLogs(Array.isArray(data) ? data : []);
    } catch (err) {
      setAuditLogs([]);
      setAuditError(err.message || String(err));
    }
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    setExpandedKeys(new Set());
  }, [tree]);

  useEffect(() => {
    if (!highlightedNodeKey) return undefined;
    const target = nodeRefs.current.get(highlightedNodeKey);
    if (target && typeof target.scrollIntoView === 'function') {
      target.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
    const timerId = window.setTimeout(() => setHighlightedNodeKey(null), 2200);
    return () => window.clearTimeout(timerId);
  }, [highlightedNodeKey]);

  const registerNodeRef = (key, element) => {
    if (element) {
      nodeRefs.current.set(key, element);
    } else {
      nodeRefs.current.delete(key);
    }
  };

  const resetTreeView = () => {
    setExpandedKeys(new Set());
    setSelectedSearchKey(null);
    setHighlightedNodeKey(null);
  };

  const handleSearchInputChange = (event) => {
    setSearchTerm(event.target.value);
    resetTreeView();
  };

  const handleClearSearch = () => {
    setSearchTerm('');
    resetTreeView();
  };

  const handleSelectSearchResult = (entry) => {
    if (!entry) return;
    setSelectedSearchKey(entry.key);

    if (entry.nodeType === 'company') {
      setExpandedKeys(new Set(collectBranchKeys([entry.node])));
      setSelectedPersonNodeKey(null);
    } else if (entry.nodeType === 'department') {
      setExpandedKeys(new Set(entry.branchPathKeys));
      setSelectedPersonNodeKey(null);
    } else {
      setExpandedKeys(new Set(entry.branchPathKeys));
      setSelectedPersonNodeKey(entry.key);
      setActiveTab(OVERVIEW_TAB);
    }

    setHighlightedNodeKey(entry.key);
  };

  const handleSelectPerson = (personNode) => {
    if (!personNode || personNode.node_type !== 'person') return;
    const nodeKey = toNodeKey(personNode);
    setSelectedPersonNodeKey(nodeKey);
    setSelectedSearchKey(null);
    setHighlightedNodeKey(nodeKey);
    setActiveTab(OVERVIEW_TAB);
  };

  const handleToggleBranch = (nodeKey) => {
    setExpandedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(nodeKey)) next.delete(nodeKey);
      else next.add(nodeKey);
      return next;
    });
  };

  const handleChooseExcelFile = () => {
    excelFileInputRef.current?.click();
  };

  const handleClearExcelFile = () => {
    setSelectedExcelFile(null);
    setError(null);
    if (excelFileInputRef.current) {
      excelFileInputRef.current.value = '';
    }
  };

  const handleExcelFileChange = (event) => {
    const nextFile = event.target.files?.[0] || null;
    if (!nextFile) {
      return;
    }
    if (!isSupportedExcelFilename(nextFile.name)) {
      setSelectedExcelFile(null);
      setError('仅支持上传 .xls 或 .xlsx 格式的组织架构文档');
      if (excelFileInputRef.current) {
        excelFileInputRef.current.value = '';
      }
      return;
    }
    setError(null);
    setSelectedExcelFile(nextFile);
  };

  const handleRebuild = async () => {
    if (!selectedExcelFile) {
      setError('请先选择组织架构 Excel 文档');
      return;
    }

    if (!window.confirm(`确定使用 ${selectedExcelFile.name} 重建组织架构吗？这会重建公司、部门和人员树。`)) {
      return;
    }

    setRebuilding(true);
    setError(null);
    try {
      await orgDirectoryApi.rebuildFromExcel(selectedExcelFile);
      setSearchTerm('');
      setSelectedSearchKey(null);
      setSelectedPersonNodeKey(null);
      setHighlightedNodeKey(null);
      await loadAll();
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setRebuilding(false);
    }
  };

  if (loading) return <div>加载中...</div>;

  return (
    <div data-testid="org-page">
      {error ? (
        <div
          data-testid="org-error"
          style={{
            color: '#991b1b',
            backgroundColor: '#fee2e2',
            border: '1px solid #fecaca',
            borderRadius: 8,
            padding: '10px 12px',
            marginBottom: 16,
          }}
        >
          错误: {error}
        </div>
      ) : null}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : 'minmax(0, 1.95fr) minmax(340px, 1fr)',
          gap: 16,
          alignItems: 'start',
        }}
      >
        <div style={{ ...panelStyle, padding: isMobile ? 14 : 18, minWidth: 0 }}>
          {isMissingPersonNodes ? (
            <div
              data-testid="org-tree-empty-people-hint"
              style={{
                marginBottom: 12,
                padding: '10px 12px',
                borderRadius: 10,
                backgroundColor: '#fff7ed',
                border: '1px solid #fdba74',
                color: '#9a3412',
                fontSize: '0.82rem',
                lineHeight: 1.6,
              }}
            >
              当前组织库缺少员工叶子，树暂时只能显示到部门。请先在右侧选择组织架构 Excel 文档，再执行重建后展开到个人。
            </div>
          ) : null}

          <div data-testid="org-tree" style={{ display: 'grid', gap: 3 }}>
            {tree.map((companyNode) => (
              <TreeNode
                key={toNodeKey(companyNode)}
                node={companyNode}
                depth={0}
                expandedKeys={expandedKeys}
                onToggleBranch={handleToggleBranch}
                onSelectPerson={handleSelectPerson}
                highlightedNodeKey={highlightedNodeKey}
                selectedPersonNodeKey={selectedPersonNodeKey}
                personColumnCount={personColumnCount}
                registerNodeRef={registerNodeRef}
              />
            ))}
            {tree.length === 0 ? <div style={{ color: '#6b7280' }}>暂无组织数据</div> : null}
          </div>
        </div>

        <div
          style={{
            ...panelStyle,
            padding: isMobile ? 14 : 18,
            minWidth: 0,
            position: isMobile ? 'static' : 'sticky',
            top: 16,
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
              gap: 8,
              marginBottom: 14,
            }}
          >
            <TabButton
              active={activeTab === OVERVIEW_TAB}
              dataTestId="org-tab-overview"
              onClick={() => setActiveTab(OVERVIEW_TAB)}
            >
              概览
            </TabButton>
            <TabButton
              active={activeTab === AUDIT_TAB}
              dataTestId="org-tab-audit"
              onClick={() => setActiveTab(AUDIT_TAB)}
            >
              审计
            </TabButton>
          </div>

          {activeTab === OVERVIEW_TAB ? (
            <div style={{ display: 'grid', gap: 14 }}>
              {isMissingPersonNodes ? (
                <div
                  data-testid="org-empty-people-warning"
                  style={{
                    padding: '12px 14px',
                    borderRadius: 10,
                    backgroundColor: '#fff7ed',
                    border: '1px solid #fdba74',
                    color: '#9a3412',
                  }}
                >
                  <div style={{ fontWeight: 700 }}>当前组织库缺少员工叶子</div>
                  <div style={{ marginTop: 6, fontSize: '0.82rem', lineHeight: 1.7 }}>
                    当前树数据里没有任何 `person` 节点，请先选择组织架构 Excel 文档，再点击下方“从 Excel 重建组织架构”，把员工节点写入当前活动库后再查看个人叶子。
                  </div>
                </div>
              ) : null}

              {selectedPersonEntry ? (
                <div
                  data-testid="org-selected-person-overview"
                  style={{
                    padding: '12px 14px',
                    borderRadius: 10,
                    border: '1px solid #bfdbfe',
                    backgroundColor: '#f8fbff',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      flexWrap: 'wrap',
                    }}
                  >
                    <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#111827' }}>
                      {selectedPersonEntry.node.name}
                    </div>
                    {selectedPersonEntry.node.is_department_manager ? (
                      <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#15803d' }}>
                        部门主管
                      </div>
                    ) : null}
                  </div>
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: isMobile ? '1fr' : 'repeat(2, minmax(0, 1fr))',
                      gap: 10,
                      marginTop: 10,
                    }}
                  >
                    <div style={{ ...panelStyle, padding: 10 }}>
                      <div style={{ color: '#6b7280', fontSize: '0.74rem' }}>员工UserID</div>
                      <div style={{ marginTop: 4, color: '#111827', fontSize: '0.84rem', fontWeight: 700 }}>
                        {selectedPersonEntry.node.employee_user_id || '-'}
                      </div>
                    </div>
                    <div style={{ ...panelStyle, padding: 10 }}>
                      <div style={{ color: '#6b7280', fontSize: '0.74rem' }}>部门主管</div>
                      <div
                        style={{
                          marginTop: 4,
                          color: selectedPersonEntry.node.is_department_manager ? '#15803d' : '#111827',
                          fontSize: '0.84rem',
                          fontWeight: 700,
                        }}
                      >
                        {selectedPersonEntry.node.department_manager_name || '-'}
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}

              <div>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={handleSearchInputChange}
                    placeholder="搜索公司、部门、人员或员工UserID"
                    data-testid="org-search-input"
                    style={{
                      flex: 1,
                      minWidth: 0,
                      padding: '10px 12px',
                      borderRadius: 10,
                      border: '1px solid #cbd5e1',
                      fontSize: '0.9rem',
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleClearSearch}
                    data-testid="org-search-clear"
                    style={{
                      padding: '10px 12px',
                      borderRadius: 10,
                      border: '1px solid #d1d5db',
                      backgroundColor: '#ffffff',
                      cursor: 'pointer',
                    }}
                  >
                    清空
                  </button>
                </div>

                {trimmedSearchTerm ? (
                  <div style={{ display: 'grid', gap: 8, marginTop: 10 }}>
                    <div style={{ color: '#64748b', fontSize: '0.82rem' }}>
                      搜索结果 {searchResults.length > 0 ? `${searchResults.length} 条` : ''}
                      {totalSearchMatches > SEARCH_RESULT_LIMIT ? `，仅显示前 ${SEARCH_RESULT_LIMIT} 条` : ''}
                    </div>

                    {searchResults.length > 0 ? (
                      <div style={{ display: 'grid', gap: 6, maxHeight: 240, overflowY: 'auto' }}>
                        {searchResults.map((entry) => (
                          <button
                            key={entry.key}
                            type="button"
                            data-testid={toSearchResultTestId(entry)}
                            onClick={() => handleSelectSearchResult(entry)}
                            style={{
                              textAlign: 'left',
                              border: `1px solid ${selectedSearchKey === entry.key ? '#60a5fa' : '#e5e7eb'}`,
                              backgroundColor: selectedSearchKey === entry.key ? '#eff6ff' : '#ffffff',
                              borderRadius: 10,
                              padding: '9px 10px',
                              cursor: 'pointer',
                            }}
                          >
                            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                              <span style={{ fontSize: '0.74rem', color: '#2563eb', fontWeight: 700 }}>
                                {searchTypeLabel(entry.nodeType)}
                              </span>
                              <span style={{ fontSize: '0.86rem', fontWeight: 700, color: '#111827' }}>
                                {entry.name}
                              </span>
                              {entry.employeeUserId ? (
                                <span style={{ fontSize: '0.76rem', color: '#64748b' }}>
                                  员工UserID {entry.employeeUserId}
                                </span>
                              ) : null}
                            </div>
                            <div
                              style={{
                                marginTop: 4,
                                color: '#6b7280',
                                fontSize: '0.76rem',
                                wordBreak: 'break-word',
                              }}
                            >
                              {entry.pathName}
                            </div>
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div data-testid="org-search-empty" style={{ color: '#6b7280', fontSize: '0.84rem' }}>
                        没有匹配结果，请换个关键词。
                      </div>
                    )}
                  </div>
                ) : null}
              </div>

              <div
                style={{
                  ...panelStyle,
                  padding: 12,
                  display: 'grid',
                  gap: 10,
                }}
              >
                <input
                  ref={excelFileInputRef}
                  type="file"
                  accept=".xls,.xlsx,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                  onChange={handleExcelFileChange}
                  data-testid="org-excel-file-input"
                  style={{ display: 'none' }}
                />
                <div>
                  <div style={{ color: '#111827', fontSize: '0.9rem', fontWeight: 700 }}>组织架构文档</div>
                  <div style={{ marginTop: 4, color: '#6b7280', fontSize: '0.78rem' }}>
                    请选择 Excel 文档，仅支持 .xls / .xlsx。
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    onClick={handleChooseExcelFile}
                    disabled={rebuilding}
                    data-testid="org-excel-file-trigger"
                    style={{
                      padding: '10px 12px',
                      borderRadius: 10,
                      border: '1px solid #d1d5db',
                      backgroundColor: '#ffffff',
                      color: '#111827',
                      cursor: rebuilding ? 'not-allowed' : 'pointer',
                      fontWeight: 600,
                    }}
                  >
                    选择组织架构文档
                  </button>
                  {selectedExcelFile ? (
                    <button
                      type="button"
                      onClick={handleClearExcelFile}
                      disabled={rebuilding}
                      data-testid="org-excel-file-clear"
                      style={{
                        padding: '10px 12px',
                        borderRadius: 10,
                        border: '1px solid #d1d5db',
                        backgroundColor: '#ffffff',
                        color: '#6b7280',
                        cursor: rebuilding ? 'not-allowed' : 'pointer',
                      }}
                    >
                      清除
                    </button>
                  ) : null}
                </div>
                <div
                  data-testid="org-excel-file-name"
                  style={{
                    padding: '10px 12px',
                    borderRadius: 10,
                    border: '1px dashed #cbd5e1',
                    backgroundColor: selectedExcelFile ? '#f8fbff' : '#f8fafc',
                    color: selectedExcelFile ? '#111827' : '#6b7280',
                    fontSize: '0.82rem',
                    wordBreak: 'break-word',
                  }}
                >
                  {selectedExcelFile ? selectedExcelFile.name : '未加载组织架构文档'}
                </div>
                <button
                  type="button"
                  data-testid="org-rebuild-trigger"
                  onClick={handleRebuild}
                  disabled={!canTriggerRebuild}
                  style={{
                    width: '100%',
                    padding: '11px 14px',
                    backgroundColor: canTriggerRebuild ? '#2563eb' : '#cbd5e1',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 10,
                    cursor: canTriggerRebuild ? 'pointer' : 'not-allowed',
                    fontWeight: 700,
                  }}
                >
                  {rebuilding ? '重建中...' : '从 Excel 重建组织架构'}
                </button>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
                  gap: 10,
                }}
              >
                <div style={{ ...panelStyle, padding: 12 }}>
                  <div style={{ color: '#6b7280', fontSize: '0.74rem' }}>公司节点</div>
                  <div style={{ marginTop: 6, fontSize: '1.45rem', fontWeight: 800 }}>{companies.length}</div>
                </div>
                <div style={{ ...panelStyle, padding: 12 }}>
                  <div style={{ color: '#6b7280', fontSize: '0.74rem' }}>部门节点</div>
                  <div style={{ marginTop: 6, fontSize: '1.45rem', fontWeight: 800 }}>{departments.length}</div>
                </div>
                <div style={{ ...panelStyle, padding: 12 }}>
                  <div style={{ color: '#6b7280', fontSize: '0.74rem' }}>人员节点</div>
                  <div style={{ marginTop: 6, fontSize: '1.45rem', fontWeight: 800 }}>{personCount}</div>
                </div>
                <div style={{ ...panelStyle, padding: 12 }}>
                  <div style={{ color: '#6b7280', fontSize: '0.74rem' }}>最近组织操作</div>
                  <div style={{ marginTop: 6, fontSize: '1rem', fontWeight: 700 }}>
                    {latestOverviewAudit ? actionLabel(latestOverviewAudit.action) : '暂无'}
                  </div>
                  <div style={{ marginTop: 4, color: '#6b7280', fontSize: '0.74rem' }}>
                    {latestOverviewAudit ? formatDateTime(latestOverviewAudit.created_at_ms) : '-'}
                  </div>
                </div>
              </div>

            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: isMobile ? '1fr' : 'repeat(2, minmax(0, 1fr))',
                  gap: 8,
                }}
              >
                <select
                  value={auditFilter.entity_type}
                  onChange={(event) =>
                    setAuditFilter((prev) => ({ ...prev, entity_type: event.target.value }))
                  }
                  data-testid="org-audit-entity-type"
                  style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #d1d5db' }}
                >
                  <option value="">全部类型</option>
                  <option value="company">公司</option>
                  <option value="department">部门</option>
                  <option value="org_structure">组织重建</option>
                </select>
                <select
                  value={auditFilter.action}
                  onChange={(event) => setAuditFilter((prev) => ({ ...prev, action: event.target.value }))}
                  data-testid="org-audit-action"
                  style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #d1d5db' }}
                >
                  <option value="">全部动作</option>
                  <option value="create">新增</option>
                  <option value="update">更新</option>
                  <option value="delete">删除</option>
                  <option value="rebuild">重建</option>
                </select>
                <select
                  value={String(auditFilter.limit)}
                  onChange={(event) =>
                    setAuditFilter((prev) => ({ ...prev, limit: Number(event.target.value) }))
                  }
                  data-testid="org-audit-limit"
                  style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #d1d5db' }}
                >
                  <option value="50">50</option>
                  <option value="200">200</option>
                  <option value="500">500</option>
                </select>
                <button
                  type="button"
                  data-testid="org-audit-refresh"
                  onClick={() => refreshAudit(auditFilter)}
                  style={{
                    padding: '9px 12px',
                    backgroundColor: '#111827',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 8,
                    cursor: 'pointer',
                  }}
                >
                  刷新审计
                </button>
              </div>

              {auditError ? (
                <div
                  data-testid="org-audit-error"
                  style={{
                    color: '#991b1b',
                    backgroundColor: '#fee2e2',
                    border: '1px solid #fecaca',
                    borderRadius: 8,
                    padding: '10px 12px',
                  }}
                >
                  错误: {auditError}
                </div>
              ) : null}

              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 560 }}>
                  <thead>
                    <tr>
                      <th style={thStyle}>时间</th>
                      <th style={thStyle}>类型</th>
                      <th style={thStyle}>动作</th>
                      <th style={thStyle}>变更内容</th>
                      <th style={thStyle}>操作人</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.map((log) => (
                      <tr key={log.id} data-testid={`org-audit-row-${log.id}`}>
                        <td style={{ ...tdStyle, whiteSpace: 'nowrap', color: '#6b7280' }}>
                          {formatDateTime(log.created_at_ms)}
                        </td>
                        <td style={tdStyle}>{entityLabel(log.entity_type)}</td>
                        <td style={tdStyle}>{actionLabel(log.action)}</td>
                        <td style={tdStyle}>
                          <div data-testid={`org-audit-change-${log.id}`}>
                            <AuditChangeText log={log} />
                          </div>
                        </td>
                        <td style={tdStyle}>{log.actor_username || log.actor_user_id}</td>
                      </tr>
                    ))}
                    {auditLogs.length === 0 ? (
                      <tr>
                        <td style={{ ...tdStyle, color: '#6b7280' }} colSpan={5}>
                          暂无记录
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OrgDirectoryManagement;
