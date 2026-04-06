import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { orgDirectoryApi } from './api';

const MOBILE_BREAKPOINT = 768;
const SEARCH_RESULT_LIMIT = 50;
const OVERVIEW_TAB = 'overview';

const toNodeKey = (node) => `${node.node_type}:${node.id}`;

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

const isSupportedExcelFilename = (filename) => {
  const normalizedName = String(filename || '').trim().toLowerCase();
  return normalizedName.endsWith('.xls') || normalizedName.endsWith('.xlsx');
};

export default function useOrgDirectoryManagementPage() {
  const nodeRefs = useRef(new Map());
  const excelFileInputRef = useRef(null);
  const auditFilterRef = useRef({ entity_type: '', action: '', limit: 200 });

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

  useEffect(() => {
    auditFilterRef.current = auditFilter;
  }, [auditFilter]);

  const personColumnCount = isMobile ? 2 : 4;
  const personCount = useMemo(() => countNodeType(tree, 'person'), [tree]);
  const latestOverviewAudit = useMemo(
    () => (overviewAuditLogs.length > 0 ? overviewAuditLogs[0] : null),
    [overviewAuditLogs]
  );
  const hasOrgData = tree.length > 0 || companies.length > 0 || departments.length > 0;
  const isMissingPersonNodes = hasOrgData && personCount === 0;
  const canTriggerRebuild = !!selectedExcelFile && !rebuilding;
  const searchEntries = useMemo(() => flattenSearchEntries(tree), [tree]);
  const selectedPersonEntry = useMemo(
    () =>
      searchEntries.find((entry) => entry.key === selectedPersonNodeKey && entry.nodeType === 'person') || null,
    [searchEntries, selectedPersonNodeKey]
  );
  const trimmedSearchTerm = searchTerm.trim().toLowerCase();
  const totalSearchMatches = useMemo(() => {
    if (!trimmedSearchTerm) return 0;
    return searchEntries.filter((entry) => matchesSearchTerm(entry, trimmedSearchTerm)).length;
  }, [searchEntries, trimmedSearchTerm]);
  const searchResults = useMemo(() => {
    if (!trimmedSearchTerm) return [];
    return searchEntries
      .filter((entry) => matchesSearchTerm(entry, trimmedSearchTerm))
      .slice(0, SEARCH_RESULT_LIMIT);
  }, [searchEntries, trimmedSearchTerm]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    setAuditError(null);

    try {
      const [treeResult, companyResult, departmentResult, tableAuditResult, overviewAuditResult] =
        await Promise.allSettled([
          orgDirectoryApi.getTree(),
          orgDirectoryApi.listCompanies(),
          orgDirectoryApi.listDepartments(),
          orgDirectoryApi.listAudit(buildAuditParams(auditFilterRef.current)),
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
          tableAuditResult.reason?.message || String(tableAuditResult.reason || '加载组织审计失败')
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
  }, []);

  const refreshAudit = useCallback(async (nextFilter = auditFilterRef.current) => {
    setAuditError(null);
    try {
      const data = await orgDirectoryApi.listAudit(buildAuditParams(nextFilter));
      setAuditLogs(Array.isArray(data) ? data : []);
    } catch (err) {
      setAuditLogs([]);
      setAuditError(err?.message || String(err));
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

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

  const registerNodeRef = useCallback((key, element) => {
    if (element) {
      nodeRefs.current.set(key, element);
    } else {
      nodeRefs.current.delete(key);
    }
  }, []);

  const resetTreeView = useCallback(() => {
    setExpandedKeys(new Set());
    setSelectedSearchKey(null);
    setHighlightedNodeKey(null);
  }, []);

  const handleSearchInputChange = useCallback(
    (event) => {
      setSearchTerm(event.target.value);
      resetTreeView();
    },
    [resetTreeView]
  );

  const handleClearSearch = useCallback(() => {
    setSearchTerm('');
    resetTreeView();
  }, [resetTreeView]);

  const handleSelectSearchResult = useCallback((entry) => {
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
  }, []);

  const handleSelectPerson = useCallback((personNode) => {
    if (!personNode || personNode.node_type !== 'person') return;
    const nodeKey = toNodeKey(personNode);
    setSelectedPersonNodeKey(nodeKey);
    setSelectedSearchKey(null);
    setHighlightedNodeKey(nodeKey);
    setActiveTab(OVERVIEW_TAB);
  }, []);

  const handleToggleBranch = useCallback((nodeKey) => {
    setExpandedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(nodeKey)) next.delete(nodeKey);
      else next.add(nodeKey);
      return next;
    });
  }, []);

  const handleChooseExcelFile = useCallback(() => {
    excelFileInputRef.current?.click();
  }, []);

  const handleClearExcelFile = useCallback(() => {
    setSelectedExcelFile(null);
    setError(null);
    if (excelFileInputRef.current) {
      excelFileInputRef.current.value = '';
    }
  }, []);

  const handleExcelFileChange = useCallback((event) => {
    const nextFile = event.target.files?.[0] || null;
    if (!nextFile) return;
    if (!isSupportedExcelFilename(nextFile.name)) {
      setSelectedExcelFile(null);
      setError('仅支持上传 .xls 或 .xlsx 格式的组织架构文件');
      if (excelFileInputRef.current) {
        excelFileInputRef.current.value = '';
      }
      return;
    }
    setError(null);
    setSelectedExcelFile(nextFile);
  }, []);

  const handleRebuild = useCallback(async () => {
    if (!selectedExcelFile) {
      setError('请先选择组织架构 Excel 文件');
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
      setError(err?.message || String(err));
    } finally {
      setRebuilding(false);
    }
  }, [loadAll, selectedExcelFile]);

  return {
    excelFileInputRef,
    isMobile,
    activeTab,
    setActiveTab,
    loading,
    rebuilding,
    error,
    auditError,
    tree,
    companies,
    departments,
    auditLogs,
    latestOverviewAudit,
    auditFilter,
    setAuditFilter,
    searchTerm,
    selectedSearchKey,
    selectedPersonNodeKey,
    selectedPersonEntry,
    highlightedNodeKey,
    expandedKeys,
    selectedExcelFile,
    personColumnCount,
    personCount,
    isMissingPersonNodes,
    canTriggerRebuild,
    trimmedSearchTerm,
    totalSearchMatches,
    searchResults,
    registerNodeRef,
    refreshAudit,
    handleSearchInputChange,
    handleClearSearch,
    handleSelectSearchResult,
    handleSelectPerson,
    handleToggleBranch,
    handleChooseExcelFile,
    handleClearExcelFile,
    handleExcelFileChange,
    handleRebuild,
  };
}
