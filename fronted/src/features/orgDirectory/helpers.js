export const MOBILE_BREAKPOINT = 768;
export const SEARCH_RESULT_LIMIT = 50;
export const OVERVIEW_TAB = 'overview';
export const AUDIT_TAB = 'audit';

export const ORG_EXCEL_FILE_REQUIRED_ERROR = '请先选择组织架构 Excel 文件';
export const ORG_EXCEL_FILE_TYPE_ERROR = '仅支持上传 .xls 或 .xlsx 格式的组织架构文件';
export const ORG_TREE_LOAD_ERROR = '加载组织架构失败';
export const ORG_AUDIT_LOAD_ERROR = '加载组织审计失败';
export const DINGTALK_DIRECTORY_REBUILD_FAILED_ERROR = '钉钉 UserID 目录重建失败';

export const toNodeKey = (node) => `${node.node_type}:${node.id}`;

export const toSearchResultTestId = (entry) =>
  `org-search-result-${entry.key.replace(/[^a-zA-Z0-9_-]/g, '-')}`;

export const entityLabel = (entityType) => {
  if (entityType === 'company') return '公司';
  if (entityType === 'department') return '部门';
  if (entityType === 'org_structure') return '组织重建';
  return entityType || '-';
};

export const actionLabel = (action) => {
  if (action === 'create') return '新增';
  if (action === 'update') return '更新';
  if (action === 'delete') return '删除';
  if (action === 'rebuild') return '重建';
  return action || '-';
};

export const searchTypeLabel = (nodeType) => {
  if (nodeType === 'company') return '公司';
  if (nodeType === 'department') return '部门';
  if (nodeType === 'person') return '人员';
  return nodeType || '-';
};

export const reasonLabel = (reason) => {
  if (reason === 'employee_user_id_missing') return '组织架构人员缺少 UserID';
  if (reason === 'employee_user_id_duplicate') return '组织架构人员 UserID 重复';
  return reason || '-';
};

export const formatDateTime = (value) => {
  if (!value) return '-';
  try {
    return new Date(value).toLocaleString('zh-CN');
  } catch {
    return String(value);
  }
};

export const chunkItems = (items, size) => {
  const normalizedSize = Math.max(1, Number(size) || 1);
  const rows = [];
  for (let index = 0; index < items.length; index += normalizedSize) {
    rows.push(items.slice(index, index + normalizedSize));
  }
  return rows;
};

export const countNodeType = (nodes, nodeType) => {
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

export const collectBranchKeys = (nodes) => {
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

export const flattenSearchEntries = (nodes) => {
  const entries = [];
  const walk = (items, branchPathKeys = []) => {
    items.forEach((node) => {
      const key = toNodeKey(node);
      const nextBranchPathKeys =
        node.node_type === 'person' ? branchPathKeys : [...branchPathKeys, key];

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

export const matchesSearchTerm = (entry, searchTerm) => {
  const haystack = [entry.name, entry.pathName, entry.employeeUserId].join(' ').toLowerCase();
  return haystack.includes(searchTerm);
};

export const buildAuditParams = (filter) => {
  const params = { limit: filter.limit || 200 };
  if (filter.entity_type) params.entity_type = filter.entity_type;
  if (filter.action) params.action = filter.action;
  return params;
};

export const isSupportedExcelFilename = (filename) => {
  const normalizedName = String(filename || '').trim().toLowerCase();
  return normalizedName.endsWith('.xls') || normalizedName.endsWith('.xlsx');
};

export const isDingtalkChannel = (item) =>
  String(item?.channel_type || '').trim().toLowerCase() === 'dingtalk';

export const buildRebuildConfirmMessage = (filename) =>
  `确定使用 ${filename} 重建组织架构吗？这会重建公司、部门和人员树。`;

export const buildDingtalkRebuildResultText = (summary) =>
  `组织人员 ${summary.org_user_count} 人，目录写入 ${summary.directory_entry_count} 条，手工别名已清空。`;

export const buildDingtalkRebuildSuccessNotice = (summary) =>
  `组织架构重建成功，钉钉 UserID 目录已重建：${buildDingtalkRebuildResultText(summary)}`;

export const buildDingtalkRebuildSkippedNotice = () =>
  '组织架构重建成功，未配置钉钉通知通道，已跳过钉钉 UserID 目录重建。';

export const buildDingtalkRebuildFailureError = (detail) =>
  `组织架构重建成功，但钉钉 UserID 目录重建失败：${detail}`;
