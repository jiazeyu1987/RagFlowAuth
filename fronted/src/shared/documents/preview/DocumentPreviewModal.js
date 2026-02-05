import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useEscapeClose } from '../../hooks/useEscapeClose';
import { ensureTablePreviewStyles } from '../../preview/tablePreviewStyles';
import { isMarkdownFilename, MarkdownPreview } from '../../preview/markdownPreview';
import { loadDocumentPreview } from '../../preview/ragflowPreviewManager';
import documentClient, { DOCUMENT_SOURCE } from '../documentClient';
import * as pdfjsLib from 'pdfjs-dist';

// Configure PDF.js worker to use local file (CRA public folder).
pdfjsLib.GlobalWorkerOptions.workerSrc = process.env.PUBLIC_URL + '/js/pdf.worker.min.mjs';

const Spinner = ({ size = 16 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    xmlns="http://www.w3.org/2000/svg"
    style={{
      animation: 'spin 1s linear infinite',
    }}
  >
    <circle
      cx="12"
      cy="12"
      r="10"
      stroke="currentColor"
      strokeWidth="4"
      fill="none"
      strokeDasharray="32"
      strokeDashoffset="32"
      style={{
        strokeDashoffset: '32',
        animation: 'dash 1.5s ease-in-out infinite',
      }}
    />
  </svg>
);

const injectSpinnerStyles = () => {
  if (typeof document !== 'undefined' && !document.getElementById('spinner-styles')) {
    const style = document.createElement('style');
    style.id = 'spinner-styles';
    style.textContent = `
      @keyframes spin { 100% { transform: rotate(360deg); } }
      @keyframes dash {
        0% { stroke-dasharray: 1, 150; stroke-dashoffset: 0; }
        50% { stroke-dasharray: 90, 150; stroke-dashoffset: -35; }
        100% { stroke-dasharray: 90, 150; stroke-dashoffset: -124; }
      }
    `;
    document.head.appendChild(style);
  }
};

if (typeof window !== 'undefined') injectSpinnerStyles();

const isPlainTextFile = (filename) => {
  const ext = String(filename || '').toLowerCase().split('.').pop();
  return ['txt', 'ini', 'log'].includes(ext);
};

const isDocxFile = (filename) => String(filename || '').toLowerCase().endsWith('.docx');
const isExcelFile = (filename) => {
  const ext = String(filename || '').toLowerCase().split('.').pop();
  return ext === 'xlsx' || ext === 'xls';
};
const isCsvFile = (filename) => String(filename || '').toLowerCase().endsWith('.csv');
const isImageFile = (filename) => {
  const ext = String(filename || '').toLowerCase().split('.').pop();
  return ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'svg', 'webp'].includes(ext);
};

const escapeHtml = (s) =>
  String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

const detectDelimiter = (line) => {
  const candidates = [',', ';', '\t'];
  let best = ',';
  let bestCount = -1;
  for (const d of candidates) {
    const c = (line.match(new RegExp(`\\${d}`, 'g')) || []).length;
    if (c > bestCount) {
      bestCount = c;
      best = d;
    }
  }
  return best;
};

const parseDelimited = (text, delimiter) => {
  const rows = [];
  let row = [];
  let cell = '';
  let inQuotes = false;

  const s = String(text ?? '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (inQuotes) {
      if (ch === '"') {
        const next = s[i + 1];
        if (next === '"') {
          cell += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        cell += ch;
      }
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
      continue;
    }
    if (ch === delimiter) {
      row.push(cell);
      cell = '';
      continue;
    }
    if (ch === '\n') {
      row.push(cell);
      cell = '';
      if (!(row.length === 1 && row[0] === '' && rows.length === 0)) rows.push(row);
      row = [];
      continue;
    }
    cell += ch;
  }
  row.push(cell);
  if (row.length > 1 || row[0] !== '') rows.push(row);
  return rows;
};

const rowsToHtmlTable = (rows, { maxRows = 2000, maxCols = 100 } = {}) => {
  const limitedRows = rows.slice(0, maxRows);
  const colCount = Math.min(maxCols, Math.max(0, ...limitedRows.map((r) => (Array.isArray(r) ? r.length : 0))));

  const head = limitedRows[0] || [];
  const body = limitedRows.slice(1);

  const thead =
    colCount > 0
      ? `<thead><tr>${Array.from({ length: colCount })
          .map((_, i) => `<th>${escapeHtml(head[i] ?? '')}</th>`)
          .join('')}</tr></thead>`
      : '';

  const tbody = `<tbody>${body
    .map((r) => {
      const cells = Array.from({ length: colCount })
        .map((_, i) => `<td>${escapeHtml(r?.[i] ?? '')}</td>`)
        .join('');
      return `<tr>${cells}</tr>`;
    })
    .join('')}</tbody>`;

  const table = `<table>${thead}${tbody}</table>`;
  const truncated = rows.length > maxRows || rows.some((r) => (r?.length || 0) > maxCols);
  return { html: table, truncated };
};

const base64ToBytes = (b64) => {
  const binary = atob(b64 || '');
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
};

const mimeFromImageType = (imageType) => {
  const t = String(imageType || '').toLowerCase();
  if (t === 'jpg') return 'image/jpeg';
  if (t === 'svg') return 'image/svg+xml';
  return t ? `image/${t}` : 'application/octet-stream';
};

export const DocumentPreviewModal = ({ open, target, onClose, canDownloadFiles = false }) => {
  const closePreview = typeof onClose === 'function' ? onClose : () => {};
  useEscapeClose(open, closePreview);

  // Inject shared table styles for Excel/CSV/DOCX preview
  useEffect(() => {
    ensureTablePreviewStyles();
  }, []);

  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [previewDocName, setPreviewDocName] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [markdownContent, setMarkdownContent] = useState(null);
  const [plainTextContent, setPlainTextContent] = useState(null);
  const [docxContent, setDocxContent] = useState(null);
  const [excelData, setExcelData] = useState(null);
  const [excelRenderHint, setExcelRenderHint] = useState(null);

  // PDF state (same behavior as DocumentBrowser)
  const [pdfDocument, setPdfDocument] = useState(null);
  const [pdfNumPages, setPdfNumPages] = useState(0);
  const [pdfCurrentPage, setPdfCurrentPage] = useState(1);
  const [pdfScale, setPdfScale] = useState(1.5);
  const canvasRef = useRef(null);

  // Image state
  const [imageScale, setImageScale] = useState(1);
  const [imageRotation, setImageRotation] = useState(0);

  const effectiveName = useMemo(() => {
    const n = String(previewDocName || target?.filename || target?.title || '');
    return n || (target?.docId ? `document_${target.docId}` : '');
  }, [previewDocName, target]);

  const resetPreviewState = () => {
    setPreviewError(null);
    setPreviewDocName(null);
    setMarkdownContent(null);
    setPlainTextContent(null);
    setDocxContent(null);
    setExcelData(null);
    setExcelRenderHint(null);
    setPdfDocument(null);
    setPdfNumPages(0);
    setPdfCurrentPage(1);
    setPdfScale(1.5);
    if (previewUrl) window.URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setImageScale(1);
    setImageRotation(0);
  };

  useEffect(() => {
    if (!open) return;
    if (!target?.source || !target?.docId) return;

    const run = async () => {
      setPreviewLoading(true);
      setPreviewError(null);

      try {
        resetPreviewState();

        const source = target.source;
        const docId = target.docId;
        const datasetName = target.datasetName;
        const title = target.filename || target.title || `document_${docId}`;

        setPreviewDocName(title);

        const payload = await loadDocumentPreview({
          docId,
          dataset: datasetName,
          title,
          getPreviewJson: async ({ docId, dataset }) =>
            documentClient.preview({
              source,
              docId,
              datasetName: source === DOCUMENT_SOURCE.RAGFLOW ? dataset : undefined,
            }),
          getDownloadBlob: canDownloadFiles
            ? async ({ docId, dataset, filename }) =>
                documentClient.downloadBlob({
                  source,
                  docId,
                  datasetName: source === DOCUMENT_SOURCE.RAGFLOW ? dataset : undefined,
                  filename,
                })
            : undefined,
        });

        const resolvedName = String(payload?.filename || title);
        setPreviewDocName(resolvedName);

        if (isImageFile(resolvedName)) {
          setImageScale(1);
          setImageRotation(0);
        }

        if (payload?.type === 'excel') {
          setExcelData(payload.sheets || {});
          setExcelRenderHint(
            isExcelFile(resolvedName)
              ? '如果 Excel 里包含流程图/形状，表格模式可能看不到；可点“原样预览(HTML)”查看。'
              : null
          );
          return;
        }

        if (payload?.type === 'docx') {
          setDocxContent(payload.html || '');
          return;
        }

        if (payload?.type === 'text') {
          const text = String(payload.content || '');
          if (isCsvFile(resolvedName)) {
            const firstLine = String(text || '').split(/\r?\n/)[0] || '';
            const delimiter = detectDelimiter(firstLine);
            const rows = parseDelimited(text, delimiter);
            const { html } = rowsToHtmlTable(rows);
            setExcelData({ CSV: html });
            setExcelRenderHint(null);
            return;
          }
          if (isMarkdownFilename(resolvedName)) setMarkdownContent(text);
          else setPlainTextContent(text);
          return;
        }

        if (payload?.type === 'html') {
          if (!payload?.content) throw new Error(payload?.message || 'Unsupported preview');
          const bytes = base64ToBytes(payload.content);
          const blob = new Blob([bytes], { type: 'text/html; charset=utf-8' });
          const url = window.URL.createObjectURL(blob);
          setPreviewUrl(url);
          return;
        }

        if (payload?.type === 'pdf') {
          if (!payload?.content) throw new Error(payload?.message || 'PDF preview failed');
          const bytes = base64ToBytes(payload.content);
          const blob = new Blob([bytes], { type: 'application/pdf' });
          const url = window.URL.createObjectURL(blob);
          const arrayBuffer = await blob.arrayBuffer();
          const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
          const pdf = await loadingTask.promise;
          setPdfDocument(pdf);
          setPdfNumPages(pdf.numPages);
          setPdfCurrentPage(1);
          setPreviewUrl(url);
          return;
        }

        if (payload?.type === 'image') {
          if (!payload?.content) throw new Error(payload?.message || 'Image preview failed');
          const bytes = base64ToBytes(payload.content);
          const mime = payload?.mime_type || mimeFromImageType(payload?.image_type);
          const blob = new Blob([bytes], { type: mime });
          const url = window.URL.createObjectURL(blob);
          setPreviewUrl(url);
          return;
        }

        throw new Error(payload?.message || 'Unsupported preview');
      } catch (e) {
        setPreviewError(e?.message || '预览失败');
      } finally {
        setPreviewLoading(false);
      }
    };

    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, target?.source, target?.docId, target?.datasetName, target?.filename, target?.title, canDownloadFiles]);

  // Render PDF page when document or page number changes
  useEffect(() => {
    if (!open) return;
    if (!pdfDocument || !canvasRef.current) return;

    const renderPage = async () => {
      const page = await pdfDocument.getPage(pdfCurrentPage);
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');
      const viewport = page.getViewport({ scale: pdfScale });
      canvas.height = viewport.height;
      canvas.width = viewport.width;
      await page.render({ canvasContext: context, viewport }).promise;
    };

    renderPage();
  }, [open, pdfDocument, pdfCurrentPage, pdfScale]);

  useEffect(() => {
    if (!open) return;
    return () => {
      try {
        if (previewUrl) window.URL.revokeObjectURL(previewUrl);
      } catch {
        // ignore
      }
    };
  }, [open, previewUrl]);

  if (!open) return null;

  return (
    <div
      onClick={closePreview}
      data-testid="document-preview-modal"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        zIndex: 1100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          maxWidth: '90vw',
          maxHeight: '90vh',
          width: '90%',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
        }}
      >
        <div
          style={{
            padding: '16px 24px',
            borderBottom: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#1f2937' }}>{effectiveName}</h3>
          <button
            onClick={closePreview}
            data-testid="document-preview-close"
            style={{
              background: 'none',
              border: 'none',
              fontSize: '1.5rem',
              cursor: 'pointer',
              color: '#6b7280',
              padding: '0',
              width: '32px',
              height: '32px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            onMouseEnter={(e) => (e.target.style.color = '#1f2937')}
            onMouseLeave={(e) => (e.target.style.color = '#6b7280')}
          >
            ×
          </button>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: '24px' }}>
          {previewLoading ? (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '400px',
                gap: '16px',
              }}
            >
              <Spinner size={32} />
              <div style={{ color: '#6b7280' }}>加载中...</div>
            </div>
          ) : previewError ? (
            <div
              style={{
                padding: '16px 18px',
                border: '1px solid #fecaca',
                backgroundColor: '#fef2f2',
                color: '#991b1b',
                borderRadius: '8px',
                fontSize: '0.95rem',
                lineHeight: 1.6,
              }}
            >
              {previewError}
            </div>
          ) : isMarkdownFilename(effectiveName) ? (
            <MarkdownPreview content={markdownContent || ''} />
          ) : isPlainTextFile(effectiveName) ? (
            <div
              style={{
                padding: '24px',
                backgroundColor: 'white',
                borderRadius: '8px',
                height: '70vh',
                overflow: 'auto',
                border: '1px solid #e5e7eb',
              }}
            >
              <pre
                style={{
                  margin: 0,
                  fontSize: '0.875rem',
                  lineHeight: '1.6',
                  color: '#111827',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontFamily:
                    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
                }}
              >
                {plainTextContent}
              </pre>
            </div>
          ) : isDocxFile(effectiveName) ? (
            <div
              className="table-preview"
              style={{
                padding: '24px',
                backgroundColor: 'white',
                borderRadius: '8px',
                height: '70vh',
                overflow: 'auto',
                border: '1px solid #e5e7eb',
              }}
            >
              <div
                style={{
                  fontSize: '0.875rem',
                  lineHeight: '1.6',
                  color: '#1f2937',
                }}
                dangerouslySetInnerHTML={{ __html: docxContent || '' }}
              />
            </div>
          ) : (isExcelFile(effectiveName) || isCsvFile(effectiveName)) && excelData ? (
            <div
              className="table-preview"
              style={{
                padding: '24px',
                backgroundColor: 'white',
                borderRadius: '8px',
                height: '70vh',
                overflow: 'auto',
                border: '1px solid #e5e7eb',
              }}
            >
              {excelRenderHint && isExcelFile(effectiveName) && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '10px 12px',
                    backgroundColor: '#eff6ff',
                    border: '1px solid #bfdbfe',
                    borderRadius: '8px',
                    color: '#1e3a8a',
                    fontSize: '0.9rem',
                    marginBottom: '16px',
                  }}
                >
                  <div style={{ flex: 1 }}>{excelRenderHint}</div>
                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        setPreviewError(null);
                        setPreviewLoading(true);
                        const source = target?.source;
                        const docId = target?.docId;
                        const datasetName = target?.datasetName;
                        if (!source || !docId) throw new Error('缺少文档信息，无法预览');

                        const data = await documentClient.preview({
                          source,
                          docId,
                          datasetName: source === DOCUMENT_SOURCE.RAGFLOW ? datasetName : undefined,
                        });
                        if (data?.type !== 'html' || !data?.content) {
                          throw new Error(data?.message || '此文件类型不支持原样预览(HTML)');
                        }
                        const bytes = base64ToBytes(data.content);
                        const htmlBlob = new Blob([bytes], { type: 'text/html; charset=utf-8' });
                        const url = window.URL.createObjectURL(htmlBlob);
                        setPdfDocument(null);
                        setPdfNumPages(0);
                        setPdfCurrentPage(1);
                        if (previewUrl) window.URL.revokeObjectURL(previewUrl);
                        setPreviewUrl(url);
                        if (data?.filename) setPreviewDocName(data.filename);
                        setExcelData(null);
                        setExcelRenderHint(null);
                      } catch (e) {
                        setPreviewError(e?.message || '预览失败');
                      } finally {
                        setPreviewLoading(false);
                      }
                    }}
                    style={{
                      padding: '8px 12px',
                      backgroundColor: '#3b82f6',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.85rem',
                      flexShrink: 0,
                    }}
                  >
                    原样预览(HTML)
                  </button>
                </div>
              )}

              {Object.keys(excelData).map((sheetName, index) => (
                <div key={sheetName} style={{ marginBottom: index < Object.keys(excelData).length - 1 ? '32px' : 0 }}>
                  <h3
                    style={{
                      fontSize: '1.1rem',
                      fontWeight: 'bold',
                      marginBottom: '12px',
                      color: '#1f2937',
                      borderBottom: '2px solid #e5e7eb',
                      paddingBottom: '8px',
                    }}
                  >
                    {sheetName}
                  </h3>
                  <div
                    style={{
                      fontSize: '0.875rem',
                      overflow: 'auto',
                    }}
                    dangerouslySetInnerHTML={{ __html: excelData[sheetName] }}
                  />
                </div>
              ))}
            </div>
          ) : pdfDocument ? (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                height: '70vh',
                backgroundColor: '#525659',
                borderRadius: '8px',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  padding: '12px 16px',
                  backgroundColor: '#323639',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  borderBottom: '1px solid #4a4e51',
                  flexWrap: 'wrap',
                }}
              >
                <button
                  onClick={() => setPdfCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={pdfCurrentPage <= 1}
                  style={{
                    padding: '6px 12px',
                    fontSize: '0.875rem',
                    backgroundColor: pdfCurrentPage <= 1 ? '#6b7280' : '#374151',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: pdfCurrentPage <= 1 ? 'not-allowed' : 'pointer',
                  }}
                >
                  上一页
                </button>
                <span style={{ color: 'white', fontSize: '0.875rem' }}>
                  {pdfCurrentPage} / {pdfNumPages}
                </span>
                <button
                  onClick={() => setPdfCurrentPage((p) => Math.min(pdfNumPages, p + 1))}
                  disabled={pdfCurrentPage >= pdfNumPages}
                  style={{
                    padding: '6px 12px',
                    fontSize: '0.875rem',
                    backgroundColor: pdfCurrentPage >= pdfNumPages ? '#6b7280' : '#374151',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: pdfCurrentPage >= pdfNumPages ? 'not-allowed' : 'pointer',
                  }}
                >
                  下一页
                </button>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <button
                    onClick={() => setPdfScale((s) => Math.max(0.5, Math.round((s - 0.25) * 100) / 100))}
                    style={{
                      padding: '6px 10px',
                      fontSize: '0.875rem',
                      backgroundColor: '#374151',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                    }}
                  >
                    -
                  </button>
                  <span style={{ color: 'white', fontSize: '0.875rem' }}>{Math.round(pdfScale * 100)}%</span>
                  <button
                    onClick={() => setPdfScale((s) => Math.min(4, Math.round((s + 0.25) * 100) / 100))}
                    style={{
                      padding: '6px 10px',
                      fontSize: '0.875rem',
                      backgroundColor: '#374151',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                    }}
                  >
                    +
                  </button>
                  {previewUrl && (
                    <a
                      href={previewUrl}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: '#93c5fd', fontSize: '0.875rem' }}
                    >
                      新窗口
                    </a>
                  )}
                </div>
              </div>
              <div style={{ flex: 1, overflow: 'auto', display: 'flex', justifyContent: 'center', padding: '16px' }}>
                <canvas ref={canvasRef} style={{ backgroundColor: 'white', borderRadius: '4px' }} />
              </div>
            </div>
          ) : isImageFile(effectiveName) ? (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                height: '70vh',
                backgroundColor: '#111827',
                borderRadius: '8px',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  padding: '12px 16px',
                  backgroundColor: '#0b1220',
                  borderBottom: '1px solid rgba(255,255,255,0.10)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  flexWrap: 'wrap',
                }}
              >
                <button
                  type="button"
                  onClick={() => setImageScale((s) => Math.max(0.2, Math.round((s - 0.1) * 100) / 100))}
                  style={{
                    padding: '6px 10px',
                    fontSize: '0.875rem',
                    backgroundColor: '#374151',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  -
                </button>
                <span style={{ color: '#e5e7eb', fontSize: '0.875rem' }}>{Math.round(imageScale * 100)}%</span>
                <button
                  type="button"
                  onClick={() => setImageScale((s) => Math.min(5, Math.round((s + 0.1) * 100) / 100))}
                  style={{
                    padding: '6px 10px',
                    fontSize: '0.875rem',
                    backgroundColor: '#374151',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  +
                </button>
                <button
                  type="button"
                  onClick={() => setImageRotation((r) => (r + 90) % 360)}
                  style={{
                    padding: '6px 10px',
                    fontSize: '0.875rem',
                    backgroundColor: '#374151',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  旋转
                </button>
                {previewUrl && (
                  <a href={previewUrl} target="_blank" rel="noreferrer" style={{ color: '#93c5fd', fontSize: '0.875rem' }}>
                    新窗口
                  </a>
                )}
              </div>
              <div style={{ flex: 1, overflow: 'auto', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                {previewUrl ? (
                  <img
                    src={previewUrl}
                    alt={effectiveName}
                    style={{
                      transform: `scale(${imageScale}) rotate(${imageRotation}deg)`,
                      transformOrigin: 'center center',
                      maxWidth: '100%',
                      maxHeight: '100%',
                    }}
                  />
                ) : null}
              </div>
            </div>
          ) : previewUrl ? (
            <iframe
              src={previewUrl}
              title={effectiveName}
              style={{ width: '100%', height: '70vh', border: '1px solid #e5e7eb', borderRadius: '8px' }}
            />
          ) : (
            <div style={{ color: '#6b7280' }}>暂无可预览内容</div>
          )}
        </div>
      </div>
    </div>
  );
};

