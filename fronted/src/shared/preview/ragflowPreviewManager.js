import mammoth from 'mammoth';
import { excelBlobToSheetsHtml, isExcelFilename } from './excelPreview';

const isDocxFilename = (name) => String(name || '').toLowerCase().endsWith('.docx');

/**
 * Unifies the "view/preview" flow for Ragflow documents across Chat/Search/Browser.
 *
 * Contract:
 * - getPreviewJson: ({ docId, dataset }) -> { type, filename, content, ... }
 * - getDownloadBlob: ({ docId, dataset, filename }) -> Blob (original file bytes)
 *
 * Returns an object that callers can render by `type`:
 * - excel: { type:'excel', filename, sheets, docId, dataset }
 * - docx:  { type:'docx', filename, html, docId, dataset }
 * - passthrough preview json for other types (text/image/pdf/html/unsupported...)
 */
export const loadRagflowPreview = async ({ docId, dataset, title, getPreviewJson, getDownloadBlob }) => {
  if (!docId) throw new Error('缺少文档信息，无法预览');
  if (typeof getPreviewJson !== 'function') throw new Error('getPreviewJson is required');

  const data = await getPreviewJson({ docId, dataset });
  // Some backends may return `filename` as the rendered filename (e.g. *.html),
  // and keep the original as `source_filename`. Prefer the original for type detection.
  const resolvedName = String(data?.source_filename || data?.filename || title || '');

  // If the current user doesn't have download permission, we must not call the download endpoint.
  // In that case rely on the backend preview response (which may convert to HTML).
  const canUseDownload = typeof getDownloadBlob === 'function';

  if (isExcelFilename(resolvedName) && canUseDownload) {
    const blob = await getDownloadBlob({ docId, dataset, filename: resolvedName });
    const { sheets } = await excelBlobToSheetsHtml(blob);
    return { type: 'excel', filename: resolvedName, sheets, docId, dataset };
  }

  if (isDocxFilename(resolvedName) && canUseDownload) {
    const blob = await getDownloadBlob({ docId, dataset, filename: resolvedName });
    const arrayBuffer = await blob.arrayBuffer();
    const result = await mammoth.convertToHtml({ arrayBuffer });
    return { type: 'docx', filename: resolvedName, html: result.value || '', docId, dataset };
  }

  return { ...(data || {}), filename: String(data?.filename || title || resolvedName) };
};
