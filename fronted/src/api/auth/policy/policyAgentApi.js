import { authBackendUrl } from '../../../config/backend';

export const policyAgentApiMethods = {
  async getMyKnowledgeBases() {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/me/kbs'),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(this.resolveErrorMessage(error, '获取我的知识库失败'));
    }

    return response.json(); // { kb_ids: [...] }
  },

  async listAgents(params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/agents?${queryParams}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(this.resolveErrorMessage(error, '获取助手列表失败'));
    }

    return response.json(); // { agents: [...], count: N }
  },

  async getAgent(agentId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/agents/${agentId}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(this.resolveErrorMessage(error, '获取助手详情失败'));
    }

    return response.json();
  },

  async searchChunks(searchParams) {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/search'),
      {
        method: 'POST',
        body: JSON.stringify(searchParams)
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(this.resolveErrorMessage(error, '检索分段内容失败'));
    }

    return response.json(); // { chunks: [...], total: N, page: N, page_size: N }
  },

  async getAvailableDatasets() {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/datasets'),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(this.resolveErrorMessage(error, '获取数据集失败'));
    }

    return response.json(); // { datasets: [...], count: N }
  },
};
