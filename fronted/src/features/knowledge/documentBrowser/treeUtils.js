import { ROOT } from './constants';

export function buildIndexes(tree) {
  const byId = new Map();
  const childrenByParent = new Map();
  (tree?.nodes || []).forEach((node) => {
    if (!node?.id) return;
    byId.set(node.id, node);
    const parent = node.parent_id || ROOT;
    if (!childrenByParent.has(parent)) childrenByParent.set(parent, []);
    childrenByParent.get(parent).push(node);
  });
  for (const list of childrenByParent.values()) {
    list.sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN'));
  }
  return { byId, childrenByParent };
}

export function pathNodes(nodeId, byId) {
  if (!nodeId) return [];
  const output = [];
  const seen = new Set();
  let current = nodeId;
  while (current && !seen.has(current)) {
    seen.add(current);
    const node = byId.get(current);
    if (!node) break;
    output.push(node);
    current = node.parent_id || ROOT;
  }
  return output.reverse();
}

export function buildDatasetsWithFolders(datasets, tree) {
  const byId = new Map();
  const byName = new Map();
  (tree?.datasets || []).forEach((dataset) => {
    if (dataset?.id) byId.set(dataset.id, dataset);
    if (dataset?.name) byName.set(dataset.name, dataset);
  });
  return (datasets || []).map((dataset) => {
    const matched = byId.get(dataset.id) || byName.get(dataset.name);
    return {
      ...dataset,
      node_id: matched?.node_id || ROOT,
      node_path: matched?.node_path || '/',
    };
  });
}
