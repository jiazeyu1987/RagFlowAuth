export const TOOL_PERMISSION_ITEMS = Object.freeze([
  { id: 'paper_download', name: '论文下载分析' },
  { id: 'patent_download', name: '专利下载分析' },
  { id: 'package_drawing', name: '包装图纸' },
  { id: 'nhsa_code_search', name: '医保编码查询工具' },
  { id: 'shanghai_tax', name: '上海电子税务局' },
  { id: 'drug_admin', name: '药监导航' },
  { id: 'nmpa', name: 'NMPA' },
]);

const TOOL_ID_SET = new Set(TOOL_PERMISSION_ITEMS.map((item) => item.id));

export const TOOL_PERMISSION_IDS = Object.freeze(Array.from(TOOL_ID_SET));

export const normalizeToolIds = (rawValue) => {
  const values = Array.isArray(rawValue) ? rawValue : [];
  const seen = new Set();
  const normalized = [];

  for (const item of values) {
    const toolId = String(item || '').trim();
    if (!toolId || !TOOL_ID_SET.has(toolId) || seen.has(toolId)) {
      continue;
    }
    seen.add(toolId);
    normalized.push(toolId);
  }

  return normalized;
};

export const mapToolIdsToChecklistItems = (toolIds) => {
  const allowed = new Set(normalizeToolIds(toolIds));
  return TOOL_PERMISSION_ITEMS
    .filter((item) => allowed.has(item.id))
    .map((item) => ({
      group_id: item.id,
      group_name: item.name,
    }));
};
