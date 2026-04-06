import { authBackendUrl } from '../../../config/backend';
import { httpClient } from '../../../shared/http/httpClient';

const normalizeObjectField = (response, fieldName, action) => {
  if (!response || typeof response !== 'object' || Array.isArray(response)) {
    throw new Error(`${action}_invalid_payload`);
  }
  const value = response[fieldName];
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return value;
};

const normalizeBatchTransferItem = (item, action) => {
  if (!item || typeof item !== 'object' || Array.isArray(item)) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof item.ok !== 'boolean') {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof item.operation !== 'string' || !item.operation.trim()) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof item.source_dataset_name !== 'string' || !item.source_dataset_name.trim()) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof item.target_dataset_name !== 'string' || !item.target_dataset_name.trim()) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof item.source_doc_id !== 'string' || !item.source_doc_id.trim()) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof item.source_deleted !== 'boolean' || typeof item.parse_triggered !== 'boolean') {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof item.parse_error !== 'string') {
    throw new Error(`${action}_invalid_payload`);
  }
  return {
    ok: item.ok,
    operation: item.operation,
    sourceDatasetName: item.source_dataset_name,
    targetDatasetName: item.target_dataset_name,
    sourceDocId: item.source_doc_id,
    targetDocId: typeof item.target_doc_id === 'string' ? item.target_doc_id : '',
    filename: typeof item.filename === 'string' ? item.filename : '',
    sourceDeleted: item.source_deleted,
    parseTriggered: item.parse_triggered,
    parseError: item.parse_error,
  };
};

const normalizeBatchTransferFailure = (item, action) => {
  if (!item || typeof item !== 'object' || Array.isArray(item)) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof item.doc_id !== 'string') {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof item.source_dataset_name !== 'string') {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof item.target_dataset_name !== 'string') {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof item.detail !== 'string' || !item.detail.trim()) {
    throw new Error(`${action}_invalid_payload`);
  }
  return {
    docId: item.doc_id,
    sourceDatasetName: item.source_dataset_name,
    targetDatasetName: item.target_dataset_name,
    detail: item.detail,
  };
};

const normalizeBatchTransferResult = (response, action) => {
  const result = normalizeObjectField(response, 'result', action);
  if (typeof result.ok !== 'boolean') {
    throw new Error(`${action}_invalid_payload`);
  }
  if (typeof result.operation !== 'string' || !result.operation.trim()) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (!Number.isFinite(result.total) || !Number.isFinite(result.success_count) || !Number.isFinite(result.failed_count)) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (!Array.isArray(result.results) || !Array.isArray(result.failed)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return {
    ok: result.ok,
    operation: result.operation,
    total: Number(result.total),
    successCount: Number(result.success_count),
    failedCount: Number(result.failed_count),
    results: result.results.map((item) => normalizeBatchTransferItem(item, action)),
    failed: result.failed.map((item) => normalizeBatchTransferFailure(item, action)),
  };
};

export const documentBrowserApi = {
  async listDocuments(datasetName = '\u5c55\u5385') {
    const query = new URLSearchParams({
      dataset_name: String(datasetName || ''),
    }).toString();
    const response = await httpClient.requestJson(authBackendUrl(`/api/ragflow/documents?${query}`), {
      method: 'GET',
    });
    if (!Array.isArray(response?.documents)) {
      throw new Error('ragflow_document_list_invalid_payload');
    }
    return response.documents;
  },

  async transferDocument(docId, sourceDatasetName, targetDatasetName, operation = 'copy') {
    const response = await httpClient.requestJson(
      authBackendUrl(`/api/ragflow/documents/${encodeURIComponent(docId)}/transfer`),
      {
        method: 'POST',
        body: JSON.stringify({
          source_dataset_name: sourceDatasetName,
          target_dataset_name: targetDatasetName,
          operation,
        }),
      }
    );
    return normalizeObjectField(response, 'result', 'ragflow_document_transfer');
  },

  async transferDocumentsBatch(items, operation = 'copy') {
    const payloadItems = Array.isArray(items) ? items : [];
    const response = await httpClient.requestJson(authBackendUrl('/api/ragflow/documents/transfer/batch'), {
      method: 'POST',
      body: JSON.stringify({
        operation,
        items: payloadItems.map((item) => ({
          doc_id: item?.docId,
          source_dataset_name: item?.sourceDatasetName,
          target_dataset_name: item?.targetDatasetName,
        })),
      }),
    });
    return normalizeBatchTransferResult(response, 'ragflow_document_transfer_batch');
  },
};
