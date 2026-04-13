const ROOT = '';

export const normalizeManagedKbRootPath = (value) => {
  const path = String(value || '').trim();
  if (!path || path === '/') return '/';
  const parts = path.split('/').map((part) => String(part || '').trim()).filter(Boolean);
  return parts.length ? `/${parts.join('/')}` : '/';
};

export const managedKbRootPathsOverlap = (left, right) => {
  const normalizedLeft = normalizeManagedKbRootPath(left);
  const normalizedRight = normalizeManagedKbRootPath(right);
  if (normalizedLeft === '/' || normalizedRight === '/') {
    return true;
  }
  return (
    normalizedLeft === normalizedRight
    || normalizedLeft.startsWith(`${normalizedRight}/`)
    || normalizedRight.startsWith(`${normalizedLeft}/`)
  );
};

const normalizeCompanyId = (value) => {
  if (value == null || value === '') return null;
  const normalized = Number(value);
  return Number.isFinite(normalized) ? normalized : null;
};

const normalizeUserId = (value) => String(value || '').trim();

const buildNodeIndexes = (nodes) => {
  const byId = new Map();
  (Array.isArray(nodes) ? nodes : []).forEach((node) => {
    const nodeId = normalizeUserId(node?.id);
    if (!nodeId) return;
    byId.set(nodeId, node);
  });
  return { byId };
};

const collectAncestorIds = (nodeId, byId, visibleIds) => {
  let currentId = normalizeUserId(nodeId);
  const guard = new Set();
  while (currentId && !guard.has(currentId)) {
    guard.add(currentId);
    visibleIds.add(currentId);
    const parentId = normalizeUserId(byId.get(currentId)?.parent_id) || ROOT;
    currentId = parentId;
  }
};

const buildOccupiedRootPaths = ({ nodes, users, companyId, excludeUserId }) => {
  const normalizedCompanyId = normalizeCompanyId(companyId);
  if (normalizedCompanyId == null) return [];

  const { byId } = buildNodeIndexes(nodes);
  return (Array.isArray(users) ? users : [])
    .filter((user) => String(user?.role || '').trim() === 'sub_admin')
    .filter((user) => String(user?.status || '').trim().toLowerCase() === 'active')
    .filter((user) => normalizeUserId(user?.user_id) !== normalizeUserId(excludeUserId))
    .filter((user) => normalizeCompanyId(user?.company_id) === normalizedCompanyId)
    .map((user) => {
      const nodeId = normalizeUserId(user?.managed_kb_root_node_id);
      const rawPath = byId.get(nodeId)?.path || user?.managed_kb_root_path || '';
      return rawPath ? normalizeManagedKbRootPath(rawPath) : '';
    })
    .filter((path, index, allPaths) => path && allPaths.indexOf(path) === index);
};

export const buildManagedKbRootSelectionState = ({
  nodes,
  users,
  companyId,
  excludeUserId = '',
  selectedNodeId = '',
}) => {
  const normalizedNodes = Array.isArray(nodes) ? nodes : [];
  if (!normalizedNodes.length) {
    return { nodes: [], disabledNodeIds: [] };
  }

  const { byId } = buildNodeIndexes(normalizedNodes);
  const occupiedRootPaths = buildOccupiedRootPaths({
    nodes: normalizedNodes,
    users,
    companyId,
    excludeUserId,
  });

  if (!occupiedRootPaths.length) {
    return { nodes: normalizedNodes, disabledNodeIds: [] };
  }

  const selectableIds = new Set();
  normalizedNodes.forEach((node) => {
    const nodeId = normalizeUserId(node?.id);
    const nodePath = normalizeManagedKbRootPath(node?.path);
    if (!nodeId) return;
    const conflicts = occupiedRootPaths.some((occupiedPath) =>
      managedKbRootPathsOverlap(nodePath, occupiedPath)
    );
    if (!conflicts) {
      selectableIds.add(nodeId);
    }
  });

  const visibleIds = new Set();
  selectableIds.forEach((nodeId) => collectAncestorIds(nodeId, byId, visibleIds));

  const normalizedSelectedNodeId = normalizeUserId(selectedNodeId);
  if (normalizedSelectedNodeId && byId.has(normalizedSelectedNodeId)) {
    collectAncestorIds(normalizedSelectedNodeId, byId, visibleIds);
  }

  const visibleNodes = normalizedNodes.filter((node) => visibleIds.has(normalizeUserId(node?.id)));
  const disabledNodeIds = visibleNodes
    .map((node) => normalizeUserId(node?.id))
    .filter((nodeId) => nodeId && !selectableIds.has(nodeId));

  return {
    nodes: visibleNodes,
    disabledNodeIds,
  };
};
