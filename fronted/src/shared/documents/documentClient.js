import { httpClient } from '../http/httpClient';

export const DOCUMENT_SOURCE = {
  RAGFLOW: 'ragflow',
  KNOWLEDGE: 'knowledge',
  PATENT: 'patent',
  PAPER: 'paper',
};

const buildQuery = (params = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '') return;
    qs.set(k, String(v));
  });
  const s = qs.toString();
  return s ? `?${s}` : '';
};

const parseMaybeJson = async (resp) => {
  try {
    return await resp.json();
  } catch {
    return null;
  }
};

const normalizeDisplayError = (message, fallback) => {
  const text = String(message || '').trim();
  if (!text) return fallback;
  if (/[\u4e00-\u9fff]/.test(text)) return text;
  return fallback;
};

const requestJsonWithResponse = async (path, options = {}) => {
  const response = await httpClient.request(path, options);
  const data = await parseMaybeJson(response);
  if (!response.ok) {
    const message = normalizeDisplayError(
      data?.detail || data?.message || data?.error,
      `请求失败（状态码：${response.status}）`
    );
    const error = new Error(message);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return { data, response };
};

const parseContentDispositionFilename = (contentDisposition, fallbackName) => {
  let filename = fallbackName;
  const cd = String(contentDisposition || '');
  if (!cd) return filename;

  const utf8Match = cd.match(/filename\*=UTF-8''([^;\s]+)/i);
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1]);

  const filenameMatch = cd.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
  if (filenameMatch?.[1]) return filenameMatch[1].replace(/['"]/g, '');

  return filename;
};

/**
 * Frontend document management facade.
 *
 * This is the only place that should know which backend endpoints to call for:
 * - preview (unified JSON contract)
 * - download (blob)
 * - upload (knowledge staging)
 * - delete
 *
 * Callers should pass a normalized `ref`:
 *   { source: 'ragflow'|'knowledge', docId, datasetName?, filename?, render? }
 */
class DocumentClient {
  async preview(ref) {
    const t0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
    const source = String(ref?.source || '').toLowerCase();
    const docId = ref?.docId;
    const render = ref?.render;
    if (!docId) throw new Error('缺少文档编号');

    if (source === DOCUMENT_SOURCE.RAGFLOW) {
      const datasetName = ref?.datasetName || ref?.dataset || '';
      if (!datasetName) throw new Error('缺少数据集');
      const { data, response } = await requestJsonWithResponse(
        `/api/preview/documents/ragflow/${encodeURIComponent(docId)}/preview${buildQuery({ dataset: datasetName, render })}`,
        { method: 'GET' }
      );
      const requestId = response?.headers?.get?.('X-Request-ID') || '';
      // eslint-disable-next-line no-console
      console.info('[PreviewTrace][Client] preview:ragflow', { docId, datasetName, render, elapsedMs: Math.round((typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0), type: data?.type, requestId });
      return data;
    }

    if (source === DOCUMENT_SOURCE.KNOWLEDGE) {
      const { data, response } = await requestJsonWithResponse(
        `/api/preview/documents/knowledge/${encodeURIComponent(docId)}/preview${buildQuery({ render })}`,
        { method: 'GET' }
      );
      const requestId = response?.headers?.get?.('X-Request-ID') || '';
      // eslint-disable-next-line no-console
      console.info('[PreviewTrace][Client] preview:knowledge', { docId, render, elapsedMs: Math.round((typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0), type: data?.type, requestId });
      return data;
    }

    if (source === DOCUMENT_SOURCE.PATENT) {
      const sessionId = String(ref?.sessionId || '').trim();
      if (!sessionId) throw new Error('缺少会话编号');
      const { data, response } = await requestJsonWithResponse(
        `/api/patent-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(docId)}/preview${buildQuery({ render })}`,
        { method: 'GET' }
      );
      const requestId = response?.headers?.get?.('X-Request-ID') || '';
      // eslint-disable-next-line no-console
      console.info('[PreviewTrace][Client] preview:patent', { docId, sessionId, render, elapsedMs: Math.round((typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0), type: data?.type, requestId });
      return data;
    }

    if (source === DOCUMENT_SOURCE.PAPER) {
      const sessionId = String(ref?.sessionId || '').trim();
      if (!sessionId) throw new Error('缺少会话编号');
      const { data, response } = await requestJsonWithResponse(
        `/api/paper-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(docId)}/preview${buildQuery({ render })}`,
        { method: 'GET' }
      );
      const requestId = response?.headers?.get?.('X-Request-ID') || '';
      // eslint-disable-next-line no-console
      console.info('[PreviewTrace][Client] preview:paper', { docId, sessionId, render, elapsedMs: Math.round((typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0), type: data?.type, requestId });
      return data;
    }

    throw new Error('无效的数据来源');
  }

  async _downloadResponse(ref) {
    const t0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
    const source = String(ref?.source || '').toLowerCase();
    const docId = ref?.docId;
    if (!docId) throw new Error('缺少文档编号');

    if (source === DOCUMENT_SOURCE.RAGFLOW) {
      const datasetName = ref?.datasetName || ref?.dataset || '';
      if (!datasetName) throw new Error('缺少数据集');
      const filename = ref?.filename || ref?.title || '';
      const path = `/api/documents/ragflow/${encodeURIComponent(docId)}/download${buildQuery({
        dataset: datasetName,
        filename,
      })}`;
      const resp = await httpClient.request(path, { method: 'GET' });
      if (resp.ok) {
        const requestId = resp?.headers?.get?.('X-Request-ID') || '';
        // eslint-disable-next-line no-console
        console.info('[PreviewTrace][Client] download:ragflow', { docId, datasetName, elapsedMs: Math.round((typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0), requestId });
        return resp;
      }

      const data = await parseMaybeJson(resp);
      const message = normalizeDisplayError(
        data?.detail || data?.message || data?.error,
        `下载失败（状态码：${resp.status}）`
      );
      const err = new Error(message);
      err.status = resp.status;
      err.data = data;
      throw err;
    }

    if (source === DOCUMENT_SOURCE.KNOWLEDGE) {
      const resp = await httpClient.request(`/api/documents/knowledge/${encodeURIComponent(docId)}/download`, { method: 'GET' });
      if (resp.ok) {
        const requestId = resp?.headers?.get?.('X-Request-ID') || '';
        // eslint-disable-next-line no-console
        console.info('[PreviewTrace][Client] download:knowledge', { docId, elapsedMs: Math.round((typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0), requestId });
        return resp;
      }

      const data = await parseMaybeJson(resp);
      const message = normalizeDisplayError(
        data?.detail || data?.message || data?.error,
        `下载失败（状态码：${resp.status}）`
      );
      const err = new Error(message);
      err.status = resp.status;
      err.data = data;
      throw err;
    }

    if (source === DOCUMENT_SOURCE.PATENT) {
      const sessionId = String(ref?.sessionId || '').trim();
      if (!sessionId) throw new Error('缺少会话编号');
      const resp = await httpClient.request(
        `/api/patent-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(docId)}/download`,
        { method: 'GET' }
      );
      if (resp.ok) {
        const requestId = resp?.headers?.get?.('X-Request-ID') || '';
        // eslint-disable-next-line no-console
        console.info('[PreviewTrace][Client] download:patent', { docId, sessionId, elapsedMs: Math.round((typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0), requestId });
        return resp;
      }

      const data = await parseMaybeJson(resp);
      const message = normalizeDisplayError(
        data?.detail || data?.message || data?.error,
        `下载失败（状态码：${resp.status}）`
      );
      const err = new Error(message);
      err.status = resp.status;
      err.data = data;
      throw err;
    }

    if (source === DOCUMENT_SOURCE.PAPER) {
      const sessionId = String(ref?.sessionId || '').trim();
      if (!sessionId) throw new Error('缺少会话编号');
      const resp = await httpClient.request(
        `/api/paper-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(docId)}/download`,
        { method: 'GET' }
      );
      if (resp.ok) {
        const requestId = resp?.headers?.get?.('X-Request-ID') || '';
        // eslint-disable-next-line no-console
        console.info('[PreviewTrace][Client] download:paper', { docId, sessionId, elapsedMs: Math.round((typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0), requestId });
        return resp;
      }

      const data = await parseMaybeJson(resp);
      const message = normalizeDisplayError(
        data?.detail || data?.message || data?.error,
        `下载失败（状态码：${resp.status}）`
      );
      const err = new Error(message);
      err.status = resp.status;
      err.data = data;
      throw err;
    }

    throw new Error('无效的数据来源');
  }

  async downloadBlob(ref) {
    const resp = await this._downloadResponse(ref);
    return resp.blob();
  }

  async downloadToBrowser(ref) {
    const resp = await this._downloadResponse(ref);
    const docId = ref?.docId;
    const fallbackName = String(ref?.filename || ref?.title || (docId ? `document_${docId}` : 'document'));
    const filename = parseContentDispositionFilename(resp.headers?.get?.('Content-Disposition'), fallbackName);

    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    return { success: true, filename };
  }

  async batchDownloadKnowledgeToBrowser(docIds) {
    const ids = Array.isArray(docIds) ? docIds : [];
    if (ids.length === 0) throw new Error('未选择文档');

    const resp = await httpClient.request(`/api/documents/knowledge/batch/download`, {
      method: 'POST',
      body: JSON.stringify({ doc_ids: ids }),
    });
    if (!resp.ok) {
      const data = await parseMaybeJson(resp);
      const message = normalizeDisplayError(
        data?.detail || data?.message || data?.error,
        `批量下载失败（状态码：${resp.status}）`
      );
      const err = new Error(message);
      err.status = resp.status;
      err.data = data;
      throw err;
    }

    const fallbackName = `documents_batch_${Date.now()}.zip`;
    const filename = parseContentDispositionFilename(resp.headers?.get?.('Content-Disposition'), fallbackName);

    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    return { success: true, filename };
  }

  async batchDownloadRagflowToBrowser(documents) {
    const docs = Array.isArray(documents) ? documents : [];
    if (docs.length === 0) throw new Error('未选择文档');

    const resp = await httpClient.request(`/api/documents/ragflow/batch/download`, {
      method: 'POST',
      body: JSON.stringify({ documents: docs }),
    });
    if (!resp.ok) {
      const data = await parseMaybeJson(resp);
      const message = normalizeDisplayError(
        data?.detail || data?.message || data?.error,
        `批量下载失败（状态码：${resp.status}）`
      );
      const err = new Error(message);
      err.status = resp.status;
      err.data = data;
      throw err;
    }

    const fallbackName = `documents_batch_${Date.now()}.zip`;
    const filename = parseContentDispositionFilename(resp.headers?.get?.('Content-Disposition'), fallbackName);

    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    return { success: true, filename };
  }

  async delete(ref) {
    const source = String(ref?.source || '').toLowerCase();
    const docId = ref?.docId;
    if (!docId) throw new Error('缺少文档编号');

    if (source === DOCUMENT_SOURCE.RAGFLOW) {
      const datasetName = ref?.datasetName || ref?.dataset || '';
      if (!datasetName) throw new Error('缺少数据集');
      return httpClient.requestJson(
        `/api/documents/ragflow/${encodeURIComponent(docId)}${buildQuery({ dataset_name: datasetName })}`,
        { method: 'DELETE' }
      );
    }

    if (source === DOCUMENT_SOURCE.KNOWLEDGE) {
      return httpClient.requestJson(`/api/documents/knowledge/${encodeURIComponent(docId)}`, { method: 'DELETE' });
    }

    throw new Error('无效的数据来源');
  }

  async uploadKnowledge(file, kbId) {
    if (!file) throw new Error('缺少上传文件');
    if (!kbId) throw new Error('缺少知识库编号');
    const formData = new FormData();
    formData.append('file', file);
    return httpClient.requestJson(`/api/documents/knowledge/upload${buildQuery({ kb_id: kbId })}`, {
      method: 'POST',
      body: formData,
      includeContentType: false,
    });
  }

  async onlyofficeEditorConfig(ref) {
    const t0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
    const source = String(ref?.source || '').toLowerCase();
    const docId = String(ref?.docId || '').trim();
    if (!docId) throw new Error('缺少文档编号');
    if (!source) throw new Error('缺少数据来源');
    const { data, response } = await requestJsonWithResponse('/api/onlyoffice/editor-config', {
      method: 'POST',
      body: JSON.stringify({
        source,
        doc_id: docId,
        dataset: ref?.datasetName || ref?.dataset || '',
        session_id: ref?.sessionId || '',
        filename: ref?.filename || ref?.title || '',
      }),
    });
    const requestId = response?.headers?.get?.('X-Request-ID') || '';
    // eslint-disable-next-line no-console
    console.info('[PreviewTrace][Client] onlyoffice:editor-config', { source, docId, elapsedMs: Math.round((typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0), serverUrl: data?.server_url, requestId });
    return data;
  }
}

const documentClient = new DocumentClient();
export default documentClient;
