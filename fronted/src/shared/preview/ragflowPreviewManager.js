import mammoth from 'mammoth';
import { excelBlobToSheetsHtml, isExcelFilename } from './excelPreview';

const isDocxFilename = (name) => String(name || '').toLowerCase().endsWith('.docx');

/**
 * 统一 Ragflow 文档与本地知识库文档的查看/预览流程。
 *
 * 约定：
 * - getPreviewJson: ({ docId, dataset }) -> { type, filename, content, ... }
 * - getDownloadBlob: ({ docId, dataset, filename }) -> Blob（原始文件字节）
 *
 * 返回值按 `type` 供调用方渲染：
 * - excel: { type:'excel', filename, sheets, docId, dataset }
 * - docx:  { type:'docx', filename, html, docId, dataset }
 * - 其他类型直接透传预览结果（如 text/image/pdf/html/unsupported）
 *
 * 说明：知识库文档的 `dataset` 为可选字段，调用方在不需要时会忽略它。
 */
export const loadDocumentPreview = async ({ docId, dataset, title, getPreviewJson, getDownloadBlob }) => {
  const t0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
  const mark = (step, extra = {}) => {
    const now = (typeof performance !== 'undefined' ? performance.now() : Date.now());
    const elapsedMs = Math.round(now - t0);
    // eslint-disable-next-line no-console
    console.info('[PreviewTrace][Manager]', step, { docId, dataset, title, elapsedMs, ...extra });
  };
  if (!docId) throw new Error('缺少文档 ID，无法预览。');
  if (typeof getPreviewJson !== 'function') throw new Error('必须提供 getPreviewJson 方法。');

  mark('getPreviewJson:start');
  const data = await getPreviewJson({ docId, dataset });
  mark('getPreviewJson:done', { type: data?.type, filename: data?.filename, sourceFilename: data?.source_filename });
  // 某些后端会把 `filename` 返回为渲染后的文件名（如 *.html），
  // 并把原始文件名保存在 `source_filename` 中。类型识别优先使用原始文件名。
  const resolvedName = String(data?.source_filename || data?.filename || title || '');

  // 当前用户若没有下载权限，就不能调用下载接口。
  // 此时依赖后端返回的预览结果（后端可能已转成 HTML）。
  const canUseDownload = typeof getDownloadBlob === 'function';

  // 优先复用后端提供的 Excel 预览数据，避免额外下载一次。
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

// 向后兼容的别名（旧代码仍在使用这个导出名）。
export const loadRagflowPreview = loadDocumentPreview;
