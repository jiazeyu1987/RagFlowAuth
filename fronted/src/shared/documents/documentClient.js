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
    const source = String(ref?.source || '').toLowerCase();
    const docId = ref?.docId;
    const render = ref?.render;
    if (!docId) throw new Error('missing_doc_id');

    if (source === DOCUMENT_SOURCE.RAGFLOW) {
      const datasetName = ref?.datasetName || ref?.dataset || '';
      if (!datasetName) throw new Error('missing_dataset');
      return httpClient.requestJson(
        `/api/preview/documents/ragflow/${encodeURIComponent(docId)}/preview${buildQuery({ dataset: datasetName, render })}`,
        { method: 'GET' }
      );
    }

    if (source === DOCUMENT_SOURCE.KNOWLEDGE) {
      return httpClient.requestJson(
        `/api/preview/documents/knowledge/${encodeURIComponent(docId)}/preview${buildQuery({ render })}`,
        { method: 'GET' }
      );
    }

    if (source === DOCUMENT_SOURCE.PATENT) {
      const sessionId = String(ref?.sessionId || '').trim();
      if (!sessionId) throw new Error('missing_session_id');
      return httpClient.requestJson(
        `/api/patent-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(docId)}/preview${buildQuery({ render })}`,
        { method: 'GET' }
      );
    }

    if (source === DOCUMENT_SOURCE.PAPER) {
      const sessionId = String(ref?.sessionId || '').trim();
      if (!sessionId) throw new Error('missing_session_id');
      return httpClient.requestJson(
        `/api/paper-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(docId)}/preview${buildQuery({ render })}`,
        { method: 'GET' }
      );
    }

    throw new Error('invalid_source');
  }

  async _downloadResponse(ref) {
    const source = String(ref?.source || '').toLowerCase();
    const docId = ref?.docId;
    if (!docId) throw new Error('missing_doc_id');

    if (source === DOCUMENT_SOURCE.RAGFLOW) {
      const datasetName = ref?.datasetName || ref?.dataset || '';
      if (!datasetName) throw new Error('missing_dataset');
      const filename = ref?.filename || ref?.title || '';
      const path = `/api/documents/ragflow/${encodeURIComponent(docId)}/download${buildQuery({
        dataset: datasetName,
        filename,
      })}`;
      const resp = await httpClient.request(path, { method: 'GET' });
      if (resp.ok) return resp;

      const data = await parseMaybeJson(resp);
      const message = data?.detail || data?.message || `download_failed (${resp.status})`;
      const err = new Error(message);
      err.status = resp.status;
      err.data = data;
      throw err;
    }

    if (source === DOCUMENT_SOURCE.KNOWLEDGE) {
      const resp = await httpClient.request(`/api/documents/knowledge/${encodeURIComponent(docId)}/download`, { method: 'GET' });
      if (resp.ok) return resp;

      const data = await parseMaybeJson(resp);
      const message = data?.detail || data?.message || `download_failed (${resp.status})`;
      const err = new Error(message);
      err.status = resp.status;
      err.data = data;
      throw err;
    }

    if (source === DOCUMENT_SOURCE.PATENT) {
      const sessionId = String(ref?.sessionId || '').trim();
      if (!sessionId) throw new Error('missing_session_id');
      const resp = await httpClient.request(
        `/api/patent-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(docId)}/download`,
        { method: 'GET' }
      );
      if (resp.ok) return resp;

      const data = await parseMaybeJson(resp);
      const message = data?.detail || data?.message || `download_failed (${resp.status})`;
      const err = new Error(message);
      err.status = resp.status;
      err.data = data;
      throw err;
    }

    if (source === DOCUMENT_SOURCE.PAPER) {
      const sessionId = String(ref?.sessionId || '').trim();
      if (!sessionId) throw new Error('missing_session_id');
      const resp = await httpClient.request(
        `/api/paper-download/sessions/${encodeURIComponent(sessionId)}/items/${encodeURIComponent(docId)}/download`,
        { method: 'GET' }
      );
      if (resp.ok) return resp;

      const data = await parseMaybeJson(resp);
      const message = data?.detail || data?.message || `download_failed (${resp.status})`;
      const err = new Error(message);
      err.status = resp.status;
      err.data = data;
      throw err;
    }

    throw new Error('invalid_source');
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
    if (ids.length === 0) throw new Error('no_documents_selected');

    const resp = await httpClient.request(`/api/documents/knowledge/batch/download`, {
      method: 'POST',
      body: JSON.stringify({ doc_ids: ids }),
    });
    if (!resp.ok) {
      const data = await parseMaybeJson(resp);
      const message = data?.detail || data?.message || `batch_download_failed (${resp.status})`;
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
    if (docs.length === 0) throw new Error('no_documents_selected');

    const resp = await httpClient.request(`/api/documents/ragflow/batch/download`, {
      method: 'POST',
      body: JSON.stringify({ documents: docs }),
    });
    if (!resp.ok) {
      const data = await parseMaybeJson(resp);
      const message = data?.detail || data?.message || `batch_download_failed (${resp.status})`;
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
    if (!docId) throw new Error('missing_doc_id');

    if (source === DOCUMENT_SOURCE.RAGFLOW) {
      const datasetName = ref?.datasetName || ref?.dataset || '';
      if (!datasetName) throw new Error('missing_dataset');
      return httpClient.requestJson(
        `/api/documents/ragflow/${encodeURIComponent(docId)}${buildQuery({ dataset_name: datasetName })}`,
        { method: 'DELETE' }
      );
    }

    if (source === DOCUMENT_SOURCE.KNOWLEDGE) {
      return httpClient.requestJson(`/api/documents/knowledge/${encodeURIComponent(docId)}`, { method: 'DELETE' });
    }

    throw new Error('invalid_source');
  }

  async uploadKnowledge(file, kbId) {
    if (!file) throw new Error('missing_file');
    if (!kbId) throw new Error('missing_kb_id');
    const formData = new FormData();
    formData.append('file', file);
    return httpClient.requestJson(`/api/documents/knowledge/upload${buildQuery({ kb_id: kbId })}`, {
      method: 'POST',
      body: formData,
      includeContentType: false,
    });
  }
}

const documentClient = new DocumentClient();
export default documentClient;
