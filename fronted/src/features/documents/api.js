import { authBackendUrl } from '../../config/backend';
import { DOCUMENT_SOURCE } from '../../shared/documents/constants';
import { httpClient } from '../../shared/http/httpClient';

export { DOCUMENT_SOURCE };

const buildQuery = (params = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    qs.set(key, String(value));
  });
  const query = qs.toString();
  return query ? `?${query}` : '';
};

const parseMaybeJson = async (response) => {
  try {
    return await response.json();
  } catch {
    return null;
  }
};

const requestJsonWithResponse = async (path, options = {}) => {
  const response = await httpClient.request(authBackendUrl(path), options);
  const data = await parseMaybeJson(response);
  if (!response.ok) {
    const message = data?.detail || data?.message || data?.error || `Request failed (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return { data, response };
};

const parseContentDispositionFilename = (contentDisposition, fallbackName) => {
  let filename = fallbackName;
  const header = String(contentDisposition || '');
  if (!header) return filename;

  const utf8Match = header.match(/filename\*=UTF-8''([^;\s]+)/i);
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1]);

  const filenameMatch = header.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
  if (filenameMatch?.[1]) return filenameMatch[1].replace(/['"]/g, '');

  return filename;
};

const nowMs = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());

const logPreviewTrace = (event, payload) => {
  // eslint-disable-next-line no-console
  console.info(`[PreviewTrace][Client] ${event}`, payload);
};

const previewDocument = async (ref) => {
  const startedAt = nowMs();
  const source = String(ref?.source || '').toLowerCase();
  const docId = ref?.docId;
  const render = ref?.render;
  if (!docId) throw new Error('missing_doc_id');

  if (source === DOCUMENT_SOURCE.RAGFLOW) {
    const datasetName = ref?.datasetName || ref?.dataset || '';
    if (!datasetName) throw new Error('missing_dataset');
    const { data, response } = await requestJsonWithResponse(
      `/api/preview/documents/ragflow/${encodeURIComponent(docId)}/preview${buildQuery({ dataset: datasetName, render })}`,
      { method: 'GET' }
    );
    logPreviewTrace('preview:ragflow', {
      docId,
      datasetName,
      render,
      elapsedMs: Math.round(nowMs() - startedAt),
      type: data?.type,
      requestId: response?.headers?.get?.('X-Request-ID') || '',
    });
    return data;
  }

  if (source === DOCUMENT_SOURCE.KNOWLEDGE) {
    const { data, response } = await requestJsonWithResponse(
      `/api/preview/documents/knowledge/${encodeURIComponent(docId)}/preview${buildQuery({ render })}`,
      { method: 'GET' }
    );
    logPreviewTrace('preview:knowledge', {
      docId,
      render,
      elapsedMs: Math.round(nowMs() - startedAt),
      type: data?.type,
      requestId: response?.headers?.get?.('X-Request-ID') || '',
    });
    return data;
  }

  if (source === DOCUMENT_SOURCE.PATENT) {
    const sessionId = String(ref?.sessionId || '').trim();
    if (!sessionId) throw new Error('missing_session_id');
    const { data, response } = await requestJsonWithResponse(
      `/api/patent-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(docId)}/preview${buildQuery({ render })}`,
      { method: 'GET' }
    );
    logPreviewTrace('preview:patent', {
      docId,
      sessionId,
      render,
      elapsedMs: Math.round(nowMs() - startedAt),
      type: data?.type,
      requestId: response?.headers?.get?.('X-Request-ID') || '',
    });
    return data;
  }

  if (source === DOCUMENT_SOURCE.PAPER) {
    const sessionId = String(ref?.sessionId || '').trim();
    if (!sessionId) throw new Error('missing_session_id');
    const { data, response } = await requestJsonWithResponse(
      `/api/paper-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(docId)}/preview${buildQuery({ render })}`,
      { method: 'GET' }
    );
    logPreviewTrace('preview:paper', {
      docId,
      sessionId,
      render,
      elapsedMs: Math.round(nowMs() - startedAt),
      type: data?.type,
      requestId: response?.headers?.get?.('X-Request-ID') || '',
    });
    return data;
  }

  throw new Error('invalid_source');
};

const buildDownloadPath = (ref) => {
  const source = String(ref?.source || '').toLowerCase();
  const docId = ref?.docId;
  if (!docId) throw new Error('missing_doc_id');

  if (source === DOCUMENT_SOURCE.RAGFLOW) {
    const datasetName = ref?.datasetName || ref?.dataset || '';
    if (!datasetName) throw new Error('missing_dataset');
    const filename = ref?.filename || ref?.title || '';
    return {
      source,
      path: `/api/documents/ragflow/${encodeURIComponent(docId)}/download${buildQuery({
        dataset: datasetName,
        filename,
      })}`,
      logContext: { docId, datasetName },
    };
  }

  if (source === DOCUMENT_SOURCE.KNOWLEDGE) {
    return {
      source,
      path: `/api/documents/knowledge/${encodeURIComponent(docId)}/download`,
      logContext: { docId },
    };
  }

  if (source === DOCUMENT_SOURCE.PATENT) {
    const sessionId = String(ref?.sessionId || '').trim();
    if (!sessionId) throw new Error('missing_session_id');
    return {
      source,
      path: `/api/patent-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(docId)}/download`,
      logContext: { docId, sessionId },
    };
  }

  if (source === DOCUMENT_SOURCE.PAPER) {
    const sessionId = String(ref?.sessionId || '').trim();
    if (!sessionId) throw new Error('missing_session_id');
    return {
      source,
      path: `/api/paper-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(docId)}/download`,
      logContext: { docId, sessionId },
    };
  }

  throw new Error('invalid_source');
};

const requestDownloadResponse = async (ref) => {
  const startedAt = nowMs();
  const { source, path, logContext } = buildDownloadPath(ref);
  const response = await httpClient.request(authBackendUrl(path), { method: 'GET' });
  if (response.ok) {
    logPreviewTrace(`download:${source}`, {
      ...logContext,
      elapsedMs: Math.round(nowMs() - startedAt),
      requestId: response?.headers?.get?.('X-Request-ID') || '',
    });
    return response;
  }

  const data = await parseMaybeJson(response);
  const message = data?.detail || data?.message || `download_failed (${response.status})`;
  const error = new Error(message);
  error.status = response.status;
  error.data = data;
  throw error;
};

const saveResponseToBrowser = async (response, fallbackName) => {
  const filename = parseContentDispositionFilename(
    response.headers?.get?.('Content-Disposition'),
    fallbackName
  );
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
  return { success: true, filename };
};

export const documentsApi = {
  preview(ref) {
    return previewDocument(ref);
  },

  async downloadBlob(ref) {
    const response = await requestDownloadResponse(ref);
    return response.blob();
  },

  async downloadToBrowser(ref) {
    const response = await requestDownloadResponse(ref);
    const docId = ref?.docId;
    const fallbackName = String(
      ref?.filename || ref?.title || (docId ? `document_${docId}` : 'document')
    );
    return saveResponseToBrowser(response, fallbackName);
  },

  async batchDownloadKnowledgeToBrowser(docIds) {
    const ids = Array.isArray(docIds) ? docIds : [];
    if (ids.length === 0) throw new Error('no_documents_selected');

    const response = await httpClient.request(authBackendUrl('/api/documents/knowledge/batch/download'), {
      method: 'POST',
      body: JSON.stringify({ doc_ids: ids }),
    });
    if (!response.ok) {
      const data = await parseMaybeJson(response);
      const message = data?.detail || data?.message || `batch_download_failed (${response.status})`;
      const error = new Error(message);
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return saveResponseToBrowser(response, `documents_batch_${Date.now()}.zip`);
  },

  async batchDownloadRagflowToBrowser(documents) {
    const items = Array.isArray(documents) ? documents : [];
    if (items.length === 0) throw new Error('no_documents_selected');

    const response = await httpClient.request(authBackendUrl('/api/documents/ragflow/batch/download'), {
      method: 'POST',
      body: JSON.stringify({ documents: items }),
    });
    if (!response.ok) {
      const data = await parseMaybeJson(response);
      const message = data?.detail || data?.message || `batch_download_failed (${response.status})`;
      const error = new Error(message);
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return saveResponseToBrowser(response, `documents_batch_${Date.now()}.zip`);
  },

  deleteDocument(ref) {
    const source = String(ref?.source || '').toLowerCase();
    const docId = ref?.docId;
    if (!docId) throw new Error('missing_doc_id');

    if (source === DOCUMENT_SOURCE.RAGFLOW) {
      const datasetName = ref?.datasetName || ref?.dataset || '';
      if (!datasetName) throw new Error('missing_dataset');
      return httpClient.requestJson(
        authBackendUrl(
          `/api/documents/ragflow/${encodeURIComponent(docId)}${buildQuery({ dataset_name: datasetName })}`
        ),
        { method: 'DELETE' }
      );
    }

    if (source === DOCUMENT_SOURCE.KNOWLEDGE) {
      return httpClient.requestJson(
        authBackendUrl(`/api/documents/knowledge/${encodeURIComponent(docId)}`),
        { method: 'DELETE' }
      );
    }

    throw new Error('invalid_source');
  },

  uploadKnowledge(file, kbId) {
    if (!file) throw new Error('missing_file');
    if (!kbId) throw new Error('missing_kb_id');
    const formData = new FormData();
    formData.append('file', file);
    return httpClient.requestJson(
      authBackendUrl(`/api/documents/knowledge/upload${buildQuery({ kb_id: kbId })}`),
      {
        method: 'POST',
        body: formData,
        includeContentType: false,
      }
    );
  },

  async onlyofficeEditorConfig(ref) {
    const startedAt = nowMs();
    const source = String(ref?.source || '').toLowerCase();
    const docId = String(ref?.docId || '').trim();
    if (!docId) throw new Error('missing_doc_id');
    if (!source) throw new Error('missing_source');
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
    logPreviewTrace('onlyoffice:editor-config', {
      source,
      docId,
      elapsedMs: Math.round(nowMs() - startedAt),
      serverUrl: data?.server_url,
      requestId: response?.headers?.get?.('X-Request-ID') || '',
    });
    return data;
  },
};

export default documentsApi;
