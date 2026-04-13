// @ts-check

function withCompanyId(path, companyId) {
  if (companyId === undefined || companyId === null || companyId === '') {
    return path;
  }
  const query = new URLSearchParams({ company_id: String(companyId) }).toString();
  return `${path}?${query}`;
}

async function readJson(response, fallbackMessage) {
  if (!response.ok()) {
    const body = await response.text().catch(() => '');
    throw new Error(`${fallbackMessage}: ${response.status()} ${body}`.trim());
  }
  return response.json();
}

async function listKnowledgeDirectories(api, headers, { companyId } = {}) {
  const response = await api.get(withCompanyId('/api/knowledge/directories', companyId), {
    headers,
  });
  const payload = await readJson(response, 'list knowledge directories failed');
  if (!payload || typeof payload !== 'object' || !Array.isArray(payload.nodes)) {
    throw new Error('list knowledge directories returned invalid payload');
  }
  return payload;
}

async function createKnowledgeDirectory(api, headers, {
  name,
  parentId = null,
  companyId,
} = {}) {
  const response = await api.post(withCompanyId('/api/knowledge/directories', companyId), {
    headers,
    data: {
      name,
      parent_id: parentId || null,
    },
  });
  const payload = await readJson(response, `create knowledge directory failed for ${name}`);
  const node = payload?.node;
  if (!node || typeof node !== 'object') {
    throw new Error(`create knowledge directory returned invalid payload for ${name}`);
  }
  if (!String(node.id || '').trim()) {
    throw new Error(`create knowledge directory did not return node id for ${name}`);
  }
  return node;
}

async function deleteKnowledgeDirectory(api, headers, nodeId) {
  const response = await api.delete(`/api/knowledge/directories/${encodeURIComponent(nodeId)}`, {
    headers,
  });
  if (response.ok() || response.status() === 404) {
    return;
  }
  const body = await response.text().catch(() => '');
  throw new Error(
    `delete knowledge directory failed for ${nodeId}: ${response.status()} ${body}`.trim()
  );
}

module.exports = {
  listKnowledgeDirectories,
  createKnowledgeDirectory,
  deleteKnowledgeDirectory,
};
