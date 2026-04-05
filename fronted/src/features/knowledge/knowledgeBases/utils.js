import { ROOT } from './constants';

export function pickAllowed(obj, keys) {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return {};
  const output = {};
  keys.forEach((key) => {
    if (Object.prototype.hasOwnProperty.call(obj, key)) output[key] = obj[key];
  });
  return output;
}

export function fmtTime(ms) {
  const value = Number(ms || 0);
  if (!value) return '-';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? '-' : d.toLocaleString('zh-CN', { hour12: false });
}

export function buildIndexes(tree) {
  const nodes = (tree?.nodes || []).filter((node) => node && node.id);
  const byId = new Map();
  const childrenByParent = new Map();
  nodes.forEach((node) => {
    byId.set(node.id, node);
    const parent = node.parent_id || ROOT;
    if (!childrenByParent.has(parent)) childrenByParent.set(parent, []);
    childrenByParent.get(parent).push(node);
  });
  for (const arr of childrenByParent.values()) {
    arr.sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN'));
  }
  return { byId, childrenByParent };
}

export function buildDatasetsByNode(tree) {
  const output = new Map();
  (tree?.datasets || []).forEach((dataset) => {
    if (!dataset?.id) return;
    const nodeId = dataset.node_id || ROOT;
    if (!output.has(nodeId)) output.set(nodeId, []);
    output.get(nodeId).push(dataset);
  });
  for (const arr of output.values()) {
    arr.sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN'));
  }
  return output;
}

export function pathNodes(nodeId, byId) {
  if (!nodeId) return [];
  const output = [];
  const guard = new Set();
  let current = nodeId;
  while (current && !guard.has(current)) {
    guard.add(current);
    const node = byId.get(current);
    if (!node) break;
    output.push(node);
    current = node.parent_id || ROOT;
  }
  return output.reverse();
}

export function datasetEmpty(ds) {
  return Number(ds?.local_document_count || 0) <= 0
    && Number(ds?.document_count || 0) <= 0
    && Number(ds?.chunk_count || 0) <= 0;
}
