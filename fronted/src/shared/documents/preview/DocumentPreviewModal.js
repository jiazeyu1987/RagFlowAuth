import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useEscapeClose } from '../../hooks/useEscapeClose';
import { ensureTablePreviewStyles } from '../../preview/tablePreviewStyles';
import { isMarkdownFilename, MarkdownPreview } from '../../preview/markdownPreview';
import { loadDocumentPreview } from '../../preview/ragflowPreviewManager';
import documentClient, { DOCUMENT_SOURCE } from '../documentClient';

const isCsvFilename = (name) => String(name || '').toLowerCase().endsWith('.csv');
const ONLYOFFICE_EXTENSIONS = new Set(['.xls', '.ppt', '.pptx']);

const getFileExtensionLower = (name) => {
  const s = String(name || '').trim().toLowerCase();
  const idx = s.lastIndexOf('.');
  if (idx < 0) return '';
  return s.slice(idx);
};

const base64ToBytes = (base64) => {
  const bin = atob(String(base64 || ''));
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
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
      rows.push(row);
      row = [];
      cell = '';
      continue;
    }

    cell += ch;
  }
  row.push(cell);
  rows.push(row);
  return rows;
};

const rowsToHtmlTable = (rows) => {
  const safeRows = Array.isArray(rows) ? rows : [];
  const maxCols = safeRows.reduce((m, r) => Math.max(m, Array.isArray(r) ? r.length : 0), 0);
  const pad = (r) => {
    const out = Array.isArray(r) ? [...r] : [];
    while (out.length < maxCols) out.push('');
    return out;
  };
  const normalized = safeRows.map(pad);

  const body = normalized
    .map((r) => `<tr>${r.map((c) => `<td>${escapeHtml(c)}</td>`).join('')}</tr>`)
    .join('');
  return `<table><tbody>${body}</tbody></table>`;
};

const OnlyOfficeViewer = ({ serverUrl, config }) => {
  const containerId = useMemo(
    () => `onlyoffice-doc-editor-${Math.random().toString(36).slice(2)}`,
    []
  );
  const editorRef = useRef(null);
  const [viewerError, setViewerError] = useState('');

  useEffect(() => {
    if (!serverUrl || !config) return undefined;

    let disposed = false;
    const normalized = String(serverUrl || '').replace(/\/+$/, '');
    const scriptSrc = `${normalized}/web-apps/apps/api/documents/api.js`;
    const scriptId = `onlyoffice-docsapi-${normalized.replace(/[^a-zA-Z0-9]/g, '_')}`;
    let scriptEl = document.getElementById(scriptId);

    const initEditor = () => {
      if (disposed) return;
      if (!window.DocsAPI || typeof window.DocsAPI.DocEditor !== 'function') {
        setViewerError('ONLYOFFICE DocsAPI 未就绪');
        return;
      }
      try {
        if (editorRef.current && typeof editorRef.current.destroyEditor === 'function') {
          editorRef.current.destroyEditor();
        }
        editorRef.current = new window.DocsAPI.DocEditor(containerId, config);
        setViewerError('');
      } catch (e) {
        setViewerError(e?.message || 'ONLYOFFICE 初始化失败');
      }
    };

    const handleLoad = () => initEditor();
    const handleError = () => setViewerError('加载 ONLYOFFICE 脚本失败');

    if (scriptEl) {
      scriptEl.addEventListener('load', handleLoad);
      scriptEl.addEventListener('error', handleError);
      if (window.DocsAPI && typeof window.DocsAPI.DocEditor === 'function') initEditor();
    } else {
      scriptEl = document.createElement('script');
      scriptEl.id = scriptId;
      scriptEl.src = scriptSrc;
      scriptEl.async = true;
      scriptEl.onload = handleLoad;
      scriptEl.onerror = handleError;
      document.body.appendChild(scriptEl);
    }

    return () => {
      disposed = true;
      if (scriptEl) {
        scriptEl.removeEventListener('load', handleLoad);
        scriptEl.removeEventListener('error', handleError);
      }
      if (editorRef.current && typeof editorRef.current.destroyEditor === 'function') {
        try {
          editorRef.current.destroyEditor();
        } catch {
          // ignore
        }
      }
      editorRef.current = null;
    };
  }, [serverUrl, config, containerId]);

  if (viewerError) return <div style={{ color: '#991b1b' }}>{viewerError}</div>;
  return <div id={containerId} style={{ width: '100%', height: '78vh', border: '1px solid #e5e7eb', borderRadius: '10px' }} />;
};

export const DocumentPreviewModal = ({ open, target, onClose, canDownloadFiles = false }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [payload, setPayload] = useState(null);
  const [effectiveName, setEffectiveName] = useState('');
  const [objectUrl, setObjectUrl] = useState('');
  const [onlyOfficeServerUrl, setOnlyOfficeServerUrl] = useState('');
  const [onlyOfficeConfig, setOnlyOfficeConfig] = useState(null);
  const [pdfPageImages, setPdfPageImages] = useState([]);
  const [pdfRendering, setPdfRendering] = useState(false);
  const [pdfRenderingMessage, setPdfRenderingMessage] = useState('');
  const lastUrlRef = useRef('');

  const close = useCallback(() => {
    setPayload(null);
    setError('');
    setEffectiveName('');
    setOnlyOfficeServerUrl('');
    setOnlyOfficeConfig(null);
    onClose?.();
  }, [onClose]);

  useEscapeClose(open, close);

  useEffect(() => {
    ensureTablePreviewStyles();
  }, []);

  useEffect(() => {
    if (!open) return;
    if (!target?.docId || !target?.source) return;

    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError('');
      setPayload(null);
      setOnlyOfficeServerUrl('');
      setOnlyOfficeConfig(null);
      setPdfPageImages([]);
      setPdfRendering(false);
      setPdfRenderingMessage('');

      try {
        const source = target.source;
        const docId = target.docId;
        const datasetName = target.datasetName || target.dataset;
        const sessionId = target.sessionId;
        const title = target.filename || target.title || `document_${docId}`;
        const ext = getFileExtensionLower(title);

        if (
          (source === DOCUMENT_SOURCE.RAGFLOW || source === DOCUMENT_SOURCE.KNOWLEDGE) &&
          ONLYOFFICE_EXTENSIONS.has(ext)
        ) {
          const onlyOffice = await documentClient.onlyofficeEditorConfig({
            source,
            docId,
            datasetName: source === DOCUMENT_SOURCE.RAGFLOW ? datasetName : undefined,
            sessionId:
              source === DOCUMENT_SOURCE.PATENT || source === DOCUMENT_SOURCE.PAPER
                ? sessionId
                : undefined,
            filename: title,
          });
          if (cancelled) return;
          setEffectiveName(String(onlyOffice?.filename || title || ''));
          setOnlyOfficeServerUrl(String(onlyOffice?.server_url || ''));
          setOnlyOfficeConfig(onlyOffice?.config || null);
          setPayload({ type: 'onlyoffice' });
          return;
        }

        const data = await loadDocumentPreview({
          docId,
          dataset: datasetName,
          title,
          getPreviewJson: async ({ docId: _id, dataset }) =>
            documentClient.preview({
              source,
              docId: _id,
              datasetName: source === DOCUMENT_SOURCE.RAGFLOW ? dataset : undefined,
              sessionId:
                source === DOCUMENT_SOURCE.PATENT || source === DOCUMENT_SOURCE.PAPER
                  ? sessionId
                  : undefined,
            }),
          getDownloadBlob: canDownloadFiles
            ? async ({ docId: _id, dataset, filename }) =>
                documentClient.downloadBlob({
                  source,
                  docId: _id,
                  datasetName: source === DOCUMENT_SOURCE.RAGFLOW ? dataset : undefined,
                  sessionId:
                    source === DOCUMENT_SOURCE.PATENT || source === DOCUMENT_SOURCE.PAPER
                      ? sessionId
                      : undefined,
                  filename,
                })
            : undefined,
        });

        if (cancelled) return;

        const name = String(data?.filename || title || '');
        setEffectiveName(name);
        setPayload(data || null);

        // Cleanup old URL
        if (lastUrlRef.current) {
          try {
            window.URL.revokeObjectURL(lastUrlRef.current);
          } catch {
            // ignore
          }
          lastUrlRef.current = '';
          setObjectUrl('');
        }

        if (data?.type === 'pdf' && data?.content) {
          if (canDownloadFiles) {
            const blob = new Blob([base64ToBytes(data.content)], { type: 'application/pdf' });
            const url = window.URL.createObjectURL(blob);
            lastUrlRef.current = url;
            setObjectUrl(url);
          } else {
            setPdfRendering(true);
            setPdfRenderingMessage('PDF 预览加载中...');
            try {
              const pdfBytes = base64ToBytes(data.content);
              const pdfjsLib = await import('pdfjs-dist/webpack.mjs');
              const loadingTask = pdfjsLib.getDocument({ data: pdfBytes });
              const pdf = await loadingTask.promise;
              const total = Number(pdf.numPages) || 0;
              const pages = [];

              for (let i = 1; i <= total; i++) {
                if (cancelled) return;
                setPdfRenderingMessage(`PDF 预览加载中 (${i}/${total})...`);
                const page = await pdf.getPage(i);
                const viewport = page.getViewport({ scale: 1.4 });
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d', { alpha: false });
                if (!ctx) continue;
                canvas.width = Math.ceil(viewport.width);
                canvas.height = Math.ceil(viewport.height);
                await page.render({ canvasContext: ctx, viewport }).promise;
                pages.push(canvas.toDataURL('image/png'));
              }

              if (!cancelled) setPdfPageImages(pages);
            } catch (pdfError) {
              if (!cancelled) setError(pdfError?.message || 'PDF 预览失败');
            } finally {
              if (!cancelled) {
                setPdfRendering(false);
                setPdfRenderingMessage('');
              }
            }
          }
        } else if (data?.type === 'html' && data?.content) {
          const blob = new Blob([base64ToBytes(data.content)], { type: 'text/html; charset=utf-8' });
          const url = window.URL.createObjectURL(blob);
          lastUrlRef.current = url;
          setObjectUrl(url);
        } else if (data?.type === 'image' && data?.content) {
          const imageType = data?.image_type || 'png';
          const mime = `image/${imageType}`;
          const blob = new Blob([base64ToBytes(data.content)], { type: mime });
          const url = window.URL.createObjectURL(blob);
          lastUrlRef.current = url;
          setObjectUrl(url);
        }
      } catch (e) {
        if (cancelled) return;
        setError(e?.message || '预览失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [open, target?.source, target?.docId, target?.datasetName, target?.dataset, target?.sessionId, target?.filename, target?.title, canDownloadFiles]);

  useEffect(() => {
    if (!open) return;
    return () => {
      if (lastUrlRef.current) {
        try {
          window.URL.revokeObjectURL(lastUrlRef.current);
        } catch {
          // ignore
        }
        lastUrlRef.current = '';
      }
    };
  }, [open]);

  const excelRenderHint = useMemo(() => {
    if (payload?.type !== 'excel') return '';
    return '如果 Excel 里包含流程图/形状，表格模式可能看不到；可点“原样预览(HTML)”查看。';
  }, [payload?.type]);

  const openOriginalHtml = useCallback(async () => {
    if (!target?.docId || !target?.source) return;
    try {
      setLoading(true);
      setError('');
      const data = await documentClient.preview({
        source: target.source,
        docId: target.docId,
        datasetName: target.source === DOCUMENT_SOURCE.RAGFLOW ? target.datasetName || target.dataset : undefined,
        sessionId:
          target.source === DOCUMENT_SOURCE.PATENT || target.source === DOCUMENT_SOURCE.PAPER
            ? target.sessionId
            : undefined,
        render: 'html',
      });
      if (data?.type !== 'html' || !data?.content) throw new Error(data?.message || '此文件类型不支持原样预览(HTML)');

      const name = String(data?.filename || effectiveName || '');
      setEffectiveName(name);
      setPayload(data);
      setOnlyOfficeServerUrl('');
      setOnlyOfficeConfig(null);
      setPdfPageImages([]);
      setPdfRendering(false);
      setPdfRenderingMessage('');

      if (lastUrlRef.current) {
        try {
          window.URL.revokeObjectURL(lastUrlRef.current);
        } catch {
          // ignore
        }
        lastUrlRef.current = '';
        setObjectUrl('');
      }
      const blob = new Blob([base64ToBytes(data.content)], { type: 'text/html; charset=utf-8' });
      const url = window.URL.createObjectURL(blob);
      lastUrlRef.current = url;
      setObjectUrl(url);
    } catch (e) {
      setError(e?.message || '预览失败');
    } finally {
      setLoading(false);
    }
  }, [target, effectiveName]);

  if (!open) return null;

  return (
    <div
      onClick={close}
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
        padding: '16px',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          backgroundColor: 'white',
          borderRadius: '10px',
          width: '95vw',
          maxWidth: '1200px',
          height: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
        }}
      >
        <div
          style={{
            padding: '14px 18px',
            borderBottom: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <div style={{ fontWeight: 700, fontSize: '1.05rem', color: '#111827', minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {effectiveName || target?.filename || target?.title || '文档预览'}
          </div>
          <button
            type="button"
            onClick={close}
            data-testid="document-preview-close"
            style={{
              background: 'transparent',
              border: 'none',
              fontSize: '1.4rem',
              cursor: 'pointer',
              color: '#6b7280',
              width: '36px',
              height: '36px',
              borderRadius: '8px',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#111827')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#6b7280')}
            aria-label="close"
          >
            ×
          </button>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: '18px' }}>
          {loading ? (
            <div style={{ color: '#6b7280' }}>加载中…</div>
          ) : error ? (
            <div style={{ color: '#991b1b' }}>{error}</div>
          ) : payload ? (
            (() => {
              const p = payload;

              if (p.type === 'excel' && p.sheets) {
                const sheetNames = Object.keys(p.sheets || {});
                return (
                  <div className="table-preview" style={{ height: '100%', overflow: 'auto' }}>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        padding: '10px 12px',
                        backgroundColor: '#eff6ff',
                        border: '1px solid #bfdbfe',
                        borderRadius: '10px',
                        color: '#1e3a8a',
                        fontSize: '0.95rem',
                        marginBottom: '16px',
                      }}
                    >
                      <div style={{ flex: 1 }}>{excelRenderHint}</div>
                      <button
                        type="button"
                        onClick={openOriginalHtml}
                        style={{
                          padding: '8px 12px',
                          backgroundColor: '#3b82f6',
                          color: 'white',
                          border: 'none',
                          borderRadius: '8px',
                          cursor: 'pointer',
                          fontSize: '0.9rem',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        原样预览(HTML)
                      </button>
                    </div>

                    {sheetNames.map((sheetName, index) => (
                      <div key={sheetName} style={{ marginBottom: index < sheetNames.length - 1 ? '32px' : 0 }}>
                        {sheetNames.length > 1 && (
                          <h3
                            style={{
                              fontSize: '1.05rem',
                              fontWeight: 800,
                              margin: '0 0 12px 0',
                              color: '#111827',
                              borderBottom: '2px solid #e5e7eb',
                              paddingBottom: '8px',
                            }}
                          >
                            {sheetName}
                          </h3>
                        )}
                        <div style={{ overflowX: 'auto' }} dangerouslySetInnerHTML={{ __html: p.sheets[sheetName] }} />
                      </div>
                    ))}
                  </div>
                );
              }

              if (p.type === 'text') {
                const text = String(p.content || '');
                const name = String(p.filename || effectiveName || '');

                if (isCsvFilename(name)) {
                  const firstLine = text.split(/\r?\n/)[0] || '';
                  const delimiter = detectDelimiter(firstLine);
                  const rows = parseDelimited(text, delimiter);
                  const tableHtml = rowsToHtmlTable(rows);
                  return <div className="table-preview" dangerouslySetInnerHTML={{ __html: tableHtml }} />;
                }

                if (isMarkdownFilename(name)) return <MarkdownPreview content={text} />;
                return <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{text}</pre>;
              }

              if (p.type === 'docx') {
                return (
                  <div className="table-preview" style={{ padding: '16px', border: '1px solid #e5e7eb', borderRadius: '10px' }}>
                    <div
                      style={{ fontSize: '0.95rem', lineHeight: '1.65', color: '#111827' }}
                      dangerouslySetInnerHTML={{ __html: String(p.html || '') }}
                    />
                  </div>
                );
              }

              if (p.type === 'html' && objectUrl) {
                return <iframe title="html-preview" src={objectUrl} style={{ width: '100%', height: '78vh', border: '1px solid #e5e7eb', borderRadius: '10px' }} />;
              }

              if (p.type === 'onlyoffice' && onlyOfficeServerUrl && onlyOfficeConfig) {
                return <OnlyOfficeViewer serverUrl={onlyOfficeServerUrl} config={onlyOfficeConfig} />;
              }

              if (p.type === 'pdf' && objectUrl) {
                return <iframe title="pdf-preview" src={objectUrl} style={{ width: '100%', height: '78vh', border: '1px solid #e5e7eb', borderRadius: '10px' }} />;
              }

              if (p.type === 'pdf' && !canDownloadFiles) {
                if (pdfRendering) return <div style={{ color: '#6b7280' }}>{pdfRenderingMessage || 'PDF 预览加载中...'}</div>;
                if (pdfPageImages.length > 0) {
                  return (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                      <div style={{ color: '#6b7280', fontSize: '0.88rem' }}>仅预览，不可下载/打印</div>
                      {pdfPageImages.map((imgSrc, index) => (
                        <img
                          key={`pdf-page-${index + 1}`}
                          alt={`pdf-page-${index + 1}`}
                          src={imgSrc}
                          style={{
                            width: '100%',
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            backgroundColor: '#ffffff',
                          }}
                        />
                      ))}
                    </div>
                  );
                }
                return <div style={{ color: '#6b7280' }}>PDF 预览不可用</div>;
              }

              if (p.type === 'image' && objectUrl) {
                return (
                  <div style={{ textAlign: 'center' }}>
                    <img alt={effectiveName || 'image'} src={objectUrl} style={{ maxWidth: '100%', maxHeight: '78vh', borderRadius: '10px' }} />
                  </div>
                );
              }

              return <div style={{ color: '#6b7280' }}>{p.message || '不支持预览，请下载查看。'}</div>;
            })()
          ) : (
            <div style={{ color: '#6b7280' }}>暂无内容</div>
          )}
        </div>
      </div>
    </div>
  );
};
