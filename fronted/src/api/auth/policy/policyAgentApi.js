import { authBackendUrl } from '../../../config/backend';

export const policyAgentApiMethods = {
  async getMyKnowledgeBases() {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/me/kbs'),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get my KBs');
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
      throw new Error(error.detail || 'Failed to list agents');
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
      throw new Error(error.detail || 'Failed to get agent');
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
      throw new Error(error.detail || 'Failed to search chunks');
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
      throw new Error(error.detail || 'Failed to get datasets');
    }

    return response.json(); // { datasets: [...], count: N }
  },
};
