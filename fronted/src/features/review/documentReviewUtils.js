import documentClient, { DOCUMENT_SOURCE } from '../../shared/documents/documentClient';

export function isMarkdownFile(filename) {
  if (!filename) return false;
  const ext = filename.toLowerCase().split('.').pop();
  return ext === 'md' || ext === 'markdown';
}

export function isPlainTextFile(filename) {
  if (!filename) return false;
  const ext = filename.toLowerCase().split('.').pop();
  return ext === 'txt' || ext === 'ini' || ext === 'log';
}

export function isTextComparable(filename) {
  return isMarkdownFile(filename) || isPlainTextFile(filename);
}

export function countLines(value) {
  const normalized = String(value || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  if (!normalized) return 0;
  return normalized.split('\n').length;
}

export async function fetchKnowledgePreviewText(docId) {
  const data = await documentClient.preview({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
  if (data?.type !== 'text') {
    throw new Error(data?.message || '预览失败：当前不是文本类文档。');
  }
  return String(data.content || '');
}

export async function loadReviewDatasets(knowledgeApi) {
  const data = await knowledgeApi.listRagflowDatasets();
  return data?.datasets || [];
}

export async function loadPendingReviewDocuments(knowledgeApi, selectedDataset) {
  if (selectedDataset === '') {
    const data = await knowledgeApi.listLocalDocuments({ status: 'pending' });
    return data?.documents || [];
  }
  const data = await knowledgeApi.listLocalDocuments({ status: 'pending', kb_id: selectedDataset });
  return data?.documents || [];
}

export async function collectConflictChecks(documents, reviewApi) {
  return Promise.all(
    (documents || []).map(async (doc) => {
      try {
        const conflict = await reviewApi.getConflict(doc.doc_id);
        return { doc, conflict };
      } catch (err) {
        return { doc, conflictError: err?.message || '冲突检查失败' };
      }
    }),
  );
}

export function buildApproveBatchSummary(conflictChecks, result) {
  const conflicted = conflictChecks.filter((item) => item.conflict?.conflict && item.conflict?.existing);
  const checkFailed = conflictChecks.filter((item) => item.conflictError);
  return {
    mode: 'approve',
    successCount: Number(result?.success_count || 0),
    failedCount: Number(result?.failed_count || 0),
    conflicted: conflicted.map((item) => ({
      docId: item.doc.doc_id,
      filename: item.doc.filename,
      detail: item.conflict?.existing?.filename
        ? `检测到重复文档，已存在文件：${item.conflict.existing.filename}`
        : '检测到重复文档，但未获取到已存在文件详情',
      existing: item.conflict?.existing || null,
      normalized: item.conflict?.normalized_name || '',
    })),
    checkFailed: checkFailed.map((item) => ({
      docId: item.doc.doc_id,
      filename: item.doc.filename,
      detail: item.conflictError,
    })),
    failedItems: result?.failed_items || [],
  };
}

export function buildRejectBatchSummary(result) {
  return {
    mode: 'reject',
    successCount: Number(result?.success_count || 0),
    failedCount: Number(result?.failed_count || 0),
    conflicted: [],
    checkFailed: [],
    failedItems: result?.failed_items || [],
  };
}

export function buildBatchSummaryText(batchReviewSummary) {
  if (!batchReviewSummary) return '';
  const lines = [
    batchReviewSummary.mode === 'approve' ? '批量通过结果' : '批量驳回结果',
    `成功：${batchReviewSummary.successCount}，失败：${batchReviewSummary.failedCount}，冲突：${batchReviewSummary.conflicted.length}，检查失败：${batchReviewSummary.checkFailed.length}`,
  ];

  if (batchReviewSummary.failedItems.length > 0) {
    lines.push('失败明细：');
    batchReviewSummary.failedItems.forEach((item) => lines.push(`${item.doc_id}: ${item.detail}`));
  }
  if (batchReviewSummary.conflicted.length > 0) {
    lines.push('冲突明细：');
    batchReviewSummary.conflicted.forEach((item) => lines.push(`${item.filename}: ${item.detail}`));
  }
  if (batchReviewSummary.checkFailed.length > 0) {
    lines.push('检查失败明细：');
    batchReviewSummary.checkFailed.forEach((item) => lines.push(`${item.filename}: ${item.detail}`));
  }

  return lines.join('\n');
}
