import mammoth from 'mammoth';
import { excelBlobToSheetsHtml, isExcelFilename } from './excelPreview';

const isDocxFilename = (name) => String(name || '').toLowerCase().endsWith('.docx');

/**
 * Unifies the "view/preview" flow for both Ragflow and local Knowledge documents.
 *
 * Contract:
 * - getPreviewJson: ({ docId, dataset }) -> { type, filename, content, ... }
 * - getDownloadBlob: ({ docId, dataset, filename }) -> Blob (original file bytes)
 *
 * Returns an object that callers can render by `type`:
 * - excel: { type:'excel', filename, sheets, docId, dataset }
 * - docx:  { type:'docx', filename, html, docId, dataset }
 * - passthrough preview json for other types (text/image/pdf/html/unsupported...)
 *
 * Note: `dataset` is optional for Knowledge docs; it will be ignored by callers if not needed.
 */
export const loadDocumentPreview = async ({ docId, dataset, title, getPreviewJson, getDownloadBlob }) => {
  const t0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
  const mark = (step, extra = {}) => {
    const now = (typeof performance !== 'undefined' ? performance.now() : Date.now());
    const elapsedMs = Math.round(now - t0);
    // eslint-disable-next-line no-console
    console.info('[PreviewTrace][Manager]', step, { docId, dataset, title, elapsedMs, ...extra });
  };
  if (!docId) throw new Error('Missing document id; cannot preview.');
  if (typeof getPreviewJson !== 'function') throw new Error('getPreviewJson is required');

  mark('getPreviewJson:start');
  const data = await getPreviewJson({ docId, dataset });
  mark('getPreviewJson:done', { type: data?.type, filename: data?.filename, sourceFilename: data?.source_filename });
  // Some backends may return `filename` as the rendered filename (e.g. *.html),
  // and keep the original as `source_filename`. Prefer the original for type detection.
  const resolvedName = String(data?.source_filename || data?.filename || title || '');

  // If the current user doesn't have download permission, we must not call the download endpoint.
  // In that case rely on the backend preview response (which may convert to HTML).
  const canUseDownload = typeof getDownloadBlob === 'function';

  // Prefer backend-provided Excel preview payload to avoid an extra download round-trip.
  if (isExcelFilename(resolvedName) && data?.type === 'excel' && data?.sheets) {
    mark('excelPassthrough:done', { sheetCount: Object.keys(data.sheets || {}).length });
    return { ...(data || {}), filename: String(data?.filename || title || resolvedName), docId, dataset };
  }

  if (isExcelFilename(resolvedName) && canUseDownload) {
    mark('excelDownload:start', { resolvedName });
    const blob = await getDownloadBlob({ docId, dataset, filename: resolvedName });
    mark('excelDownload:done', { size: blob?.size });
    const { sheets } = await excelBlobToSheetsHtml(blob);
    mark('excelToHtml:done', { sheetCount: Object.keys(sheets || {}).length });
    return { type: 'excel', filename: resolvedName, sheets, docId, dataset, watermark: data?.watermark || null };
  }

  if (isDocxFilename(resolvedName) && canUseDownload) {
    mark('docxDownload:start', { resolvedName });
    const blob = await getDownloadBlob({ docId, dataset, filename: resolvedName });
    mark('docxDownload:done', { size: blob?.size });
    const arrayBuffer = await blob.arrayBuffer();
    const result = await mammoth.convertToHtml({ arrayBuffer });
    mark('docxToHtml:done', { htmlLength: String(result?.value || '').length });
    return { type: 'docx', filename: resolvedName, html: result.value || '', docId, dataset, watermark: data?.watermark || null };
  }

  mark('passthrough:done', { resolvedName, type: data?.type });
  return { ...(data || {}), filename: String(data?.filename || title || resolvedName) };
};

// Backward compatible alias (older code imports this name).
export const loadRagflowPreview = loadDocumentPreview;
