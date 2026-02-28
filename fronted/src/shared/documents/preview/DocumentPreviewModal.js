import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useEscapeClose } from '../../hooks/useEscapeClose';
import { ensureTablePreviewStyles } from '../../preview/tablePreviewStyles';
import { isMarkdownFilename, MarkdownPreview } from '../../preview/markdownPreview';
import { loadDocumentPreview } from '../../preview/ragflowPreviewManager';
import documentClient, { DOCUMENT_SOURCE } from '../documentClient';

const isCsvFilename = (name) => String(name || '').toLowerCase().endsWith('.csv');

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

export const DocumentPreviewModal = ({ open, target, onClose, canDownloadFiles = false }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [payload, setPayload] = useState(null);
  const [effectiveName, setEffectiveName] = useState('');
  const [objectUrl, setObjectUrl] = useState('');
  const lastUrlRef = useRef('');

  const close = useCallback(() => {
    setPayload(null);
    setError('');
    setEffectiveName('');
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

      try {
        const source = target.source;
        const docId = target.docId;
        const datasetName = target.datasetName || target.dataset;
        const sessionId = target.sessionId;
        const title = target.filename || target.title || `document_${docId}`;

        const data = await loadDocumentPreview({
          docId,
          dataset: datasetName,
          title,
          getPreviewJson: async ({ docId: _id, dataset }) =>
            documentClient.preview({
              source,
              docId: _id,
              datasetName: source === DOCUMENT_SOURCE.RAGFLOW ? dataset : undefined,
              sessionId: source === DOCUMENT_SOURCE.PATENT ? sessionId : undefined,
            }),
          getDownloadBlob: canDownloadFiles
            ? async ({ docId: _id, dataset, filename }) =>
                documentClient.downloadBlob({
                  source,
                  docId: _id,
                  datasetName: source === DOCUMENT_SOURCE.RAGFLOW ? dataset : undefined,
                  sessionId: source === DOCUMENT_SOURCE.PATENT ? sessionId : undefined,
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
          const blob = new Blob([base64ToBytes(data.content)], { type: 'application/pdf' });
          const url = window.URL.createObjectURL(blob);
          lastUrlRef.current = url;
          setObjectUrl(url);
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
        sessionId: target.source === DOCUMENT_SOURCE.PATENT ? target.sessionId : undefined,
        render: 'html',
      });
      if (data?.type !== 'html' || !data?.content) throw new Error(data?.message || '此文件类型不支持原样预览(HTML)');

      const name = String(data?.filename || effectiveName || '');
      setEffectiveName(name);
      setPayload(data);

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

              if (p.type === 'pdf' && objectUrl) {
                return <iframe title="pdf-preview" src={objectUrl} style={{ width: '100%', height: '78vh', border: '1px solid #e5e7eb', borderRadius: '10px' }} />;
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
